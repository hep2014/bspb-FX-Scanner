from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from data_pipeline.core import Run, atomic_write, digest

MARKET = "data/processed/market/"
CONTRACTS = "data/processed/contracts/"
ECON = "data/processed/economics/"
LINEAGE = ("source_id", "source", "source_sha256")
SPOT = ("date", "currency", "currency_code", "cbr_currency_id", "nominal", "rate_original",
        "rub_per_unit", "publication_date", "date_role", *LINEAGE)
RATES = ("date", "rate_name", "tenor", "rate", "rate_unit", "publication_date", *LINEAGE)
ISS = ("trade_date", "secid", "instrument_name", "underlying", "contract_type", "expiration_date",
       "settlement_type", "open", "high", "low", "close", "settlement_price", "volume", "open_interest",
       "volume_unit", "num_trades", "traded", "usable_for_backtest", "quality_flag", "currency", "price_unit", "board", "history_kind", *LINEAGE)
SPECS = ("secid", "instrument_name", "underlying", "contract_type", "expiration_date", "settlement_type",
         "currency", "quote_currency", "price_unit", "contract_size", "price_tick", "settlement_rule",
         "initial_margin_long", "initial_margin_short", "initial_margin_exchange", "margin_as_of", "margin_source_sha256",
         "history_from", "history_till",
         "listed_from", "last_trade_date", "engine", "market", "board", *LINEAGE)
TRADE = ("period_start", "period_end", "frequency", "publication_date", "direction", "geography",
         "indicator", "currency_group", "currency_group_label", "value", "unit", "sheet", "cell",
         "methodology_note", *LINEAGE)
DERIVATIVES = ("period_start", "period_end", "publication_date", "indicator", "instrument",
               "currency_pair", "measure_type", "participant_scope", "value", "unit", "sheet",
               "cell", "methodology_note", *LINEAGE)
BANK = ("standard", "period_start", "period_end", "publication_date", "indicator", "indicator_original",
        "value", "unit", "document_type", "locator", "page", "verification_status", *LINEAGE)
DOCUMENTS = ("document_id", "source_document_id", "source_dataset", "source_url", "document_type", "language", "publication_date",
             "text", "text_hash", "file_format", "currency_clause_candidate", "license_status",
             "pii_status", "extraction_method", "corpus_class", "dedup_group", "source_id", "source_sha256")
CANDIDATES = ("candidate_id", "document_id", "source_id", "source_url", "source_sha256", "text_hash",
              "start", "end", "matched_text", "context_start", "context", "label_origin", "reviewer_status")
ANNOTATION = ("document_id", "text_hash", "candidate_id", "exposure_exists", "clause_type",
              "reference_currency", "payment_currency", "notional_amount", "fixing_date", "payment_date",
              "exchange_rate_source", "conversion_formula", "exposure_direction", "evidence_span",
              "annotation_confidence", "reviewer_status")
CUAD_LABELS = ("document_id", "label_source", "category", "start", "end", "evidence", "source_id", "source_sha256")
NLI = ("document_id", "original_split", "hypothesis_id", "hypothesis", "label", "label_original",
       "evidence_span_indices", "evidence_spans", "evidence_text", "source_url", "source_id", "source_sha256")
DATE_FIELDS = {"date", "trade_date", "period_start", "period_end", "publication_date", "expiration_date"}
INT_FIELDS = {"nominal", "num_trades", "open_interest"}
FLOAT_FIELDS = {"rate_original", "rub_per_unit", "rate", "open", "high", "low", "close",
                "settlement_price", "volume"}


def csv_bytes(rows: list[dict], fields: tuple[str, ...]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def write_dataset(run: Run, path: str, rows: list[dict], fields: tuple[str, ...], *,
                  key: tuple[str, ...], dates: str | None = None,
                  sources: tuple[str, ...] = (), warnings: list[str] | None = None) -> None:
    target = run.path(path)
    output_type = target.suffix
    if output_type == ".csv":
        data = csv_bytes(rows, fields)
    elif output_type == ".jsonl":
        data = "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows).encode()
    elif output_type == ".parquet":
        fields_types = {n: pa.date32() if n in DATE_FIELDS else pa.int64() if n in INT_FIELDS
                        else pa.float64() if n in FLOAT_FIELDS else pa.bool_() if n in {"traded", "usable_for_backtest"}
                        else pa.string() for n in fields}
        schema = pa.schema([(name, fields_types[name]) for name in fields])
        table = pa.Table.from_pylist(rows, schema=schema)
        buffer = pa.BufferOutputStream()
        pq.write_table(table, buffer, compression="zstd")
        data = buffer.getvalue().to_pybytes()
    else:
        raise ValueError(f"Unsupported dataset format: {output_type}")
    atomic_write(target, data)
    source_ids = sorted({row["source_id"] for row in rows if row.get("source_id")} | set(sources))
    run.state["datasets"][path] = {
        "rows": len(rows), "fields": fields, "key": key, "date_field": dates, "bytes": len(data),
        "sha256": digest(target), "sources": source_ids, "warnings": warnings or [],
    }


def read_dataset(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False).replace("", None)
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            return pd.DataFrame(json.loads(line) for line in stream if line.strip())
    raise ValueError(f"Unknown dataset format: {path}")


def date_order(row: dict, field: str):
    return row.get(field) or date.min
