from pathlib import Path

import pytest
import yaml

from bank_economics.investment import baseline, forecast


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def config():
    return yaml.safe_load((ROOT / "configs/investment.yaml").read_text(encoding="utf-8"))


def test_baseline_bridge_reproduces_previous_study():
    assumptions = yaml.safe_load((ROOT / "configs/economics_assumptions.yaml").read_text(encoding="utf-8"))
    prior, bridge, _, reverse = baseline(assumptions)
    assert prior["Base"]["npv"] == pytest.approx(-46.69330412977925)
    assert sum(bridge.values()) == pytest.approx(prior["Base"]["npv"])
    assert reverse["combined_v2_npv"] == pytest.approx(-33.13969958557884)


def test_incrementality_capacity_and_cumulative_flow(config):
    run = forecast(config, "staged")
    inputs = config["products"]["staged"]
    for y, capacity in zip(run["years"], inputs["capacity"], strict=True):
        assert y["active"] <= capacity
        assert y["capital"] <= inputs["capital_limit"] + 1e-8
        assert y["gross_fx"] == pytest.approx(y["displaced_fx"] + y["unserved_fx"] + y["fx"])
        assert y["cash"] == pytest.approx(y["operating"] + y["dep"] - y["tax"] - y["reinvest"] - y["delta_nwc"])
        assert y["irac"] == pytest.approx(y["operating"] - y["allocation"] - y["capital_charge"])
    assert sum(y["reach"] for y in run["years"]) <= config["segments"]["recurring"]["reach_limit"]
    assert run["cumulative24"] == pytest.approx(sum(run["cash"][:3]))
    assert run["cash"][0] == -(run["capex0"] + run["prelaunch_expense"])


def test_no_double_capital_charge_and_profit_tax(config):
    base = forecast(config, "staged")
    config["shared"]["capital_hurdle"] *= 2
    high_cost = forecast(config, "staged")
    assert high_cost["npv"] == base["npv"]
    assert high_cost["years"][2]["irac"] < base["years"][2]["irac"]
    for y in high_cost["years"]:
        assert y["tax"] == pytest.approx(0.25 * max(0, y["operating"]))


@pytest.mark.parametrize("variant", ["staged", "trade", "full"])
def test_zero_clients_and_delayed_first_revenue(config, variant):
    run = forecast(config, variant, changes={"reach": 0})
    assert all(y["revenue"] == y["capital"] == 0 for y in run["years"])
    assert all(y["ltv_cac"] is None for y in run["years"])
    delayed = forecast(config, variant, changes={"delay": 12})
    assert delayed["years"][0]["revenue"] == 0
    assert delayed["first_month"] > 12


def test_financing_is_explicit_upside(config):
    base = forecast(config, "trade")
    finance = forecast(config, "trade", finance=True)
    assert all(y["extra"] == y["credit_ead"] == 0 for y in base["years"])
    assert finance["years"][2]["el"] > base["years"][2]["el"]
    assert finance["years"][2]["capital"] > base["years"][2]["capital"]
