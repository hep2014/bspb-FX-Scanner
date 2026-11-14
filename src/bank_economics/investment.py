"""Cohort-based, incremental business model for the seven FX Control options."""
from __future__ import annotations

from itertools import product
from math import isclose

from bank_economics.model import annual, valuation


def probability(p):
    return min(1.0, max(0.0, p))


def forecast(config, product_id, case="Base", *, segment_id=None, tariff_id=None, changes=None, finance=False):
    p = config["products"][product_id]
    s = config["segments"][segment_id or p["segment"]]
    t = config["pricing"][tariff_id or p["pricing"]]
    g = config["shared"]
    c = config["cases"][case]
    d = changes or {}
    cost = c["cost"] * d.get("opex", 1)
    capex_factor = c["cost"] * d.get("capex", 1)
    initial_build = (p["build"] + p["integration"]) * capex_factor
    initial_expense = (p["security"] + p["setup"]) * capex_factor
    first_month = p["first_month"] + c["delay"] + d.get("delay", 0)
    previous = {"active": 0.0, "traders": 0.0, "nwc": 0.0}
    capex_history, years = [initial_build], []
    pool = s["reach_limit"]
    for i, year in enumerate(config["years"]):
        ramp = max(0, min(1, (12 * (i + 1) + 1 - first_month) / 12))
        reach = min(pool, p["reach"][i] * c["reach"] * d.get("reach", 1) * ramp)
        pool -= reach
        contacted = reach * s["contact"]
        retention = probability(s["retained"] * t["retention_factor"] * c["retention"] * d.get("retention", 1))
        retained = min(p["capacity"][i], previous["active"] * retention)
        new_active = min(p["capacity"][i] - retained, contacted * probability(s["active"] * c["activation"]))
        active = retained + new_active
        confirmed = new_active * s["confirm"]
        advised = confirmed * g["recommend"]
        rfqs = advised * probability(s["rfq"] * c["to_quote"] * d.get("to_quote", 1))
        quotes = rfqs * g["quote"]
        first_traders = quotes * probability(s["close"] * c["close"] * d.get("close", 1)) * p["fx_factor"]
        rolling_traders = min(retained, previous["traders"] * retention)
        traders = first_traders + rolling_traders
        repeat_clients = traders * probability(s["repeat_share"] * c["repeat"] * d.get("repeat", 1))
        gross_deals = traders + repeat_clients * s["extra_deals"]
        ticket = s["ticket"] * c["ticket"] * d.get("ticket", 1)
        margin = max(0, s["margin"] * c["margin"] + d.get("margin_delta", 0))
        cannibal = probability(s["cannibal"] + c["cannibal_delta"] + d.get("cannibal_delta", 0))
        fx_cap_factor = s["maturity"] / 365 * s["ead_factor"] * s["capital_factor"] * c["capital"] * d.get("capital", 1)
        capacity_turnover = p["capital_limit"] / fx_cap_factor if fx_cap_factor > 0 else float("inf")
        demand_deals = gross_deals * (1 - cannibal)
        inc_deals = min(demand_deals, capacity_turnover / ticket) if p.get("limit_turnover") and ticket else demand_deals
        turnover = inc_deals * ticket
        gross_fx = gross_deals * ticket * margin / 10000
        displaced_fx = gross_fx * cannibal
        fx = turnover * margin / 10000
        unserved_fx = gross_fx - displaced_fx - fx

        paid_fraction = probability(s["paid"] * t["paid_factor"] * c["paid"] * d.get("paid", 1))
        paid = active * paid_fraction
        paid_months = paid_fraction * (new_active * g["paid_months_new"] * ramp + retained * g["paid_months_retained"])
        subs = paid_months * t["monthly"] * d.get("price", 1) / 1000
        usage = paid * t["usage_count"] * t["usage_price"] * d.get("price", 1) / 1000
        bundle = paid_months * t["bundle_price"] * (1 - t["displacement"]) * d.get("price", 1) / 1000
        # Credit referrals are assigned zero until attributed. The upside below uses an explicit scenario.
        credit_ead = active * g["credit_attach"] * g["credit_outstanding"] if finance and product_id == "trade" else 0.0
        extra = credit_ead * g["credit_income_rate"]
        revenue = fx + subs + usage + bundle + extra

        cac = contacted * s["cac"] * cost * d.get("cac", 1) / 1000
        servicing = active * s["service"] * p["service_factor"] * cost * d.get("service", 1) / 1000
        trading_ops = inc_deals * p["ops_trade"] * cost / 1000
        pricing_ops = paid * t["activity_cost"] * cost / 1000
        cash_fixed = (p["infra"] + p["staff"] + p["licenses"]) * (1 + g["annual_growth_cost"]) ** i * cost
        alloc = p["allocation"] * (1 + g["annual_growth_cost"]) ** i
        fx_ead = turnover * s["maturity"] / 365 * s["ead_factor"]
        ead = fx_ead + credit_ead
        el = fx_ead * s["pd"] * s["lgd"] + credit_ead * g["credit_pd"] * g["credit_lgd"]
        capital = (fx_ead * s["capital_factor"] + credit_ead * g["credit_capital_factor"]) * c["capital"] * d.get("capital", 1)
        capital_charge = capital * g["capital_hurdle"]

        reinvest = p["stage_capex"][i] * capex_factor
        capex_history.append(reinvest)
        amort = int(g["amort_years"])
        dep = (initial_build * (i < amort) + sum(capex_history[1:][max(0, i - amort + 1):])) / amort
        variable = servicing + trading_ops + pricing_ops
        contribution = revenue - variable - el
        operating = contribution - cac - cash_fixed - dep
        tax = max(0, operating) * g["tax"]
        irac = operating - alloc - capital_charge
        nwc = (subs + usage + bundle) * g["debtor_days"] / 365
        delta_nwc = nwc - previous["nwc"]
        cash = operating + dep - tax - reinvest - delta_nwc
        effective_traders = traders * inc_deals / demand_deals if demand_deals else 0
        largest_share = min(1, 3 / effective_traders) if effective_traders else 0
        unit = (contribution - capital_charge) / active if active else None
        per_cac = cac / new_active if new_active else None
        ltv = unit * sum((retention / (1 + g["discount"])) ** i for i in range(3)) if unit is not None else None

        annual_row = {
            "year": year, "ramp": ramp, "reach": reach, "remaining": pool, "contacted": contacted,
            "retained": retained, "new_active": new_active, "active": active, "confirmed": confirmed,
            "advised": advised, "rfqs": rfqs, "quotes": quotes, "first_traders": first_traders,
            "rolling_traders": rolling_traders, "traders": traders, "repeat_clients": repeat_clients,
            "gross_deals": gross_deals, "ticket": ticket, "margin": margin, "cannibal": cannibal,
            "inc_deals": inc_deals, "turnover": turnover, "gross_fx": gross_fx, "displaced_fx": displaced_fx,
            "unserved_fx": unserved_fx, "effective_traders": effective_traders,
            "fx": fx, "paid_fraction": paid_fraction, "paid": paid, "paid_months": paid_months, "subs": subs,
            "usage": usage, "bundle": bundle, "extra": extra, "revenue": revenue, "credit_ead": credit_ead,
            "cac": cac, "servicing": servicing, "trading_ops": trading_ops, "pricing_ops": pricing_ops,
            "variable": variable, "fixed": cash_fixed, "allocation": alloc, "ead": ead, "el": el,
            "capital": capital, "capital_charge": capital_charge, "largest_share": largest_share,
            "initial_build": initial_build, "initial_expense": initial_expense, "reinvest": reinvest, "dep": dep,
            "contribution": contribution, "operating": operating, "tax": tax, "irac": irac, "nwc": nwc,
            "delta_nwc": delta_nwc, "cash": cash, "retention": retention, "unit": unit, "cac_per_client": per_cac,
            "ltv": ltv, "ltv_cac": ltv / per_cac if per_cac and ltv is not None else None,
            "acquisition_payback": 12 * per_cac / unit if per_cac and unit and unit > 0 else None,
            "pricing_arpa": (subs + usage + bundle) / paid if paid else None,
            "revenue_arpu": revenue / active if active else None,
            "margin_contribution": contribution / revenue if revenue else None,
            "cash_opex": cac + variable + cash_fixed,
        }
        years.append(annual_row)
        previous = annual_row
    cash = [-initial_build - initial_expense, *(y["cash"] for y in years)]
    discounts = [g["discount"]] * len(years)
    results = valuation(cash[:4], discounts[:3])
    three = years[:3]
    cap = max(y["capital"] for y in three)
    contribution_pass = (three[-1]["unit"] or 0) > 0
    capital_pass = cap <= p["capital_limit"] + 1e-9
    concentration_pass = three[-1]["largest_share"] <= p["weight_limit"]
    financial_pass = (results["npv"] >= 0 and results["payback_months"] is not None
                      and three[-1]["irac"] > 0 and three[-1]["operating"] > 0
                      and contribution_pass and capital_pass and concentration_pass)
    cumulative = [sum(cash[:i + 1]) for i in range(len(cash))]
    return {
        "years": years, "cash": cash, **results, "capex0": initial_build, "prelaunch_expense": initial_expense,
        "invest0": -cash[0], "first_month": first_month, "peak_funding": max(0, -min(cumulative[:4])),
        "npv12": valuation(cash[:2], discounts[:1])["npv"], "npv24": valuation(cash[:3], discounts[:2])["npv"],
        "npv60": valuation(cash, discounts)["npv"], "cumulative24": cumulative[2],
        "risk_pass": capital_pass and concentration_pass, "capital_peak": cap, "capital_limit": p["capital_limit"],
        "concentration_limit": p["weight_limit"], "financial_pass": financial_pass,
        "hard_pass": financial_pass and three[0]["operating"] >= 0 and cumulative[2] >= 0,
        "tco": -cash[0] + sum(y["cash_opex"] + y["reinvest"] for y in three),
        "tco_economic": -cash[0] + sum(y["cash_opex"] + y["reinvest"] + y["allocation"] for y in three),
    }


