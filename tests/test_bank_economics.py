from pathlib import Path

import pytest
import yaml

from bank_economics.model import annual, break_even_margin, valuation


@pytest.fixture
def drivers():
    path = Path(__file__).resolve().parents[1] / "configs/economics_assumptions.yaml"
    return {d["id"]: d["values"][1][0] for d in yaml.safe_load(path.read_text(encoding="utf-8"))["drivers"]}


def test_incremental_revenue_and_cost_waterfall(drivers):
    baseline = annual(drivers)
    full_cannibalization = annual({**drivers, "cannibalization": 1})
    assert full_cannibalization["hedge_income"] == 0
    assert full_cannibalization["capital_expense"] == 0
    assert full_cannibalization["premium_income"] == baseline["premium_income"]
    assert baseline["operating"] - baseline["capital_expense"] == pytest.approx(baseline["irac"])
    assert baseline["capital"] < baseline["ead"] < baseline["open_notional"] < baseline["turnover"]
    assert annual({**drivers, "targeted": 0})["irac"] == -drivers["fixed_cost"]


def test_discount_payback_irr_and_break_even_margin():
    v = valuation([-100, 30, 60, 60], [0.10, 0.10, 0.10])
    assert v["npv"] == pytest.approx(-100 + 30 / 1.1 + 60 / 1.21 + 60 / 1.331)
    assert v["payback_months"] == pytest.approx(26)
    assert valuation([-100, 30, 60, 60], [v["irr"]] * 3)["npv"] == pytest.approx(0, abs=1e-9)
    assert valuation([-100, -2, 3, -5], [0.2] * 3)["irr"] is None
    margin = break_even_margin([-5, -1, -2, -3], [1000, 2000, 3000], [0.2] * 3)
    assert valuation([-5, -1 + margin * 0.1, -2 + margin * 0.2, -3 + margin * 0.3],
                     [0.2] * 3)["npv"] == pytest.approx(0, abs=1e-9)
