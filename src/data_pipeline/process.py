from __future__ import annotations

import logging
from datetime import date

from data_pipeline.core import Run, SourceError, write_json
from data_pipeline.datasets import (
    ANNOTATION, BANK, CANDIDATES, CONTRACTS, CUAD_LABELS, DERIVATIVES, DOCUMENTS, ECON, ISS,
    MARKET, NLI, RATES, SPECS, SPOT, TRADE, write_dataset,
)
from data_pipeline.sources import cbr, contracts, economics, moex
from data_pipeline.extraction.bank import financial_report_rows
from data_pipeline.extraction.reviews import count_table

LOG = logging.getLogger(__name__)


def process_market(run: Run) -> None:
    spot, rate = [], []
    fx_config = run.sources["cbr_fx"]["codes"]
    spot_notes = []
    for currency, (identifier, code) in fx_config.items():
        inputs = run.raw("cbr_fx", currency, cbr.fx_url(run, identifier))
        if not inputs:
            inputs = run.raw("cbr_fx", currency)
        if not inputs:
            spot_notes.append(f"No primary file for {currency}")
            continue
        spot.extend(row for row in cbr.spot_rows(inputs[-1], currency, identifier, code)
                    if run.start <= row["date"] <= run.end)
    spot.sort(key=lambda row: (row["date"], row["currency"]))
    for suffix in ("parquet", "csv"):
        write_dataset(run, f"{MARKET}fx_spot_daily.{suffix}", spot, SPOT, key=("date", "currency"),
                      dates="date", sources=("cbr_fx",), warnings=spot_notes)
    for source in ("cbr_ruonia", "cbr_key_rate"):
        inputs = run.raw(source, "history", cbr.cbr_table_url(run, source)) or run.raw(source, "history")
        if inputs:
            rate.extend(row for row in cbr.rate_rows(inputs[-1]) if run.start <= row["date"] <= run.end)
    rate.sort(key=lambda row: (row["date"], row["rate_name"]))
    write_dataset(run, f"{MARKET}rub_interest_rates.parquet", rate, RATES, key=("date", "rate_name"),
                  dates="date", sources=("cbr_ruonia", "cbr_key_rate"))
    iss_spot, futures, specs, warnings = moex.prepare(run)
    for path, rows in (("fx_spot_moex_daily.parquet", iss_spot), ("fx_futures_daily.parquet", futures)):
        rows.sort(key=lambda row: (row["trade_date"], row["secid"], row["board"]))
        write_dataset(run, MARKET + path, rows, ISS, key=("trade_date", "secid", "board"),
                      dates="trade_date", sources=("moex",), warnings=warnings)
    write_dataset(run, f"{MARKET}instrument_specifications.csv", specs, SPECS, key=("secid", "board"),
                  dates="history_from", sources=("moex",), warnings=warnings)


def process_contracts(run: Run) -> None:
    docs, candidates, tasks, labels, nli, duplicates, dropped, reviewed_labels = contracts.prepare(run)
    warnings = []
    if docs:
        warnings.append("Corpus is for research. Automated masking cannot verify absence of PII")
    if duplicates:
        warnings.append(f"{sum(len(group['documents']) - 1 for group in duplicates)} duplicate documents excluded")
    if dropped:
        warnings.append(f"{len(dropped)} documents excluded for text quality")
    court_examples = list(contracts.court_examples(run))
    for filename, rows, schema, key, date_field, sources, notes in (
        ("contracts_corpus.jsonl", docs, DOCUMENTS, ("document_id",), "publication_date",
         ("cuad", "eis", "sec", "stanford_mcc"), warnings),
        ("fx_clause_candidates.jsonl", candidates, CANDIDATES, ("candidate_id",), None, ("cuad",), []),
        ("annotation_template.jsonl", tasks or [contracts.annotation_template(None)], ANNOTATION,
         (), None, (), []),
        ("cuad_annotations.jsonl", labels, CUAD_LABELS, (), None, ("cuad",), []),
        ("reviewed_fx_examples.jsonl", reviewed_labels, CUAD_LABELS, ("document_id",), None, ("cuad",),
         ["Evidence was inspected during preparation. Independent second review remains pending."]),
        ("russian_fx_court_excerpts.jsonl", court_examples,
         ("document_id", "publication_date", "reference_currency", "payment_currency", "evidence",
          "description", "document_type", "language", "label_origin", "pii_status", "source_id",
          "source_url", "source_sha256"), ("document_id",), "publication_date", ("russian_court",),
         ["Court decisions quote or describe contracts. Original agreements are unavailable."]),
        ("contractnli_labels.jsonl", nli, NLI, ("document_id", "hypothesis_id", "original_split"),
         None, ("contractnli",), []),
    ):
        write_dataset(run, CONTRACTS + filename, rows, schema, key=key, dates=date_field,
                      sources=sources, warnings=notes)
    write_json(run.root / "data/metadata/contract_dedup.json", {"duplicates": duplicates, "dropped": dropped})