def baseline(config):
    drivers = {d["id"]: d for d in config["drivers"]}
    result = {}
    for i, name in enumerate(config["cases"]):
        inputs = [{key: d["values"][i][y] for key, d in drivers.items()} for y in range(3)]
        rows = [annual(d) for d in inputs]
        discounts = [d["discount"] for d in inputs]
        cash = [-inputs[0]["launch_cost"], *(r["operating"] for r in rows)]
        result[name] = {"years": rows, "cash": cash, **valuation(cash, discounts)}
    inputs = [{key: d["values"][1][y] for key, d in drivers.items()} for y in range(3)]
    rows = result["Base"]["years"]
    costs = [d["discount"] for d in inputs]

    def pv(values):
        return valuation([0, *values], costs)["npv"]

    bridge = {"launch": -inputs[0]["launch_cost"], "fixed": -pv([r["fixed_cost"] for r in rows]),
              "servicing": -pv([r["service_cost"] for r in rows]), "execution": -pv([r["trade_ops"] for r in rows]),
              "loss": -pv([r["expected_loss"] for r in rows]), "premium": pv([r["premium_income"] for r in rows]),
              "gross_fx": pv([r["hedge_income"] / (1 - d["cannibalization"]) for d, r in zip(inputs, rows, strict=True)]),
              "cannibal": -pv([r["hedge_income"] / (1 - d["cannibalization"]) * d["cannibalization"]
                              for d, r in zip(inputs, rows, strict=True)])}
    assert isclose(sum(bridge.values()), result["Base"]["npv"], abs_tol=1e-8)
    functions = {
        "launch_zero": lambda d: {"launch_cost": 0}, "fixed_minus_25": lambda d: {"fixed_cost": 0.75 * d["fixed_cost"]},
        "reach_plus_25": lambda d: {"targeted": 1.25 * d["targeted"]},
        "ticket_plus_25": lambda d: {"ticket": 1.25 * d["ticket"]},
        "deals_plus_25": lambda d: {"repeat_deals": 1.25 * d["repeat_deals"]},
        "paid_plus_25": lambda d: {"premium": 1.25 * d["premium"]},
        "mar_plus_20": lambda d: {"margin_bps": d["margin_bps"] + 20},
        "conversion_plus_10": lambda d: {"conversion": d["conversion"] + 0.10},
        "cannibal_zero": lambda d: {"cannibalization": 0},
    }
    counterfactuals = {}
    for name, change in functions.items():
        altered = [{**d, **change(d)} for d in inputs]
        cf = [-altered[0]["launch_cost"], *(annual(d)["operating"] for d in altered)]
        counterfactuals[name] = valuation(cf, costs)["npv"] - result["Base"]["npv"]
    metrics = {
        "flat_margin_bps": (bridge["gross_fx"] + bridge["cannibal"] - result["Base"]["npv"]) /
        pv([r["turnover"] / 10000 for r in rows]),
        "annual_fixed_cut": -result["Base"]["npv"] / -bridge["fixed"],
        "reach_multiplier": 1 - result["Base"]["npv"] / pv([r["contribution"] for r in rows]),
        "ticket_multiplier": 1 - result["Base"]["npv"] / pv([r["hedge_income"] - r["expected_loss"] for r in rows]),
        "paid_multiplier": 1 - result["Base"]["npv"] / bridge["premium"],
        "combined_v2_npv": valuation([-inputs[0]["launch_cost"], *(
            annual({**d, "margin_bps": d["margin_bps"] + 20, "conversion": d["conversion"] + 0.10})["operating"]
            for d in inputs)], costs)["npv"],
        "capital_charge_pv_excluded": pv([r["capital_expense"] for r in rows]),
    }
    return result, bridge, counterfactuals, metrics


def sweep(config, ids):
    options = config["search"]
    keys = list(options)
    for pid in ids:
        for values in product(*options.values()):
            changes = dict(zip(keys, values, strict=True))
            run = forecast(config, pid, changes=changes)
            yield {"product": pid, **changes, "npv": run["npv"], "irac29": run["years"][2]["irac"],
                   "payback_months": run["payback_months"], "capital": run["capital_peak"],
                   "operating27": run["years"][0]["operating"], "cumulative24": run["cumulative24"],
                   "funding": run["peak_funding"], "pass": run["financial_pass"], "hard_pass": run["hard_pass"]}
