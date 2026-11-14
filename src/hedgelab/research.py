from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil, isclose, isfinite
from pathlib import Path

import numpy as np

DAY = timedelta(days=1)
STRATEGIES = ("unhedged", "fixed_25", "fixed_50", "fixed_75", "fixed_100", "rolling_50", "risk_rule")


@dataclass(frozen=True)
class Rates:
    dates: tuple[date, ...]
    values: tuple[float, ...]

    def at_or_before(self, day: date, max_gap: int) -> int | None:
        index = bisect_right(self.dates, day) - 1
        if index >= 0 and (day - self.dates[index]).days <= max_gap:
            return index
        return None


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    anchor: float
    settlement: float

    @property
    def spot_return(self) -> float:
        return self.settlement / self.anchor - 1


def load_rates(path: Path) -> tuple[dict[str, Rates], dict]:
    locations = defaultdict(dict)
    counts = Counter()
    for row in csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines(), strict=True):
        currency = row["currency"]
        expected = {"USD": "840", "EUR": "978", "CNY": "156"}[currency]
        day = date.fromisoformat(row["date"])
        value, nominal, original = float(row["rub_per_unit"]), int(row["nominal"]), float(row["rate_original"])
        if (row["currency_code"] != expected or not isfinite(value) or value <= 0 or nominal <= 0
                or row["date_role"] != "official_effective_date" or row["source_id"] != "cbr_fx"
                or not isclose(value, original / nominal, rel_tol=1e-9) or day in locations[currency]):
            raise ValueError(f"Invalid CBR observation: {currency}, {day}")
        locations[currency][day] = value
        counts[currency, "missing_publication"] += not row["publication_date"]
        counts[currency, "nonunit_nominal"] += nominal != 1
    result, quality = {}, {}
    for currency, values in locations.items():
        dates = tuple(sorted(values))
        series = Rates(dates, tuple(values[d] for d in dates))
        jumps = [(left, right, spot2 / spot1 - 1) for left, right, spot1, spot2 in
                 zip(dates[:-1], dates[1:], series.values[:-1], series.values[1:], strict=True)
                 if abs(spot2 / spot1 - 1) >= 0.08]
        quality[currency] = {
            "rows": len(dates), "start": str(dates[0]), "end": str(dates[-1]),
            "max_gap_days": max((b - a).days for a, b in zip(dates[:-1], dates[1:], strict=True)),
            "missing_publication": counts[currency, "missing_publication"],
            "nonunit_nominal": counts[currency, "nonunit_nominal"],
            "jumps_8pct": [(str(a), str(b), j) for a, b, j in jumps],
        }
        result[currency] = series
    if set(result) != {"USD", "EUR", "CNY"} or len({v.dates for v in result.values()}) != 1:
        raise ValueError("The CBR currency calendars differ")
    return result, quality


def windows(rates: Rates, start: date, end: date, horizon: int, max_gap: int) -> list[Window]:
    pairs = []
    for day in rates.dates:
        target = day + horizon * DAY
        if target > end:
            break
        if day < start:
            continue
        anchor = rates.at_or_before(day - DAY, max_gap)
        settlement = rates.at_or_before(target, max_gap)
        if anchor is not None and settlement is not None:
            pairs.append(Window(day, target, rates.values[anchor], rates.values[settlement]))
    return pairs


def official_changes(rates: Rates, horizon: int, max_gap: int, first: date, last: date):
    """Retrospective effective-date changes matching the first archive audit."""
    for index, end in enumerate(rates.dates):
        if first <= end <= last:
            anchor = rates.at_or_before(end - horizon * DAY, max_gap)
            if anchor is not None:
                yield end, rates.dates[anchor], rates.values[index] / rates.values[anchor] - 1


def split(window: Window, test_start: date = date(2024, 1, 1)) -> str:
    first_cutoff = date(2022, 1, 1)
    if window.end < first_cutoff:
        return "development"
    if first_cutoff <= window.start and window.end < test_start:
        return "validation"
    if window.start >= test_start:
        return "test"
    return "cross_cutoff"


def regime(window: Window, market_change: date) -> str:
    boundaries = (date(2022, 1, 1), date(2023, 1, 1), market_change)
    start_bin = bisect_right(boundaries, window.start)
    end_bin = bisect_right(boundaries, window.end)
    return ("2019_2021", "2022", "pre_june_2024", "post_june_2024")[start_bin] if start_bin == end_bin else "boundary"


def expected_shortfall(losses: list[float], probability: float = 0.95) -> tuple[float, float]:
    if not losses or not 0 < probability < 1 or not all(isfinite(loss) for loss in losses):
        raise ValueError("A nonempty finite sample and a probability in (0, 1) are required")
    ordered = sorted(losses, reverse=True)
    var = ordered[len(ordered) - ceil(probability * len(ordered))]
    mass = (1 - probability) * len(ordered)
    if isclose(mass, round(mass), rel_tol=0, abs_tol=1e-12) and round(mass) >= 1:
        mass = float(round(mass))
    whole = int(mass)
    weighted = sum(ordered[:whole]) + (mass - whole) * ordered[whole]
    return var, weighted / mass