def in_period(run: Run, row: dict) -> bool:
    return row["period_end"] >= run.start and row["period_end"] <= run.end


def process_economics(run: Run) -> None:
    trade, derivatives, financials = [], [], []
    trade_raw = run.raw("cbr_trade_structure", "currency_structure")
    if trade_raw:
        trade.extend(economics.trade_structure(trade_raw[-1]))
    volume_raw = run.raw("cbr_trade_volume", "trade_volume")
    if volume_raw:
        trade.extend(economics.trade_volume(volume_raw[-1]))
    trade = [row for row in trade if in_period(run, row)]
    trade.sort(key=lambda row: (row["period_end"], row["frequency"], row["direction"],
                                row["geography"], row["indicator"], row["currency_group"] or ""))
    write_dataset(run, ECON + "foreign_trade_currency_structure.csv", trade, TRADE,
                  key=("period_end", "frequency", "direction", "geography", "indicator", "currency_group"),
                  dates="period_end", sources=("cbr_trade_structure", "cbr_trade_volume"))
    warnings = []
    files = {raw.key: raw for raw in run.raw("cbr_derivatives") if raw.path.suffix == ".xlsx"}
    for raw in files.values():
        try:
            observations = list(economics.derivative_turnover(raw))
            if not observations:
                warnings.append(f"{raw.key}: no supported table rows")
            derivatives.extend(observations)
        except (SourceError, KeyError, ValueError) as exc:
            warnings.append(f"{raw.key}: {exc}")
    derivatives.extend(economics.reviewed_observations(run, "cbr_derivatives"))
    for raw in run.raw("cbr_derivatives", "review_2026"):
        try:
            derivatives.extend(list(count_table(raw)))
        except (ImportError, SourceError) as exc:
            warnings.append(str(exc))
    derivatives = [row for row in derivatives if in_period(run, row)]
    derivatives.sort(key=lambda row: (row["period_end"], row["instrument"], row.get("currency_pair") or ""))
    write_dataset(run, ECON + "fx_derivatives_market.csv", derivatives, DERIVATIVES,
                  key=("period_end", "indicator", "instrument", "currency_pair", "measure_type", "participant_scope", "unit"),
                  dates="period_end", sources=("cbr_derivatives",), warnings=warnings)
    for key, (_, published) in run.sources["bspb_release"]["releases"].items():
        rows = run.raw("bspb_release", key)
        if rows:
            financials.extend(economics.press_release_rows(rows[-1], date.fromisoformat(published)))
    financials.extend(financial_report_rows(run))
    financials = [row for row in financials if in_period(run, row)]
    financials.sort(key=lambda row: (row["standard"], row["period_end"], row["indicator"], row["locator"]))
    write_dataset(run, ECON + "bspb_financials.csv", financials, BANK,
                  key=("standard", "period_end", "indicator", "source_sha256", "locator"),
                  dates="period_end", sources=("bspb_ifrs", "bspb_ras", "bspb_release"))


def process(run: Run) -> None:
    LOG.info("Process market data")
    process_market(run)
    LOG.info("Process contract data")
    process_contracts(run)
    LOG.info("Process economic data")
    process_economics(run)
    run.state["quality"] = {}
    run.save()
