"""Audit the published workbook and the pilot cash and risk decisions."""

from __future__ import annotations

import csv
import hashlib
import math
from copy import deepcopy
from itertools import accumulate
from pathlib import Path

import openpyxl
import yaml

from bank_economics.investment import forecast
from bank_economics.model import valuation

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "output/investment"
MODEL = ROOT / "models/BSPB_FX_Control_Investment_Model_v3_1.xlsx"
MODEL_SHA = "f1e51ab82e825915d81648744ff9662ba83593c79802e3282b4f1c9c0901650a"
PILOT_SPLIT = {
    # Control allocation of each approved envelope. Bank accounting assigns actual cost IDs at kickoff.
    # Values: initial build, initial integration, initial infosec, initial preparation,
    #         year 1 acquisition, customer servicing, incremental trade ops, paid product ops, fixed.
    "scope": (0, 0, 0, .10, 0, 0, 0, 0, 0),
    "controls": (0, 0, .18, 0, 0, 0, 0, 0, 0),
    "list": (0, 0, 0, .08, 0, 0, 0, 0, 0),
    "pilot_a": (0, 0, .10, .19, 0, 0, 0, 0, 0),
    "mvp": (1.25, 0, 0, 0, 0, 0, 0, 0, 0),
    "pilot_b": (0, .50, .22, .03, .05, .05, .02176, .02824, 0),
    "income": (0, 0, 0, 0, 0, 0, 0, 0, 0),
    "unit": (0, 0, .10, 0, 0, .10, 0, 0, .20),
    "committee": (0, 0, 0, 0, 0, 0, 0, 0, .15),
}
BUCKETS = ("initial_build", "initial_integration", "initial_security",
           "initial_setup", "opex_acquisition", "opex_service", "opex_trades",
           "opex_premium", "opex_fixed")


def close(actual, expected, label):
    if actual is None or expected is None:
        assert actual is expected, (label, actual, expected)
        return
    assert math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-7), (label, actual, expected)


