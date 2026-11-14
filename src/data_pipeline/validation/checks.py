from __future__ import annotations

import hashlib
from xml.etree import ElementTree

import numpy as np
import pandas as pd

from data_pipeline.core import Run, digest
from data_pipeline.datasets import CONTRACTS, ECON, MARKET, read_dataset
from data_pipeline.sources.cbr import decimal, rate_rows, russian_date


def check_cbr_samples(run: Run, frame: pd.DataFrame, result: dict) -> None:
    index = {(str(row.date)[:10], row.cbr_currency_id): row for row in frame.itertuples()}
    count = 0
    for raw in [x for x in run.raw("cbr_fx") if x.key.startswith("daily_")]:
        root = ElementTree.parse(raw.path).getroot()
        effective = russian_date(root.attrib["Date"]).isoformat()
        for record in root.findall("Valute"):
            pair = (effective, record.attrib["ID"])
            if pair not in index:
                continue
            expected = decimal(record.findtext("Value")) / decimal(record.findtext("Nominal"))
            count += 1
            if abs(float(expected) - float(index[pair].rub_per_unit)) > 1e-9:
                result["errors"].append(f"CBR XML_daily cross-check mismatch for {pair}")
    result["cbr_independent_crosscheck_rows"] = count


def check_spot(run: Run, frame: pd.DataFrame, result: dict) -> None:
    nominal = pd.to_numeric(frame["nominal"], errors="coerce")
    raw_rate = pd.to_numeric(frame["rate_original"], errors="coerce")
    unit_rate = pd.to_numeric(frame["rub_per_unit"], errors="coerce")
    valid = nominal.gt(0) & raw_rate.gt(0) & unit_rate.gt(0) & nominal.mod(1).eq(0)
    if not valid.all() or not np.allclose(raw_rate / nominal, unit_rate, atol=1e-10):
        result["errors"].append("FX quote, nominal or per-unit normalization failed")
    result["series"] = {}
    for currency, group in frame.groupby("currency"):
        group = group.sort_values("date")
        dates = pd.to_datetime(group["date"])
        numbers = pd.to_numeric(group["rub_per_unit"])
        gaps = dates.diff().dt.days
        moves = numbers.pct_change()
        jump = moves.abs().gt(run.settings["spot_jump_threshold"])
        nominal_change = group["nominal"].ne(group["nominal"].shift())
        nominal_change.iloc[0] = False
        result["series"][currency] = {
            "rows": len(group), "from": dates.min().date().isoformat(),
            "to": dates.max().date().isoformat(), "longest_gap_days": int(gaps.max()) if len(group) > 1 else None,
            "nominal_changes": [{"date": str(dt)[:10], "nominal": int(n)}
                                for dt, n in zip(group.loc[nominal_change, "date"],
                                                 group.loc[nominal_change, "nominal"], strict=True)],
            "flagged_jumps": [{"date": str(dt)[:10], "pct_change": round(100 * float(move), 3)}
                             for dt, move in zip(group.loc[jump, "date"], moves[jump], strict=True)],
        }
    if any(item["flagged_jumps"] for item in result["series"].values()):
        result["warnings"].append("Large observed-to-observed FX moves retained for review")
    result["warnings"].append("CBR XML gives effective date only. Publication dates are missing")
    if not (frame["date_role"] == "official_effective_date").all():
        result["errors"].append("Official exchange rate date semantics changed")
    if not frame["date"].is_monotonic_increasing:
        result["errors"].append("FX dates are not ordered")
    check_cbr_samples(run, frame, result)


def check_rates(run: Run, frame: pd.DataFrame, result: dict) -> None:
    rate = pd.to_numeric(frame["rate"], errors="coerce")
    if not rate.between(0, 100).all() or not frame["rate_unit"].eq("pct_pa").all():
        result["errors"].append("Rate values or units failed checks")
    rate_date = pd.to_datetime(frame["date"])
    publication = pd.to_datetime(frame["publication_date"])
    if (publication < rate_date).any():
        result["errors"].append("A publication date is earlier than the rate date")
    ruonia = frame["rate_name"].eq("RUONIA")
    if publication[ruonia].isna().any() or not frame.loc[ruonia, "tenor"].eq("ON").all():
        result["errors"].append("RUONIA records must include the ON tenor and publication date")
    xlsx = run.raw("cbr_ruonia", "xlsx_history")
    if xlsx:
        from data_pipeline.sources.cbr import ruonia_xlsx_url

        matched = run.raw("cbr_ruonia", "xlsx_history", ruonia_xlsx_url(run)) or xlsx
        expected = {row["date"]: (row["rate"], row["publication_date"])
                    for row in rate_rows(matched[-1]) if run.start <= row["date"] <= run.end}
        actual = {row.date: (row.rate, row.publication_date)
                  for row in frame.loc[ruonia].itertuples()}
        result["ruonia_crosschecked_rows"] = len(expected.keys() & actual.keys())
        if expected != actual:
            result["errors"].append("RUONIA HTML and XLSX differ by date, rate or publication date")
    result["series"] = {
        key: {"rows": len(group), "from": str(group["date"].min())[:10], "to": str(group["date"].max())[:10]}
        for key, group in frame.groupby("rate_name")
    }


