"""Reproduce HedgeLab and the workbook-to-CBR reconciliation on frozen data."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import yaml

from hedgelab.research import STRATEGIES, load_rates, official_changes, simulate, summarize

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/snapshot"
TABLES = ROOT / "output/hedgelab"

def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, strict=True))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def spot_analysis(rates, config):
    summary, samples = [], []
    for ccy, series in sorted(rates.items()):
        for horizon in config["horizons"]:
            observations = list(official_changes(series, horizon, config["max_calendar_gap"],
                                                 config["start"], config["end"]))
            partitions = {
                "all": observations,
                "2019_2021": [r for r in observations if r[0] < date(2022, 1, 1)],
                "2022": [r for r in observations if r[1] >= date(2022, 1, 1) and r[0] < date(2023, 1, 1)],
                "pre_june_2024": [r for r in observations if r[1] >= date(2023, 1, 1) and r[0] < config["post_venue_change"]],
                "post_june_2024": [r for r in observations if r[1] >= config["post_venue_change"]],
            }
            for group, values in partitions.items():
                changes = [r[2] for r in values]
                q05, mid, q95 = np.percentile(changes, [5, 50, 95])
                low, high = min(values, key=lambda r: r[2]), max(values, key=lambda r: r[2])
                summary.append({
                    "currency": ccy, "horizon_days": horizon, "regime": group, "windows": len(values),
                    "p05_pct": 100 * q05, "median_pct": 100 * mid, "p95_pct": 100 * q95,
                    "min_pct": 100 * low[2], "min_start": low[1], "min_end": low[0],
                    "max_pct": 100 * high[2], "max_start": high[1], "max_end": high[0],
                })
            samples.extend({"currency": ccy, "horizon_days": horizon, "start": start,
                            "end": end, "return_pct": 100 * change}
                           for end, start, change in observations)
    write_csv(TABLES / "spot_historical_changes.csv", summary)
    return summary, samples


def hedge_analysis(rates, config):
    profiles = config["scenarios"]
    template = profiles[0]
    profiles = profiles + [{"id": f"importer_{ccy.lower()}", "currency": ccy,
                            "payable": template["payable"], "receivable": 0}
                           for ccy in ("USD", "EUR")]
    all_rows, metrics = [], []
    for profile in profiles:
        ccy = profile["currency"]
        exposure = profile["receivable"] - profile["payable"]
        for horizon in config["horizons"]:
            rows = list(simulate(rates[ccy], exposure, horizon, config))
            groups = defaultdict(list)
            complete_dates = set.intersection(*(set(r["entry_date"] for r in rows if r["strategy"] == s)
                                                for s in STRATEGIES))
            for row in rows:
                if row["entry_date"] not in complete_dates:
                    continue
                groups["all", row["strategy"]].append(row)
                groups[row["split"], row["strategy"]].append(row)
                groups[row["regime"], row["strategy"]].append(row)
                all_rows.append({"scenario": profile["id"], "currency": ccy, **row})
            bases = {group: summarize(group_rows, config["tail_probability"])
                     for (group, strategy), group_rows in groups.items() if strategy == "unhedged"}
            for (group, strategy), group_rows in groups.items():
                stats = summarize(group_rows, config["tail_probability"])
                base = bases[group]
                metrics.append({
                    "scenario": profile["id"], "currency": ccy, "horizon_days": horizon, "group": group,
                    "strategy": strategy, **stats,
                    "mean_loss_vs_budget_rub": float(np.mean([r["loss_vs_budget_rub"] for r in group_rows])),
                    "mean_payment_rub": -stats["mean_cash_flow_rub"] if exposure < 0 else None,
                    "change_in_mean_cash_flow_rub": stats["mean_cash_flow_rub"] - base["mean_cash_flow_rub"],
                    "cvar_reduction_rub": base["cvar95_rub"] - stats["cvar95_rub"],
                    "worst_shortfall_reduction_rub": base["worst_shortfall_rub"] - stats["worst_shortfall_rub"],
                })
    write_csv(TABLES / "hedge_strategy_metrics.csv", metrics)
    write_csv(TABLES / "hedge_historical_windows.csv", all_rows)
    primary = template["currency"]
    costs = []
    for annual_bps in config["cost_sensitivity_bps"]:
        local = {**config, "annual_lock_cost_bps": annual_bps}
        for horizon in config["horizons"]:
            subset = list(simulate(rates[primary], -template["payable"], horizon, local))
            base = summarize([r for r in subset if r["strategy"] == "unhedged" and r["split"] == "test"])
            for strategy in STRATEGIES[:-1]:
                cohort = [r for r in subset if r["strategy"] == strategy and r["split"] == "test"]
                stats = summarize(cohort, config["tail_probability"])
                costs.append({"currency": primary, "horizon_days": horizon, "annual_cost_bps": annual_bps,
                              "additional_fee_bps": local["execution_fee_bps"], "strategy": strategy,
                              "cvar_reduction_rub": base["cvar95_rub"] - stats["cvar95_rub"], **stats})
    write_csv(TABLES / "hedge_cost_sensitivity.csv", costs)
    sizes = []
    for row in metrics:
        if row["scenario"] != "importer" or row["group"] != "test":
            continue
        for size in (250000, 1000000, 5000000):
            ratio = size / template["payable"]
            sizes.append({"horizon_days": row["horizon_days"], "notional_cny": size, "strategy": row["strategy"],
                          "cvar95_rub": ratio * row["cvar95_rub"], "worst_shortfall_rub": ratio * row["worst_shortfall_rub"],
                          "mean_model_cost_rub": ratio * row["mean_model_cost_rub"]})
    write_csv(TABLES / "hedge_notional_sensitivity.csv", sizes)
    return metrics


def rate_evidence(config):
    rows = pq.read_table(PROCESSED / "market/rub_interest_rates.parquet").to_pylist()
    quality = []
    for name in ("RUONIA", "CBR_KEY_RATE"):
        items = sorted([r for r in rows if r["rate_name"] == name and config["start"] <= r["date"] <= config["end"]],
                       key=lambda r: r["date"])
        if not items or len({r["date"] for r in items}) != len(items) or any(r["rate_unit"] != "pct_pa" for r in items):
            raise ValueError(f"Invalid rate observations: {name}")
        last = items[-1]
        quality.append({"series": name, "observations": len(items), "start": str(items[0]["date"]),
                        "end": str(last["date"]), "last_pct_pa": last["rate"],
                        "missing_publication": sum(r["publication_date"] is None for r in items),
                        "published_after_cut": sum(r["publication_date"] is not None and
                                                   r["publication_date"] > config["end"] for r in items),
                        "max_gap_days": max((r2["date"] - r1["date"]).days for r1, r2 in zip(items[:-1], items[1:], strict=True)),
                        "source": last["source"]})
    return quality


def reconcile():
    base = PROCESSED / "economics"
    shares = csv_rows(base / "foreign_trade_currency_structure.csv")
    market = csv_rows(base / "fx_derivatives_market.csv")
    checks = csv_rows(ROOT / "data/snapshot/source_reconciliation.csv")
    sheet_map = {"FX доля в экспорте": "export", "FX доля в импорте": "import", "OTC сделки табл": "otc"}
    if not checks or any(row["result"] != "match" for row in checks):
        raise ValueError("The reconciliation contains an unresolved detail")
    expected = Counter()
    for row in checks:
        series, indicator = sheet_map[row["sheet"]], row["indicator"]
        # The case workbook assigns rows 4–11 to the four pairs of corporate and retail values.
        scope = ("corporate" if int(row["cell"].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) % 2 == 0 else "retail"
                 ) if series == "otc" else "Всего"
        expected[series, row["date"], indicator, scope, Decimal(row["official_value"])] += 1
    records = []
    for r in shares:
        if r["geography"] == "Всего" and r["frequency"] == "month" and r["indicator"] == "settlement_currency_share":
            records.append((r["direction"], r["period_end"], r["currency_group"], r["geography"], r))
    for r in market:
        if r["measure_type"] == "deal_count" and r["participant_scope"] in {"corporate", "retail"}:
            records.append(("otc", r["period_start"], r["instrument"], r["participant_scope"], r))
    actual = Counter((series, day, indicator, scope, Decimal(r["value"])) for series, day, indicator, scope, r in records)
    if actual != expected or not all(r["source"].startswith("https://www.cbr.ru/") for *_, r in records):
        raise ValueError("The official rows cannot reproduce the case reconciliation")
    out = [{"series": series, "date": day, "indicator": indicator, "scope": scope,
            "official_value": r["value"], "unit": r["unit"], "result": "match", "source_id": r["source_id"],
            "source_url": r["source"], "source_sha256": r["source_sha256"],
            "source_sheet": r["sheet"], "source_cell": r["cell"]}
           for series, day, indicator, scope, r in sorted(records, key=lambda x: x[:4])]
    write_csv(TABLES / "source_reconciliation.csv", out)
    return dict(Counter(r["series"] for r in out))


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((ROOT / "configs/research_scenarios.yaml").read_text(encoding="utf-8"))
    rates, _ = load_rates(PROCESSED / "market/fx_spot_daily.csv")
    spot, _ = spot_analysis(rates, config)
    hedges = hedge_analysis(rates, config)
    write_csv(TABLES / "rub_interest_rates_quality.csv", rate_evidence(config))
    matched = sum(reconcile().values())
    test = [r for r in hedges if r["scenario"] == "importer" and r["horizon_days"] == 30
            and r["group"] == "test" and r["strategy"] in {"unhedged", "fixed_50"}]
    print(f"HedgeLab: {len(hedges)} strategy summaries, {len(spot)} spot summaries, {matched} verified case points.")
    for row in test:
        print(f'{row["strategy"]}: {row["windows"]} windows, CVaR95 {row["cvar95_rub"]:,.2f} RUB')


if __name__ == "__main__":
    main()
