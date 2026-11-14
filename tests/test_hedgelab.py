from datetime import date, timedelta

import pytest

from hedgelab.research import Rates, Window, evaluate, expected_shortfall, hedge_cash, load_rates, risk_fraction, simulate


def test_rates_normalized_and_using_previous_available_date(tmp_path):
    path = tmp_path / "spot.csv"
    path.write_text(
        "date,currency,currency_code,nominal,rate_original,rub_per_unit,date_role,source_id,publication_date\n"
        "2020-01-01,CNY,156,10,95,9.5,official_effective_date,cbr_fx,\n"
        "2020-01-03,CNY,156,1,10,10,official_effective_date,cbr_fx,\n"
        "2020-01-01,USD,840,1,62,62,official_effective_date,cbr_fx,\n"
        "2020-01-03,USD,840,1,63,63,official_effective_date,cbr_fx,\n"
        "2020-01-01,EUR,978,1,71,71,official_effective_date,cbr_fx,\n"
        "2020-01-03,EUR,978,1,72,72,official_effective_date,cbr_fx,\n", encoding="utf-8",
    )
    cny = load_rates(path)[0]["CNY"]
    assert cny.values == (9.5, 10)
    assert cny.at_or_before(date(2020, 1, 2), 1) == 0
    assert cny.at_or_before(date(2020, 1, 2), 0) is None
    path.write_text(path.read_text().replace(",95,9.5,", ",95,95,"), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid CBR"):
        load_rates(path)


@pytest.mark.parametrize("net", [-100, 100, 0])
def test_full_coverage_neutralizes_both_cash_flow_directions(net):
    first, last = date(2025, 1, 1), date(2025, 1, 31)
    for spot in (7, 10, 14):
        r = Rates((first, last), (10, spot))
        w = Window(first, last, 10, spot)
        result = evaluate(w, r, net, "fixed_100", 1, 0, 0, 30, 7)
        assert result["cash_flow_rub"] == net * 10
        assert result["model_cost_rub"] == 0


def test_roll_cost_and_starting_direction():
    start = date(2025, 1, 1)
    mid, end = start + timedelta(days=29), start + timedelta(days=60)
    rates = Rates((start, mid, end), (10, 12, 9))
    w = Window(start, end, 10, 9)
    rolling = evaluate(w, rates, -100, "rolling_50", 0.5, 0, 10, 30, 7)
    fixed = evaluate(w, rates, -100, "fixed_50", 0.5, 0, 10, 30, 7)
    assert rolling["model_cost_rub"] == pytest.approx(1.1)
    assert fixed["model_cost_rub"] == pytest.approx(0.5)
    assert rolling["cash_flow_rub"] == pytest.approx(fixed["cash_flow_rub"] - 0.6)
    assert hedge_cash(-100, 1, 10, 12, 30, 0, 0)[0] == 200
    assert hedge_cash(100, 1, 10, 12, 30, 0, 0)[0] == -200
    assert risk_fraction([0.2] * 70, 0, 0.01, 0.03, 60) == 0


def test_tail_uses_fraction_of_boundary_observation():
    data = list(range(1, 12))
    quantile, tail = expected_shortfall(data, 0.80)
    assert quantile == 9
    assert tail == pytest.approx((11 + 10 + 0.2 * 9) / 2.2)


def test_future_spots_cannot_change_previously_selected_hedge_fraction():
    start, chosen = date(2023, 1, 1), date(2024, 5, 1)
    dates = tuple(start + timedelta(days=i) for i in range(700))
    values = tuple(10.0 + (i % 31) / 12 for i in range(700))
    altered = tuple(value if day < chosen else 2 * value for day, value in zip(dates, values, strict=True))
    config = {
        "start": start, "end": dates[-1], "test_starts": date(2024, 1, 1),
        "post_venue_change": date(2024, 6, 13), "max_calendar_gap": 7, "risk_lookback_days": 365,
        "risk_min_observations": 60, "annual_lock_cost_bps": 200, "execution_fee_bps": 10,
        "budget_limit": 0.03, "rolling_days": 30,
    }
    def at_choice(rates):
        return next(x for x in simulate(rates, -1000, 30, config)
                    if x["entry_date"] == chosen and x["strategy"] == "risk_rule")
    before, after = at_choice(Rates(dates, values)), at_choice(Rates(dates, altered))
    assert before["fraction"] == after["fraction"]
    assert before["cash_flow_rub"] != after["cash_flow_rub"]