def check_iss(frame: pd.DataFrame, result: dict) -> None:
    dt = pd.to_datetime(frame["trade_date"])
    expiry = pd.to_datetime(frame["expiration_date"])
    expired = dt > expiry
    settlements = frame["quality_flag"].fillna("").str.contains("post_expiration_settlement_only", regex=False)
    if (expired & ~settlements).any():
        result["errors"].append(f"{int((expired & ~settlements).sum())} unexpected rows after expiry")
    for flag, label in (("post_expiration_settlement_only", "post-expiry settlement-only records"),
                        ("no_trades_zero_price", "zero price placeholders on zero-trade days converted to null"),
                        ("nonpositive_source_price", "nonpositive source OHLC on trading days set to null"),
                        ("spot_activity_without_prices", "spot rows with activity counter and no observable prices"),
                        ("exchange_spot_restriction", "USD/EUR spot records flagged under the exchange restriction since 2024-06-13")):
        count = frame["quality_flag"].fillna("").str.contains(flag, regex=False).sum()
        if count:
            result["warnings"].append(f"{int(count)} {label}")
    for name in ("open", "high", "low", "close", "settlement_price", "volume", "open_interest"):
        series = pd.to_numeric(frame[name], errors="coerce")
        minimum = 0 if name in {"volume", "open_interest"} else 1e-12
        if (series.dropna() < minimum).any():
            result["errors"].append(f"Negative or invalid ISS value in {name}")
    mask = frame[["open", "high", "low", "close"]].notna().all(axis=1)
    valid = frame.loc[mask]
    invalid = valid["low"].gt(valid[["open", "close"]].min(axis=1)) | valid["high"].lt(
        valid[["open", "close"]].max(axis=1))
    if invalid.any():
        result["errors"].append(f"{int(invalid.sum())} inconsistent OHLC rows")
    result["series"] = {
        name: {"rows": len(g), "from": str(g["trade_date"].min())[:10],
               "to": str(g["trade_date"].max())[:10], "instruments": g["secid"].nunique(),
               "last_trade": str(g.loc[g["traded"] & g["close"].notna(), "trade_date"].max())[:10],
               "eligible_last_trade": str(g.loc[g["usable_for_backtest"], "trade_date"].max())[:10]}
        for name, g in frame.groupby("underlying")
    }


def check_trade(frame: pd.DataFrame, result: dict) -> None:
    shares = frame[frame["indicator"].eq("settlement_currency_share")].copy()
    shares["value"] = pd.to_numeric(shares["value"], errors="coerce")
    if not shares["value"].dropna().between(0, 100).all():
        result["errors"].append("FX settlement shares must lie in [0,100]")
    grouped = shares.groupby(["period_end", "frequency", "direction", "geography"])["value"]
    sums = grouped.sum(min_count=3).dropna()
    exceptions = sums[~np.isclose(sums, 100, atol=0.1)]
    if len(exceptions):
        result["warnings"].append(f"{len(exceptions)} published complete share groups differ from 100%")
    missing = int(shares["value"].isna().sum())
    if missing:
        result["warnings"].append(f"{missing} unpublished share cells retained as null")
    volume = pd.to_numeric(frame.loc[frame["indicator"].eq("goods_trade_value_fob"), "value"], errors="coerce")
    if (volume.dropna() < 0).any():
        result["errors"].append("Negative trade volume")


def check_contracts(frame: pd.DataFrame, result: dict) -> None:
    sha = frame["text"].map(lambda value: hashlib.sha256(value.encode()).hexdigest())
    if not sha.eq(frame["text_hash"]).all():
        result["errors"].append("Text hash mismatch")
    if frame["dedup_group"].duplicated().any() or frame["text_hash"].duplicated().any():
        result["errors"].append("Duplicate contract text or split group")
    if frame["text"].str.contains("\ufffd", regex=False).any():
        result["errors"].append("Replacement character in contract text")
    result["contract_classes"] = frame["corpus_class"].value_counts().to_dict()
    result["languages"] = frame["language"].value_counts().to_dict()


def check_candidates(run: Run, frame: pd.DataFrame, result: dict) -> None:
    corpus_path = run.path(CONTRACTS + "contracts_corpus.jsonl")
    corpus = read_dataset(corpus_path).set_index("document_id")
    for row in frame.itertuples():
        if row.document_id not in corpus.index:
            result["errors"].append("Candidate references a missing document")
            return
        contract = corpus.loc[row.document_id]
        if not (0 <= row.start < row.end <= len(contract["text"])
                and contract["text"][row.start:row.end] == row.matched_text
                and contract["text_hash"] == row.text_hash):
            result["errors"].append(f"Unaligned candidate {row.candidate_id}")
            return
        if row.label_origin != "keyword_rule" or row.reviewer_status != "unreviewed":
            result["errors"].append(f"Invalid candidate review status {row.candidate_id}")
            return


