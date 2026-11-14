from __future__ import annotations

from math import isfinite


def annual(d: dict[str, float]) -> dict[str, float | None]:
    potential = d["targeted"] * d["fx_share"]
    eligible = potential * d["eligible"]
    active = eligible * d["activation"]
    confirmed = active * d["confirmed"]
    first = confirmed * d["conversion"]
    repeats = first * d["repeat_share"]
    deals = first + repeats * d["repeat_deals"]
    subscribers = active * d["premium"]
    incremental_deals = deals * (1 - d["cannibalization"])
    turnover = incremental_deals * d["ticket"]
    hedge_income = turnover * d["margin_bps"] / 10000
    premium_income = subscribers * d["monthly_price"] * d["billed_months"] / 1000
    service_cost = active * d["servicing"] / 1000
    trade_ops = incremental_deals * d["trade_ops"] / 1000
    open_notional = turnover * d["life_days"] / 365
    ead = open_notional * d["pfe_ratio"]
    expected_loss = ead * d["pd"] * d["lgd"]
    capital = ead * d["capital_ratio"]
    capital_expense = capital * d["capital_charge"]
    revenue = hedge_income + premium_income
    contribution = revenue - service_cost - trade_ops - expected_loss
    operating = contribution - d["fixed_cost"]
    irac = operating - capital_expense
    contributions_per_invited = contribution / d["targeted"] if d["targeted"] else None
    breakeven = d["fixed_cost"] / contributions_per_invited if contributions_per_invited and contributions_per_invited > 0 else None
    return {
        "targeted": d["targeted"], "potential": potential, "eligible": eligible, "active": active,
        "confirmed": confirmed, "first": first, "repeat_clients": repeats, "deals": deals,
        "subscribers": subscribers, "incremental_deals": incremental_deals, "turnover": turnover,
        "hedge_income": hedge_income, "premium_income": premium_income, "revenue": revenue,
        "service_cost": service_cost, "trade_ops": trade_ops, "open_notional": open_notional,
        "ead": ead, "expected_loss": expected_loss, "capital": capital, "capital_expense": capital_expense,
        "fixed_cost": d["fixed_cost"], "contribution": contribution,
        "contribution_margin": contribution / revenue if revenue else None,
        "operating": operating, "irac": irac, "breakeven_clients": breakeven,
        "contribution_per_active_th": contribution * 1000 / active if active else None,
        "irac_per_active_th": irac * 1000 / active if active else None,
    }


def valuation(cash: list[float], discounts: list[float]) -> dict[str, float | None]:
    if len(cash) != len(discounts) + 1 or not all(isfinite(x) for x in cash) or any(d <= -1 for d in discounts):
        raise ValueError("Cash flow and discount curve are inconsistent")
    discounted = cash[0]
    divisor = 1.0
    cumulative = cash[0]
    payback = 0.0 if cash[0] >= 0 else None
    for index, (flow, rate) in enumerate(zip(cash[1:], discounts, strict=True), 1):
        divisor *= 1 + rate
        discounted += flow / divisor
        if payback is None and cumulative < 0 <= cumulative + flow:
            payback = (index - 1 - cumulative / flow) * 12
        cumulative += flow
    irr = None
    if cash[0] < 0 and any(flow > 0 for flow in cash[1:]):
        signs = [x > 0 for x in cash if x != 0]
        if sum(a != b for a, b in zip(signs, signs[1:])) == 1:
            low, high = -0.9999, 1.0
            def npv(rate):
                return sum(v / (1 + rate) ** index for index, v in enumerate(cash))
            while npv(high) > 0 and high < 100:
                high *= 2
            if npv(low) > 0 >= npv(high):
                for _ in range(70):
                    mid = (low + high) / 2
                    if npv(mid) > 0:
                        low = mid
                    else:
                        high = mid
                irr = (high + low) / 2
    return {"npv": discounted, "irr": irr, "payback_months": payback, "cash_total": cumulative}


def break_even_margin(cash: list[float], turnover: list[float], discounts: list[float]) -> float | None:
    per_bps = valuation([0, *(value / 10000 for value in turnover)], discounts)["npv"]
    return -valuation(cash, discounts)["npv"] / per_bps if per_bps and per_bps > 0 else None