def risk_fraction(past_returns: list[float], signed_exposure: float, cost_fraction: float,
                  budget_limit: float, minimum_history: int, probability: float = 0.95) -> float | None:
    if signed_exposure == 0:
        return 0.0
    if len(past_returns) < minimum_history:
        return None
    direction = 1 if signed_exposure > 0 else -1
    risk, _ = expected_shortfall([-direction * value for value in past_returns], probability)
    for fraction in (0, 0.25, 0.50, 0.75, 1.0):
        if (1 - fraction) * risk + fraction * cost_fraction <= budget_limit:
            return fraction
    return 1.0 if risk > cost_fraction else 0.0


def hedge_cash(signed_exposure: float, fraction: float, start: float, end: float,
               days: int, annual_bps: float, fee_bps: float) -> tuple[float, float]:
    if not 0 <= fraction <= 1 or min(start, end) <= 0 or min(days, annual_bps, fee_bps) < 0:
        raise ValueError("Invalid hedge parameters")
    # Net importer buys the reference currency. Net exporter sells it.
    modeled_cost = abs(signed_exposure) * fraction * start * (annual_bps * days / 365 + fee_bps) / 10000
    return -signed_exposure * fraction * (end - start) - modeled_cost, modeled_cost


def evaluate(window: Window, rates: Rates, signed_exposure: float, strategy: str, fraction: float,
             annual_bps: float, fee_bps: float, rolling_days: int, max_gap: int) -> dict | None:
    end_points = [window.end]
    if strategy == "rolling_50":
        end_points = [
            window.start + day * DAY
            for day in range(rolling_days, (window.end - window.start).days, rolling_days)
        ] + end_points
    begin, anchor = window.start, window.anchor
    balance, costs, liquidity = 0.0, 0.0, 0.0
    for finish in end_points:
        rate_index = rates.at_or_before(finish if finish == window.end else finish - DAY, max_gap)
        if rate_index is None:
            return None
        settlement = rates.values[rate_index]
        payoff, cost = hedge_cash(signed_exposure, fraction, anchor, settlement,
                                 (finish - begin).days, annual_bps, fee_bps)
        balance += payoff
        costs += cost
        liquidity = max(liquidity, -balance)
        begin, anchor = finish, settlement
    cash_flow = signed_exposure * window.settlement + balance
    budget = signed_exposure * window.anchor
    return {
        "cash_flow_rub": cash_flow,
        "loss_vs_budget_rub": budget - cash_flow,
        "model_cost_rub": costs,
        "modeled_interim_cash_deficit_rub": liquidity if len(end_points) > 1 else 0.0,
        "fraction": fraction if signed_exposure else 0.0,
    }


def simulate(rates: Rates, signed_exposure: float, horizon: int, settings: dict):
    all_windows = windows(rates, settings["start"], settings["end"], horizon, settings["max_calendar_gap"])
    exit_dates = [w.end for w in all_windows]
    all_returns = [w.spot_return for w in all_windows]
    fee = settings["execution_fee_bps"]
    annual = settings["annual_lock_cost_bps"]
    for w in all_windows:
        cutoff = bisect_left(exit_dates, w.start)
        begin = bisect_left(exit_dates, w.start - settings["risk_lookback_days"] * DAY)
        lookback = all_returns[begin:cutoff]
        adaptive = risk_fraction(lookback, signed_exposure, (annual * horizon / 365 + fee) / 10000,
                                 settings["budget_limit"], settings["risk_min_observations"],
                                 settings.get("tail_probability", 0.95))
        amounts = (0, 0.25, 0.50, 0.75, 1.0, 0.50, adaptive)
        for strategy, fraction in zip(STRATEGIES, amounts, strict=True):
            if fraction is None:
                continue
            result = evaluate(w, rates, signed_exposure, strategy, fraction, annual, fee,
                              settings["rolling_days"], settings["max_calendar_gap"])
            if result is not None:
                yield {
                    "entry_date": w.start,
                    "payment_date": w.end,
                    "horizon_days": horizon,
                    "split": split(w, settings["test_starts"]),
                    "regime": regime(w, settings["post_venue_change"]),
                    "strategy": strategy,
                    "budget_rub": signed_exposure * w.anchor,
                    **result,
                }


def summarize(rows: list[dict], quantile: float = 0.95) -> dict:
    cash = [row["cash_flow_rub"] for row in rows]
    loss = [row["loss_vs_budget_rub"] for row in rows]
    var, cvar = expected_shortfall(loss, quantile)
    return {
        "windows": len(rows), "mean_cash_flow_rub": float(np.mean(cash)),
        "sd_cash_flow_rub": float(np.std(cash, ddof=1)) if len(cash) > 1 else 0.0,
        "var95_rub": var, "cvar95_rub": cvar, "worst_shortfall_rub": max(0.0, max(loss)),
        "worst_cash_flow_rub": min(cash), "mean_model_cost_rub": float(np.mean([r["model_cost_rub"] for r in rows])),
        "mean_fraction": float(np.mean([r["fraction"] for r in rows])),
        "worst_interim_cash_deficit_rub": max(r["modeled_interim_cash_deficit_rub"] for r in rows),
    }