def validate(run: Run) -> int:
    manifest_pairs = {(item["source_id"], item["sha256"]) for item in run.downloads}
    errors = []
    verified_raw = set()
    for item in run.downloads:
        path = run.path(item["path"])
        if path in verified_raw:
            continue
        verified_raw.add(path)
        if not path.is_file() or digest(path) != item["sha256"]:
            errors.append(f"Raw hash mismatch: {item['path']}")
    run.state["raw_integrity"] = {"files": len(verified_raw), "errors": errors}
    if not run.state["datasets"] and not errors:
        errors.append("No processed datasets to validate")
    quality = {}
    for relative, metadata in run.state["datasets"].items():
        path = run.path(relative)
        result = {"errors": [], "warnings": list(dict.fromkeys(metadata["warnings"]))}
        quality[relative] = result
        if not path.exists() or digest(path) != metadata["sha256"]:
            result["errors"].append("File missing or SHA-256 changed")
            continue
        frame = read_dataset(path)
        result["rows"] = len(frame)
        if len(frame) != metadata["rows"]:
            result["errors"].append("Row count differs from the dataset manifest")
        if frame.empty:
            result["warnings"].append("No rows available")
            continue
        missing = set(metadata["fields"]) - set(frame.columns)
        if missing:
            result["errors"].append(f"Missing fields: {sorted(missing)}")
            continue
        result["missing_pct"] = {
            col: round(100 * float(share), 2)
            for col, share in frame.isna().mean().items() if share > 0
        }
        date_field = metadata["date_field"]
        if date_field:
            dates = pd.to_datetime(frame[date_field], errors="coerce")
            if dates.notna().any():
                result.update({"date_min": dates.min().date().isoformat(),
                               "date_max": dates.max().date().isoformat(), "unique_dates": int(dates.nunique())})
            if frame[date_field].notna().sum() != dates.notna().sum():
                result["errors"].append(f"Invalid dates in {date_field}")
        key = metadata["key"]
        if key and frame.duplicated(subset=key).any():
            result["errors"].append(f"{int(frame.duplicated(subset=key).sum())} duplicates by {key}")
        if "source_sha256" in frame:
            pairs = set(zip(frame["source_id"], frame["source_sha256"], strict=True))
            result["source_rows"] = {str(k): int(v) for k, v in frame["source_id"].value_counts().items()}
            if date_field:
                result["source_periods"] = {
                    str(source): {"min": group.min().date().isoformat(), "max": group.max().date().isoformat()}
                    for source, group in dates.dropna().groupby(frame["source_id"])
                }
            if pairs - manifest_pairs:
                result["errors"].append("At least one row has no source in the manifest")
            if not set(frame["source_id"]).issubset(run.sources):
                result["errors"].append("Unknown source in registry")
        if relative.startswith(MARKET + "fx_spot_daily"):
            check_spot(run, frame, result)
        elif relative == MARKET + "rub_interest_rates.parquet":
            check_rates(run, frame, result)
        elif relative in {MARKET + "fx_spot_moex_daily.parquet", MARKET + "fx_futures_daily.parquet"}:
            check_iss(frame, result)
        elif relative == ECON + "foreign_trade_currency_structure.csv":
            check_trade(frame, result)
        elif relative == ECON + "fx_derivatives_market.csv":
            values = pd.to_numeric(frame["value"], errors="coerce")
            if values.isna().any() or (values < 0).any():
                result["errors"].append("Invalid turnover or position value")
            units = {"turnover": "usd_mn", "gross_notional_outstanding": "usd_mn",
                     "average_daily_turnover": "usd_mn_per_day", "deal_count": "contracts"}
            if not frame["measure_type"].map(units).eq(frame["unit"]).all():
                result["errors"].append("Incompatible market measure and unit")
            result["measure_types"] = frame["measure_type"].value_counts().to_dict()
        elif relative == ECON + "bspb_financials.csv":
            values = pd.to_numeric(frame["value"], errors="coerce")
            if (values.isna() & frame["verification_status"].ne("withheld_in_public_form")).any():
                result["errors"].append("Missing numeric value without an official withholding flag")
            if not frame["standard"].isin(["IFRS", "RAS"]).all() or not frame["unit"].isin(
                    ["rub_th", "rub_mn", "rub_bn", "rub", "pct", "customers"]).all():
                result["errors"].append("Unexpected reporting standard or financial unit")
        elif relative == CONTRACTS + "contracts_corpus.jsonl":
            check_contracts(frame, result)
        elif relative == CONTRACTS + "fx_clause_candidates.jsonl":
            check_candidates(run, frame, result)
        elif relative == CONTRACTS + "cuad_annotations.jsonl" and "original_span_aligned" in frame:
            bad = int(frame["original_span_aligned"].eq(False).sum())
            if bad:
                result["warnings"].append(f"{bad} publisher annotation spans do not exactly match raw context")
    run.state["quality"] = quality
    run.save()
    return len(errors) + sum(len(result["errors"]) for result in quality.values())
