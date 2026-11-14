"""Reproduce the audit, forecasts, reverse modelling and commercial comparisons."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import yaml

from bank_economics.investment import baseline, forecast, sweep

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/investment"


def table(name, rows):
    rows = list(rows)
    with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def value_break_even(function, lo, hi, reference=0):
    high = function(hi)
    if high < reference:
        return None
    if function(lo) >= reference:
        return lo
    for _ in range(34):
        middle = (lo + hi) / 2
        if function(middle) >= reference:
            hi = middle
        else:
            lo = middle
    return hi


def portfolio_rank(config, results):
    ranks = []
    weights = [config["ranking"]["weights"], *config["ranking"]["profiles"]]
    for i, vector in enumerate(weights):
        candidates = []
        for name, p in config["products"].items():
            r = results[name]["Base"]
            if not r["risk_pass"]:
                continue
            evidence, client, scaling, risk = config["ranking"]["factors"][name]
            financial = max(1, min(5, 3.8 + r["npv"] / 10 + r["years"][2]["irac"] / 12))
            investment = max(1, min(5, 5 - r["invest0"] / 5 - (1 if r["payback_months"] is None else 0)))
            speed = max(1, min(5, 7 - r["first_month"] / 2))
            factors = [financial, evidence, client, investment, speed, scaling, risk]
            candidates.append({"product": name, "score": sum(w * f for w, f in zip(vector, factors, strict=True)),
                               "gate": "financial_pass" if r["financial_pass"] else "pilot_only",
                               **dict(zip(("finance", "evidence", "client", "investment", "speed", "scale", "risk"), factors, strict=True))})
        ranks.extend({"weight_profile": i, "rank": j + 1, **r} for j, r in
                     enumerate(sorted(candidates, key=lambda r: (-r["score"], r["product"]))))
    return ranks


def costs_and_pilots(config, results):
    # This is the spend just to validate the channel, not a financial forecast.
    pilots = [
        {"pilot": "A", "duration_weeks": 6, "firms": 20, "cash_budget": 0.65,
         "one_time": 0.65, "capital": 0.0, "quote_count": 0, "case_starts": 12,
         "ticket": 0, "margin": 0, "incremental_share": 0, "paid_clients": 0, "monthly_price": 0, "paid_months": 0},
        {"pilot": "B", "duration_weeks": 12, "firms": 20, "cash_budget": 2.70,
         "one_time": 2.10, "capital": 1.50, "quote_count": 8, "case_starts": 12,
         "ticket": 30, "margin": 31, "incremental_share": 0.68, "paid_clients": 2, "monthly_price": 23, "paid_months": 2},
    ]
    for p in pilots:
        closes = p["quote_count"] * 0.5
        p["first_deals"] = closes
        p["fx_revenue"] = closes * p["ticket"] * p["incremental_share"] * p["margin"] / 10000
        p["premium_revenue"] = p["paid_clients"] * p["monthly_price"] * p["paid_months"] / 1000
        p["revenue"] = p["fx_revenue"] + p["premium_revenue"]
        p["net_spend_before_el"] = p["cash_budget"] - p["revenue"]
    cost_options = [
        ("Собственная платформа", "full"), ("API и канал ДБО", "dbo"),
        ("Ручная проверка и веб-форма", "lean"), ("Поэтапное подключение AI", "staged"),
    ]
    costs = []
    for label, pid in cost_options:
        r = results[pid]["Base"]
        collection = r["years"][0]
        before_sale = r["invest0"] + collection["fixed"] * (r["first_month"] - 1) / 12
        costs.append({"infrastructure": label, "product": pid, "cash_before_first_revenue": before_sale,
                      "initial_build": r["capex0"], "launch_expense": r["prelaunch_expense"],
                      "fixed_y1": collection["fixed"], "fixed_y3": r["years"][2]["fixed"],
                      "cash_tco36": r["tco"], "economic_tco36": r["tco_economic"]})
    staged = results["staged"]["Base"]
    for upfront, fee in [(0.7, 1.2), (1.2, 2.0), (1.7, 3.0)]:
        costs.append({"infrastructure": f"Внешний компонент, +{upfront} / +{fee} в год",
                      "product": "staged_vendor", "cash_before_first_revenue": costs[3]["cash_before_first_revenue"] + upfront + fee / 4,
                      "initial_build": staged["capex0"], "launch_expense": staged["prelaunch_expense"] + upfront,
                      "fixed_y1": staged["years"][0]["fixed"] + fee, "fixed_y3": staged["years"][2]["fixed"] + fee,
                      "cash_tco36": staged["tco"] + upfront + 3 * fee,
                      "economic_tco36": staged["tco_economic"] + upfront + 3 * fee})
    table("cost_configurations", costs)
    table("pilot_budget", pilots)
    return costs, pilots


def main():
    config = yaml.safe_load((ROOT / "configs/investment.yaml").read_text(encoding="utf-8"))
    v2, bridge, interventions, hurdles = baseline(yaml.safe_load((ROOT / "configs/economics_assumptions.yaml").read_text(encoding="utf-8")))
    OUT.mkdir(parents=True, exist_ok=True)
    results = {p: {case: forecast(config, p, case) for case in config["cases"]} for p in config["products"]}
    shortlist = ["staged", "hybrid", "high_turnover", "lean"]
    grid = list(sweep(config, shortlist))
    table("reverse_search", grid)
    grid_counts = {p: dict(Counter("strict" if r["hard_pass"] else "pass" if r["pass"] else "fail"
                                  for r in grid if r["product"] == p)) for p in shortlist}
    segments = []
    for s, definitions in config["segments"].items():
        r = forecast(config, "staged", segment_id=s)
        y = r["years"][2]
        segmented_margin = y["contribution"] - y["capital_charge"]
        serv = y["servicing"] + y["cac"]
        segments.append({"segment": s, "label": definitions["label"], "market_status": "CRM required",
                         "reach_limit": definitions["reach_limit"], "npv": r["npv"], "irac": y["irac"],
                         "deals": y["inc_deals"], "ticket": y["ticket"], "margin_bps": y["margin"], "paid_pct": y["paid_fraction"],
                         "unit": y["unit"], "cac_plus_service": serv,
                         "cac_per_client": y["cac_per_client"],
                         "contribution_per_cost": segmented_margin / serv if serv else None})
    tariffs = []
    for t, definitions in config["pricing"].items():
        r = forecast(config, "staged", tariff_id=t)
        y = r["years"][2]
        has_price = definitions["monthly"] or definitions["usage_price"] or definitions["bundle_price"]
        def at_price(factor):
            return forecast(config, "staged", tariff_id=t, changes={"price": factor})["npv"]
        price_threshold = value_break_even(at_price, 0, 4) if has_price else None
        tariffs.append({"pricing": t, "label": definitions["label"], "npv": r["npv"], "irac": y["irac"],
                        "arpa_k": y["pricing_arpa"] * 1000 if y["pricing_arpa"] is not None else None,
                        "arpu_k": y["revenue_arpu"] * 1000 if y["revenue_arpu"] else None, "margin": y["margin_contribution"],
                        "cac_k": y["cac_per_client"] * 1000 if y["cac_per_client"] else None,
                        "ltv_k": y["ltv"] * 1000 if y["ltv"] is not None else None, "ltv_cac": y["ltv_cac"],
                        "cac_payback": y["acquisition_payback"], "retention": y["retention"], "churn": 1 - y["retention"],
                        "paid": y["paid_fraction"], "deals": y["inc_deals"], "price_threshold": price_threshold})
    stresses = []
    for p in shortlist:
        for key, (name, overrides) in config["stresses"].items():
            edits = dict(overrides)
            if key == "margin_down20":
                edits["margin_delta"] = -0.2 * config["segments"][config["products"][p]["segment"]]["margin"]
            result = forecast(config, p, changes=edits)
            years = result["years"]
            current_margin = config["segments"][config["products"][p]["segment"]]["margin"]
            def with_margin(bps):
                return forecast(config, p, changes={**edits, "margin_delta": bps - current_margin})["npv"]
            threshold = value_break_even(with_margin, 0, 200)
            stresses.append({"product": p, "stress": key, "label": name, "npv": result["npv"], "payback": result["payback_months"],
                             "funding": result["peak_funding"], "irac27": years[0]["irac"], "irac28": years[1]["irac"],
                             "irac29": years[2]["irac"], "op27": years[0]["operating"], "op28": years[1]["operating"],
                             "op29": years[2]["operating"], "capital": result["capital_peak"],
                             "risk": result["risk_pass"], "margin_to_npv_zero_bps": threshold})
    frontier = []
    margin = config["segments"]["recurring"]["margin"]
    for h in (0.7, 0.85, 1.0, 1.15, 1.30, 1.5):
        for bps in (21, 26, 31, 36, 41, 46, 51):
            changes = {"reach": h, "margin_delta": bps - margin}
            r = forecast(config, "staged", changes=changes)
            frontier.append({"reach": h, "margin": bps, "npv": r["npv"], "gate": r["financial_pass"]})
    reach_slice = [{"multiplier": value / 100, "npv": forecast(config, "staged", changes={"reach": value / 100})["npv"]}
                   for value in range(50, 171)]
    first_base = results["staged"]["Base"]
    pairs = [
        ("Чистая FX-маржа, ±5 б.п.", {"margin_delta": -5}, {"margin_delta": 5}),
        ("Цена аналитики, ±20%", {"price": 0.8}, {"price": 1.2}),
        ("Стоимость сопровождения, ±20%", {"service": 1.2}, {"service": 0.8}),
        ("Средний номинал, ±15%", {"ticket": 0.85}, {"ticket": 1.15}),
        ("Конверсия сделки, ±20%", {"close": 0.8}, {"close": 1.2}),
        ("Начальные вложения и CAPEX, ±20%", {"capex": 1.2}, {"capex": 0.8}),
        ("Охват, ±15%", {"reach": 0.85}, {"reach": 1.15}),
        ("Повторы, ±15%", {"repeat": 0.85}, {"repeat": 1.15}),
    ]
    tornado = [{"label": label, "low_npv": forecast(config, "staged", changes=low)["npv"],
                "high_npv": forecast(config, "staged", changes=high)["npv"]} for label, low, high in pairs]
    market = Counter()
    market_path = ROOT / "data/snapshot/economics/fx_derivatives_market.csv"
    with market_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row["indicator"], row["participant_scope"], row["instrument"]) != ("otc_deals_count", "corporate", "fx_forward_and_ndf"):
                continue
            year, month, _ = map(int, row["period_start"].split("-"))
            if month <= 6 and year in (2025, 2026):
                market[year] += int(float(row["value"]))
    reverse = {
        "margin_bps": value_break_even(lambda bps: forecast(config, "staged", changes={"margin_delta": bps - margin})["npv"], 15, 65),
        "reach_multiplier": next((row["multiplier"] for row in reach_slice if row["npv"] >= 0), None),
        "best_reach_only": max(reach_slice, key=lambda row: row["npv"]),
        "tariff_multiplier": value_break_even(lambda mult: forecast(config, "staged", changes={"price": mult})["npv"], 0, 4),
        "max_capex_multiplier": None,
    }
    cut = value_break_even(lambda reduction: forecast(config, "staged", changes={"capex": 1 - reduction})["npv"], 0, 1)
    if cut is not None:
        reverse["max_capex_multiplier"] = 1 - cut
    steps = []
    improvements = [
        ("Контакт", "contact", 4, 0, "Маркер ВЭД в CRM и список с согласием"),
        ("Активация", "active", 5, -5, "Короткая форма карточки и проверка данных менеджером"),
        ("Подтверждение", "confirm", 6, -10, "Шаблон полей, место в договоре, контроль срока фиксации"),
        ("Рекомендация", "recommend", 4, -5, "Чек-лист естественного покрытия и остатка"),
        ("Запрос котировки", "rfq", 5, -4, "Передача структурированного запроса из карточки"),
        ("Исполнимая котировка", "quote", 8, -5, "SLA казначейства и предварительный контроль лимита"),
        ("Первая сделка", "close", 6, -8, "Контакт после котировки и код причины отказа"),
        ("Повторные сделки", "repeat_share", 6, -3, "Напоминание о подтверждённом транше"),
        ("Платящие", "paid", 6, 0, "Демонстрация календаря и платного отчёта"),
        ("Удержание", "retained", 5, -3, "Месячный обзор позиции и следующего транша"),
    ]
    for label, field, person_days, minutes, action in improvements:
        group = config["shared"] if field in {"quote", "recommend"} else config["segments"]["recurring"]
        before = group[field]
        after = min(1, before + 0.05)
        group[field] = after
        scenario = forecast(config, "staged")
        group[field] = before
        action_cost = person_days * 0.015
        gross_delta = scenario["npv"] - first_base["npv"]
        steps.append({"stage": label, "before": before, "after": after, "action": action, "person_days": person_days,
                      "time_minutes_assumption": minutes, "one_off_cost_mln": action_cost, "delta_npv": gross_delta,
                      "net_delta_npv": gross_delta - action_cost,
                      "delta_2029_revenue": scenario["years"][2]["revenue"] - first_base["years"][2]["revenue"],
                      "delta_first": scenario["years"][2]["first_traders"] - first_base["years"][2]["first_traders"]})
    ranks = portfolio_rank(config, results)
    costs, pilots = costs_and_pilots(config, results)
    table("baseline_npv_bridge", ({"component": k, "pv_mln": v} for k, v in bridge.items()))
    table("annual_scenarios", ({"product": p, "scenario": case, **r} for p, scenarios in results.items()
                                for case, approved in scenarios.items() for r in approved["years"]))
    table("concepts", ({"product": p, "case": case, **{k: v for k, v in r.items() if k not in ("years", "cash")}}
                     for p, cases in results.items() for case, r in cases.items()))
    for name, rows in [("tariffs", tariffs), ("segments", segments), ("stress", stresses),
                       ("break_even_frontier", frontier), ("funnel_sensitivity", steps), ("rankings", ranks),
                       ("reach_only", reach_slice), ("tornado", tornado)]:
        table(name, rows)
    credit = forecast(config, "trade", finance=True)
    combinations = {
        "minimum_trigger": {"margin_delta": 2.0},
        "guarded_pivot": {"margin_delta": 5.0, "service": 0.9, "capex": 0.95},
        "guarded_pivot_stressed": {"margin_delta": 5.0, "service": 1.1, "capex": 0.95, "close": 0.75, "paid": 0.6},
    }
    gated_variants = {key: forecast(config, "staged", changes=edit) for key, edit in combinations.items()}
    workbook_sensitivity = [
        {"margin_delta": margin, "price_delta": price,
         "npv": forecast(config, "staged", changes={"margin_delta": margin, "price": 1 + price})["npv"]}
        for margin in (-5, 0, 5) for price in (-0.2, 0, 0.2)
    ]
    data = {"config": config, "baseline": v2, "bridge": bridge, "v2_steps": interventions,
            "v2_thresholds": hurdles, "results": results, "segments": segments, "tariffs": tariffs, "stresses": stresses,
            "frontier": frontier, "reverse": reverse, "sweep_counts": grid_counts,
            "strict_best": sorted([r for r in grid if r["hard_pass"]], key=lambda r: -r["npv"])[:5],
            "feasible_best": {p: max((r for r in grid if r["product"] == p and r["pass"]), key=lambda r: r["npv"], default=None)
                              for p in shortlist},
            "rankings": ranks, "funnel_steps": steps, "credit_upside": credit, "costs": costs, "pilots": pilots,
            "workbook_sensitivity": workbook_sensitivity, "gated_variants": gated_variants, "market": dict(market), "tornado": tornado}
    (OUT / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str, allow_nan=False),
                                     encoding="utf-8")
    print("8 configurations x 3 cases, 6 tariffs, 5 segments,", len(grid), "reverse grid rows.")
    print("V2", round(v2["Base"]["npv"], 2), "staged base", round(first_base["npv"], 2),
          "thresholds", reverse, "grid", grid_counts)
    print("Rank:", [(x["product"], round(x["score"], 2)) for x in ranks if x["weight_profile"] == 0])


if __name__ == "__main__":
    main()