def write_csv(name, rows):
    with (TABLES / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def check_funding(config, base):
    roadmap = yaml.safe_load((ROOT / "configs/pilot_roadmap.yaml").read_text(encoding="utf-8"))
    y = base["years"][0]
    p = config["products"]["staged"]
    ceilings = (p["build"], p["integration"], p["security"], p["setup"],
                y["cac"], y["servicing"], y["trading_ops"], y["pricing_ops"], y["fixed"])
    rows = []
    for work in roadmap["workstreams"]:
        key = work["id"]
        if work["phase"] not in {"A", "B"}:
            continue
        amounts = PILOT_SPLIT[key]
        close(sum(amounts), work["cost"], key)
        rows.append({"work_id": key, "phase": work["phase"], "work": work["label"],
                     "start_month": work["start"], "end_month": work["end"],
                     "stage_cash_m_rub": work["cost"], **dict(zip(BUCKETS, amounts, strict=True)),
                     "t0_m_rub": round(sum(amounts[:4]), 6),
                     "opex_2027_m_rub": round(sum(amounts[4:]), 6),
                     "new_cash_modelled_m_rub": 0.,
                     "basis": "control allocation, actual cost IDs pending"})
    applied = tuple(sum(row[k] for row in rows) for k in BUCKETS)
    for bucket, amount, ceiling in zip(BUCKETS, applied, ceilings, strict=True):
        assert amount <= ceiling + 1e-9, (bucket, amount, ceiling)
    close(sum(r["stage_cash_m_rub"] for r in rows if r["phase"] == "A"), .65, "Pilot A")
    close(sum(r["stage_cash_m_rub"] for r in rows if r["phase"] == "B"), 2.70, "Pilot B")
    close(sum(applied[:4]), base["invest0"], "A/B t0 covered")
    close(sum(applied[4:]), .60, "A/B operating subset")
    write_csv("pilot_budget_crosswalk.csv", rows)
    write_csv("pilot_budget_ceiling_checks.csv", [
        {"bucket": k, "v3_ceiling_m_rub": limit, "assigned_m_rub": round(a, 6),
         "remaining_m_rub": round(limit - a, 6),
         "retiming": "economic category t0 despite later disbursement" if i < 4 else "in-year cash OPEX allocation"}
        for i, (k, limit, a) in enumerate(zip(BUCKETS, ceilings, applied, strict=True))
    ])

    with (TABLES / "pilot_budget.csv").open(encoding="utf-8-sig", newline="") as stream:
        pilot_b = next(row for row in csv.DictReader(stream) if row["pilot"] == "B")
    n = float(pilot_b["quote_count"]) * .5
    ticket = float(pilot_b["ticket"])
    incremental_share = float(pilot_b["incremental_share"])
    margin = float(pilot_b["margin"])
    px = float(pilot_b["monthly_price"])
    paid = float(pilot_b["paid_clients"])
    months = float(pilot_b["paid_months"])
    fx = n * ticket * incremental_share * margin / 10000
    premium = paid * px * months / 1000
    gross = n * ticket
    close(fx + premium, float(pilot_b["revenue"]), "Pilot B recognized revenue")
    close(2.7 - fx - premium, float(pilot_b["net_spend_before_el"]), "B envelope less recognized revenue")
    incremental_ops = n * incremental_share * p["ops_trade"] / 1000
    close(incremental_ops, PILOT_SPLIT["pilot_b"][6], "illustrative accounting allocation to trade ops")
    # Risk test for simultaneous outstanding trades. Scope includes all pilot trades for limit and risk approval.
    segment = config["segments"]["recurring"]
    overlap_ead = gross * segment["ead_factor"]
    overlap_cap = overlap_ead * segment["capital_factor"]
    b_limit = float(pilot_b["capital"])
    max_nominal = b_limit / segment["capital_factor"] / segment["ead_factor"]
    assert overlap_cap > b_limit
    write_csv("pilot_commercial_checks.csv", [
        {"measure": name, "value": value, "unit": unit, "basis": description}
        for name, value, unit, description in [
            ("quotes", float(pilot_b["quote_count"]), "count", "B design"),
            ("trades", n, "count", "quotes x 50%"),
            ("gross_notional", gross, "million RUB", "trades x ticket"),
            ("incremental_notional", gross * incremental_share, "million RUB", "gross x 68%; hypothesis, compare with control"),
            ("recognized_fx", fx, "million RUB", "incremental notional x 31 bps"),
            ("recognized_premium", premium, "million RUB", "2 clients x 23,000 RUB x 2 months"),
            ("revenue_total", fx + premium, "million RUB", "before collection and EL"),
            ("envelope_less_revenue", 2.7 - fx - premium, "million RUB", "budget minus recognized revenue; cash depends on collections"),
            ("pilot_capital_limit", b_limit, "million RUB", "project hypothesis"),
            ("capital_full_overlap", overlap_cap, "million RUB", "gross open notional x 8% EAD proxy x 24% capital factor"),
            ("max_open_gross_at_pilot_cap", max_nominal, "million RUB", "1.5 / (8% x 24%), proxy"),
            ("simultaneous_30m_tickets_max", math.floor(max_nominal / ticket), "count", "risk proxy, bank approves actual limits"),
        ]
    ])


def stress_rows(config):
    s = config["segments"]["recurring"]
    p = config["products"]["staged"]
    annual_top3 = p["weight_limit"]
    cases = [
        ("conservative", "Conservative", {}, None),
        ("base", "Base", {}, None),
        ("optimistic", "Optimistic", {}, None),
        ("no_premium", "Base", config["stresses"]["no_premium"][1], None),
        ("margin_down20", "Base", config["stresses"]["margin_down20"][1], None),
        ("no_premium_and_margin_down20", "Base", {"paid": 0, "margin_delta": -s["margin"]*.2}, None),
        ("capital_factor_up30", "Base", config["stresses"]["capital_up30"][1], None),
        ("capital_buffer_10pct", "Base", {}, None),
        ("one_incremental_cost_t0_0_60", "Base", {}, .60),
        ("one_incremental_cost_y1_0_60", "Base", {}, -.60),
        ("margin_plus2_bps", "Base", {"margin_delta": 2}, None),
        ("margin_plus5_cost_actions", "Base", {"margin_delta": 5, "service": .90, "capex": .95}, None),
        ("cost_actions_stressed", "Base", {"margin_delta": 5, "service": 1.10,
                                           "capex": .95, "close": .75, "paid": .60}, None),
    ]
    rows = []
    for case_id, case, changes, extra in cases:
        case_config = config
        if case_id == "capital_buffer_10pct":
            case_config = deepcopy(config)
            case_config["products"]["staged"]["capital_limit"] = p["capital_limit"] * .90
        r = forecast(case_config, "staged", case, changes=changes)
        ys = r["years"][:3]
        cf = r["cash"][:4]
        if extra is not None:
            # Cash-only sensitivity for a confirmed budget overrun, without a tax/IRAC credit.
            if extra > 0:
                cf[0] -= extra
            else:
                cf[1] += extra
        metrics = valuation(cf, [config["shared"]["discount"]] * 3)
        rows.append({"case_id": case_id, "scenario": case, "margin_bps": ys[0]["margin"],
                     "paid_fraction": ys[0]["paid_fraction"], "t0_m_rub": -cf[0],
                     "fcf_2027_m_rub": cf[1], "fcf_2028_m_rub": cf[2], "fcf_2029_m_rub": cf[3],
                     "npv36_m_rub": metrics["npv"], "irr36": metrics["irr"],
                     "simple_payback_months": metrics["payback_months"],
                     "net_funding_peak_annual_points_m_rub": -min(accumulate(cf)),
                     "revenue_2029_m_rub": ys[-1]["revenue"], "ebit_2029_m_rub": ys[-1]["operating"],
                     "irac_2029_ex_cash_only_shock_m_rub": ys[-1]["irac"],
                     "capital_peak_m_rub": r["capital_peak"], "operating_cap_m_rub": r["capital_limit"],
                     "top3_2027_proxy": ys[0]["largest_share"], "top3_2029_proxy": ys[-1]["largest_share"],
                     "all_3_years_top3_within_limit": max(y["largest_share"] for y in ys) <= annual_top3,
                     "bank_gates": "pending"})
    return rows


def reproduce():
    config = yaml.safe_load((ROOT / "configs/investment.yaml").read_text(encoding="utf-8"))
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == MODEL_SHA
    expect = {"Conservative": -14.033217348681585, "Base": -.7301951873115757,
              "Optimistic": 7.644305238730088}
    results = {c: forecast(config, "staged", c) for c in expect}
    wb = openpyxl.load_workbook(MODEL, data_only=True)
    scenarios = wb["Scenario Comparison"]
    dash = wb["Executive Dashboard"]
    assert (dash["D10"].value, dash["E10"].value) == ("staged", "Base")
    baseline = results["Base"]
    rate = config["shared"]["discount"]
    for result_name, result in results.items():
        matching = [i for i in range(24, scenarios.max_row+1)
                    if scenarios.cell(i, 3).value == config["products"]["staged"]["label"]
                    and scenarios.cell(i, 4).value == result_name]
        assert len(matching) == 1, result_name
        i = matching[0]
        assert "NPV 36" in str(scenarios["G23"].value)
        close(scenarios.cell(i, 7).value, result["npv"], result_name + " Workbook NPV")
        close(result["npv"], expect[result_name], result_name + " Frozen NPV")
        close(sum(cf / (1+rate)**t for t, cf in enumerate(result["cash"][:4])),
              result["npv"], result_name + " PV identity")
    cash = wb["NPV & IRR"]
    for cell, val in {"D10": baseline["npv"], "D11": baseline["irr"],
                      "D12": baseline["payback_months"], "D14": baseline["peak_funding"]}.items():
        close(cash[cell].value, val, cell)
    for m, v in {"D8": baseline["capex0"], "D9": baseline["prelaunch_expense"]}.items():
        close(wb["CAPEX"][m].value, v, m)
    close(wb["Cash Flow"]["D14"].value, -baseline["invest0"], "initial cash")
    assert dash["D24"].value == baseline["first_month"]
    labels = {16:"revenue", 17:"cash_opex", 18:"operating", 19:"irac", 20:"cash", 21:"capital"}
    detail = []
    for col, y in zip("DEF", baseline["years"][:3], strict=True):
        for row, field in labels.items():
            close(dash[f"{col}{row}"].value, y[field], col+field)
        tie = {
            "FX Revenue": {7:"margin", 8:"cannibal", 12:"turnover", 13:"gross_fx", 14:"displaced_fx",
                           15:"fx", 16:"unserved_fx"},
            "Subscription Revenue": {6:"paid_fraction", 8:"paid_months", 9:"subs"},
            "Additional Revenue": {7:"extra"},
            "Capital & Risk": {8:"ead", 9:"el", 10:"capital", 11:"capital_charge", 12:"largest_share"},
            "Financial Statements": {12:"tax", 15:"irac"},
            "Cash Flow": {7:"dep", 8:"reinvest", 9:"nwc", 10:"delta_nwc", 11:"cash"},
        }
        for sheet, check in tie.items():
            for row, field in check.items():
                close(wb[sheet][f"{col}{row}"].value, y[field], sheet+col+field)
        close(y["gross_fx"]-y["displaced_fx"]-y["unserved_fx"], y["fx"], "FX identity")
        close(y["fx"] + y["subs"], y["revenue"], "two revenue lines")
        close(y["operating"]+y["dep"]-y["tax"]-y["reinvest"]-y["delta_nwc"], y["cash"], "cash identity")
        fields = ("year", "contacted", "active", "quotes", "inc_deals", "turnover", "gross_fx",
                  "displaced_fx", "unserved_fx", "fx", "subs", "revenue", "cash_opex",
                  "ead", "el", "capital", "capital_charge", "largest_share", "operating",
                  "irac", "tax", "nwc", "delta_nwc", "dep", "reinvest", "cash")
        detail.append({f: y[f] for f in fields})
    write_csv("financial_base_annual.csv", detail)
    rows = stress_rows(config)
    write_csv("financial_audit_scenarios.csv", rows)

    gates = wb["Break-even"]
    margin = gates["D13"].value
    premium_factor = gates["D14"].value
    capex = gates["D15"].value
    thresholds = []
    for case_id, changes, val, unit in [
        ("npv_zero_fx_margin", {"margin_delta": margin-31}, margin, "bps"),
        ("npv_zero_premium_price", {"price": premium_factor}, 23*premium_factor, "thousand RUB per month"),
        ("npv_zero_initial_and_capex_factor", {"capex": capex}, capex, "multiplier"),
    ]:
        at = forecast(config, "staged", changes=changes)
        close(at["npv"], 0., case_id)
        thresholds.append({"measure": case_id, "value": val, "unit": unit, "npv36_m_rub": at["npv"],
                           "irac_2029_m_rub": at["years"][2]["irac"], "payback_months": at["payback_months"]})
    write_csv("financial_thresholds.csv", thresholds)

    revisions = []
    for col, y in zip("DEFGH", baseline["years"], strict=True):
        # Risk-adjusted EBIT=0 at fixed mix. Capital is already deducted in unit; overhead allocation is separate.
        new = (y["cac"] + y["fixed"] + y["dep"] + y["allocation"]) / y["unit"]
        old = (y["cac"] + y["fixed"] + y["dep"] + y["capital_charge"]) / y["unit"]
        close(gates[f"{col}8"].value, new, "v3.1 threshold "+col)
        revisions.append({"sheet": "Break-even", "cell": col+"8", "year": y["year"],
                          "v3_active_entities": old, "v31_active_entities": new, "delta": new-old,
                          "v3_numerator": "CAC + cash fixed + depreciation + capital charge",
                          "v31_numerator": "CAC + cash fixed + depreciation + allocated capacity",
                          "denominator": "per-active contribution after EL and capital charge",
                          "impact_npv36_m_rub": 0., "impact_gate": "none, row 8 is explanatory"})
    write_csv("financial_workbook_diff.csv", revisions)
    check_funding(config, baseline)
    print(f"v3.1 SHA-256 {MODEL_SHA}. Three scenario NPV, Base cash/revenue/capital and the IRAC thresholds match.")
    print(f"2027-2029 cash TCO {baseline['tco']:.6f}, accounting allocation TCO {baseline['tco_economic']:.6f}")
    print(f"Gross fixed-only cash before first revenue {baseline['invest0']+(baseline['first_month']-1)*baseline['years'][0]['fixed']/12:.3f}")
    for row in rows:
        print(f"{row['case_id']:<36} NPV {row['npv36_m_rub']:+.6f}, IRAC29 {row['irac_2029_ex_cash_only_shock_m_rub']:+.6f}")
    print("Financial crosswalk, three financial thresholds and simultaneous pilot-capital stress verified.")


if __name__ == "__main__":
    TABLES.mkdir(parents=True, exist_ok=True)
    reproduce()
