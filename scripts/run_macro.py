"""Build the FX Protection Gap evidence from official snapshots already available in the project."""
from __future__ import annotations

from math import isclose
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/snapshot/economics"
TABLE = ROOT / "output/macro/tables"
FIGURE = ROOT / "output/macro/figures"
CUTOFF = "2026-11-14"
ASIA = "Азия"
TOTAL = "Всего"
PALETTE = {"rub": "#155f89", "listed_430r": "#707e90", "other_fx": "#bd7827",
           "forward": "#155f89", "swap": "#bd7827", "ink": "#16314a"}
TRADE = "https://www.cbr.ru/vfs/statistics/credit_statistics/cur_str_new.xlsx"
BOP = "https://www.cbr.ru/Collection/Collection/File/62500/Bbs2610r.pdf"
DERIV = "https://www.cbr.ru/Collection/Collection/File/62422/derivatives_market_2026.pdf"


def save_table(frame, name):
    frame.to_csv(TABLE / f"{name}.csv", index=False, encoding="utf-8-sig", float_format="%.10f")


def currency_and_derivatives():
    trade = pd.read_csv(INPUT / "foreign_trade_currency_structure.csv")
    assert trade.publication_date.le(CUTOFF).all()
    currency = trade.loc[trade.indicator.eq("settlement_currency_share") & trade.geography.isin([TOTAL, ASIA])].copy()
    sum_keys = ["direction", "geography", "frequency", "period_end"]
    assert currency.groupby(sum_keys).value.sum().sub(100.).abs().max() < .01
    assert not currency.duplicated(sum_keys + ["currency_group"]).any()
    full_months = currency.loc[currency.frequency.eq("month") & currency.geography.eq(TOTAL)]
    assert len(full_months) == 552 and full_months.period_end.max() == "2026-08-31"
    assert set(currency.unit) == {"pct"} and set(currency.source) == {TRADE}
    save_table(currency, "macro_settlement_currency_series")

    fob = trade.loc[trade.indicator.eq("goods_trade_value_fob")].copy()
    assert len(fob) == 186 and fob.period_end.max() == "2026-09-30" and set(fob.unit) == {"usd_mn"}
    save_table(fob, "macro_goods_fob_series")
    derivatives = pd.read_csv(INPUT / "fx_derivatives_market.csv")
    monthly_counts = derivatives.loc[derivatives.indicator.eq("otc_deals_count")].copy()
    corp = monthly_counts.loc[monthly_counts.participant_scope.eq("corporate")]
    assert len(monthly_counts) == 144 and len(corp) == 72
    assert set(monthly_counts.unit) == {"contracts"} and monthly_counts.publication_date.le(CUTOFF).all()
    assert not corp.duplicated(["period_start", "instrument"]).any()

    usd_turn = derivatives.loc[
        derivatives.indicator.eq("monthly_turnover")
        & derivatives.participant_scope.eq("nonfinancial_clients")
        & derivatives.currency_pair.isin(["CNY/RUB", "USD/RUB", "EUR/RUB", "ALL_RUB"])
        & derivatives.instrument.isin(["fx_forward", "fx_swap"])
        & derivatives.period_start.ge("2020-01-01")
    ].copy()
    assert set(usd_turn.unit) == {"usd_mn"} and set(usd_turn.measure_type) == {"turnover"}
    cny = usd_turn.loc[usd_turn.currency_pair.eq("CNY/RUB")]
    assert len(cny) == 24 and set(cny.period_start.str[:4]) == {"2023"}
    positions = derivatives.loc[
        derivatives.indicator.eq("monthly_gross_notional_outstanding")
        & derivatives.instrument.eq("fx_forwards_and_swaps")
        & derivatives.currency_pair.isin(["ALL", "CNY", "USD"])
    ].copy()
    assert set(positions.unit) == {"usd_mn"} and set(positions.measure_type) == {"gross_notional_outstanding"}
    assert positions.period_start.max() == "2024-01-01"
    assert not usd_turn.duplicated(["period_start", "instrument", "currency_pair"]).any()
    assert not positions.duplicated(["period_start", "instrument", "currency_pair"]).any()
    save_table(pd.concat([monthly_counts, usd_turn, positions], ignore_index=True), "macro_fx_derivatives_series")

    case_recon = pd.read_csv(ROOT / "data/snapshot/source_reconciliation.csv")
    assert len(case_recon) == 696 and case_recon.result.eq("match").all()
    corp = corp.assign(period=corp.period_start.str[:4]+" H"+(corp.period_start.str[5:7].astype(int).gt(6)+1).astype(str))
    deals = corp.groupby(["period", "instrument"], as_index=False).agg(count=("value", "sum"), months=("value", "size"))
    assert deals.months.eq(6).all()
    table_count = deals.set_index(["period", "instrument"])["count"]
    assert table_count.loc["2025 H1", "fx_forward_and_ndf"] == 10044
    assert table_count.loc["2026 H1", "fx_forward_and_ndf"] == 18572
    assert table_count.loc["2025 H1", "fx_swap"] == 10670
    assert table_count.loc["2026 H1", "fx_swap"] == 15342
    save_table(deals.assign(source_url=DERIV, table="Table 1; corporate clients"),
               "macro_otc_deals_halfyears")
    return currency, fob, corp, table_count, usd_turn, positions


def client_risk():
    raw = pd.read_csv(ROOT / "output/hedgelab/hedge_historical_windows.csv")
    only = raw.loc[
        raw.scenario.isin(["importer", "mixed"]) & raw.currency.eq("CNY")
        & raw.horizon_days.eq(30) & raw.split.eq("test")
        & raw.strategy.isin(["unhedged", "fixed_50"])
    ].copy()
    rows = []
    reference = pd.read_csv(ROOT / "output/hedgelab/hedge_strategy_metrics.csv")
    for (profile, strategy), group in only.groupby(["scenario", "strategy"]):
        assert len(group) == 676
        losses = group.loss_vs_budget_rub.sort_values(ascending=False).tolist()
        tail = len(losses) * .05
        whole = int(tail)
        cvar = (sum(losses[:whole]) + losses[whole]*(tail-whole))/tail
        ref = reference.loc[reference.scenario.eq(profile) & reference.currency.eq("CNY")
                            & reference.horizon_days.eq(30) & reference.group.eq("test")
                            & reference.strategy.eq(strategy)].iloc[0]
        assert isclose(ref.cvar95_rub, cvar, abs_tol=.001)
        assert isclose(ref.mean_model_cost_rub, group.model_cost_rub.mean(), abs_tol=.001)
        rows.append({"profile": profile, "strategy": strategy,
                     "gross_obligation_cny": 1_000_000,
                     "aligned_receipts_cny": 0 if profile == "importer" else 600_000,
                     "residual_notional_cny": 1_000_000 if profile == "importer" else 400_000,
                     "days": 30, "windows": len(group), "first_entry": group.entry_date.min(),
                     "last_payment": group.payment_date.max(), "cvar95_rub": cvar,
                     "mean_model_cost_rub": group.model_cost_rub.mean(),
                     "mean_payment_or_net_outflow_rub": -group.cash_flow_rub.mean(),
                     "worst_loss_rub": losses[0], "status": "historical model example / no quote"})
    table = pd.DataFrame(rows).sort_values(["profile", "strategy"])
    save_table(table, "macro_client_budget_risk")
    return table


def scenarios(currency):
    bop = pd.read_csv(ROOT / "data/reference/bop_inputs.csv")
    bop["sum_goods_services_usd_mn"] = bop.imports_goods_usd_mn + bop.imports_services_usd_mn
    rub = currency.loc[currency.direction.eq("import") & currency.geography.eq(TOTAL)
                       & currency.currency_group.eq("rub"), ["period_end", "frequency", "value"]]
    bop = bop.merge(rub.rename(columns={"value":"rub_settlement_pct"}), on=["period_end","frequency"], validate="one_to_one")
    bop["rub_pool_proxy_usd_mn"] = bop.sum_goods_services_usd_mn * bop.rub_settlement_pct / 100
    bop["bop_source_url"] = BOP
    bop["structure_source_url"] = TRADE
    bop["interpretation"] = "Proxy: BOP economic flows and settlements differ; includes noncompany transactions e.g. travel"
    save_table(bop, "macro_proxy_denominator")
    anchor = bop.loc[bop.period_end.eq("2025-12-31")].iloc[0]
    assert anchor.sum_goods_services_usd_mn == 401253
    h126 = bop.loc[bop.period_start.str.startswith("2026")]
    assert h126.sum_goods_services_usd_mn.sum() == 205299
    rows = []
    # These are planning probes. They have no probabilistic or survey interpretation.
    for name, clause, residual, unprotected in [
        ("low", .05, .30, .25), ("base_sensitivity", .15, .50, .45), ("high", .30, .70, .65)
    ]:
        for capture in [.005, .01, .03]:
            flow = float(anchor.rub_pool_proxy_usd_mn)
            clause_flow = flow * clause
            residual_flow = clause_flow * residual
            gap = residual_flow * unprotected
            rows.append({"period": "2025", "scenario": name,
                         "imports_goods_services_bop_usd_bn": anchor.sum_goods_services_usd_mn/1000,
                         "rub_settlement_share": anchor.rub_settlement_pct/100,
                         "rub_pool_proxy_usd_bn": flow/1000,
                         "indexed_share_value": clause, "remaining_after_natural_hedge_value": residual,
                         "uncovered_after_existing_financial_hedges_value": unprotected,
                         "joint_gap_share_of_rub_pool": clause * residual * unprotected,
                         "indexed_usd_bn": clause_flow/1000, "residual_usd_bn": residual_flow/1000,
                         "gap_usd_bn": gap/1000,
                         "hypothetical_uptake_of_uncovered": capture,
                         "potential_served_usd_bn": gap*capture/1000,
                         "uptake_to_serve_0_1_bn": (100/gap if gap else None),
                         "formula": "bop_import * rub_share * indexed * residual * unprotected * uptake",
                         "units": "USD billions proxy / ratios",
                         "status": "deterministic sensitivity; not inferred national or bank serviceable market"})
    grid = pd.DataFrame(rows)
    assert (grid.potential_served_usd_bn <= grid.gap_usd_bn).all()
    assert (grid.gap_usd_bn <= grid.rub_pool_proxy_usd_bn).all()
    save_table(grid, "macro_scenarios")
    return bop, grid


def render(currency, corporate, usd_turn, positions, grid):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.spines.top":False,
                         "axes.spines.right":False,"axes.labelcolor":PALETTE["ink"],
                         "axes.titlecolor":PALETTE["ink"],"text.color":PALETTE["ink"],
                         "axes.edgecolor":"#a9b6c2"})
    colors = [PALETTE["rub"], PALETTE["listed_430r"], PALETTE["other_fx"]]
    labels = ["Российский рубль", "Валюты перечня № 430-р", "Прочие валюты"]
    plot = currency.loc[currency.geography.eq(TOTAL) & currency.frequency.eq("month")]
    fig, axes = plt.subplots(2,1,sharex=True,figsize=(12,7.6))
    for ax, side, heading in zip(axes, ("export","import"), ("Экспортные поступления","Импортные платежи"), strict=True):
        pivot = plot.loc[plot.direction.eq(side)].pivot(index="period_end", columns="currency_group", values="value")
        ax.stackplot(pd.to_datetime(pivot.index), *(pivot[x] for x in ("rub","listed_430r","other_fx")),
                     colors=colors, labels=labels, alpha=.94)
        ax.set_title(heading, loc="left", fontweight="bold")
        ax.set_ylim(0,100)
        ax.set_yticks([0,25,50,75,100])
        ax.yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
        ax.grid(axis="y", alpha=.25)
    axes[1].xaxis.set_major_locator(mdates.YearLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].set_xlim(pd.Timestamp("2019-01-01"), pd.Timestamp("2026-09-15"))
    fig.suptitle("Валюта расчётов за российские товары и услуги", x=.085, ha="left",fontsize=20,fontweight="bold")
    fig.legend(*axes[0].get_legend_handles_labels(),loc="lower left",bbox_to_anchor=(.077,.048),ncol=3,frameon=False)
    fig.text(.085,.026,"Январь 2019 – август 2026 г.  |  Все географические зоны  |  Источник: Банк России, публикация 15.10.2026.",fontsize=9)
    fig.subplots_adjust(left=.085,right=.985,top=.875,bottom=.16,hspace=.28)
    fig.savefig(FIGURE/"settlement_currency_structure.png",dpi=170,facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(1,3,figsize=(15,5.8),gridspec_kw={"width_ratios":[1.15,1,1]})
    series = [
        (corporate, "fx_forward_and_ndf", "Forward / NDF", PALETTE["forward"]),
        (corporate, "fx_swap", "FX swap", PALETTE["swap"])
    ]
    for data, instr, name, color in series:
        sel = data.loc[data.instrument.eq(instr)]
        axes[0].plot(pd.to_datetime(sel.period_start), sel.value, label=name,color=color,lw=2.3,marker=".",ms=5)
        sel = usd_turn.loc[usd_turn.currency_pair.eq("CNY/RUB") & usd_turn.instrument.eq("fx_forward" if instr=="fx_forward_and_ndf" else instr)]
        axes[1].plot(pd.to_datetime(sel.period_start), sel.value/1000, label=name,color=color,lw=2.3,marker=".",ms=5)
    for cur, color, label in [("CNY",PALETTE["forward"],"С участием CNY"),("USD",PALETTE["swap"],"С участием USD")]:
        pos = positions.loc[positions.currency_pair.eq(cur)]
        axes[2].plot(pd.to_datetime(pos.period_start),pos.value/1000,color=color,label=label,lw=2.3)
    for ax, ttl, ylabel in zip(axes, ("Корпоративные OTC-сделки","Оборот CNY/RUB","Открытые позиции ПФИ"),
                              ("Число сделок в месяц","Млрд USD за месяц","Млрд USD на начало месяца"),strict=True):
        ax.set_title(ttl,loc="left",fontsize=12.5,fontweight="bold")
        ax.set_ylabel(ylabel,fontsize=10)
        ax.set_ylim(bottom=0)
        ax.legend(loc="upper left",frameon=False,fontsize=9)
        ax.grid(axis="y",alpha=.22)
    axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%m.%y"))
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%m.%y"))
    axes[2].xaxis.set_major_locator(mdates.YearLocator())
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Валютные ПФИ: три разных измерения рынка", x=.065,ha="left",fontsize=21,fontweight="bold")
    fig.text(.065,.048,"Слева: 01.2025–06.2026, все пары, табл. 1 обзора ПФИ. Центр: нефинансовые клиенты, 2023, NDF входит в форварды. Справа: 01.2019–01.2024, валютные ноги пересекаются.",fontsize=9)
    fig.text(.065,.021,"Источник: Банк России, обзор ПФИ от 30.09.2026 и статистика финансовых рынков. Для каждой панели единицы и отчётный охват различаются.",fontsize=9)
    fig.subplots_adjust(left=.065,right=.98,top=.82,bottom=.16,wspace=.34)
    fig.savefig(FIGURE/"derivatives_market_measures.png",dpi=170,facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(1,2,figsize=(12,5.6),gridspec_kw={"width_ratios":[1,1.13]})
    group = grid.loc[grid.hypothetical_uptake_of_uncovered.eq(.01)]
    names = ["Низкий","Средний","Высокий"]
    palette = ["#aac7d8","#337da5","#14496c"]
    for ax, col, label in zip(axes, ("gap_usd_bn","potential_served_usd_bn"),
                              ("FX Protection Gap, млрд USD экв.","Обслужено при 1%, млн USD экв."),strict=True):
        values = group[col] * (1000 if col=="potential_served_usd_bn" else 1)
        shown = [f"{v:.2f}".replace(".",",") for v in values]
        bars = ax.barh(names,values,color=palette,height=.5)
        ax.invert_yaxis()
        ax.set_xlim(0,values.max()*1.19)
        ax.set_xlabel(label)
        ax.bar_label(bars,labels=shown,padding=5)
        ax.grid(axis="x",alpha=.24)
        ax.tick_params(axis="y",length=0)
    fig.suptitle("FX Protection Gap при разных допущениях", x=.13,ha="left",fontsize=19,fontweight="bold")
    fig.text(.13,.064,"База 2025 г.  |  Доли заданы для чувствительности. 1% считается от остатка без защиты, вероятность не оценивается.",fontsize=9)
    fig.text(.13,.038,"Основа: платёжный баланс и валюта расчётов Банка России. Покрытие клиентов БСПБ проверяется отдельно.",fontsize=9)
    fig.subplots_adjust(left=.13,right=.97,top=.82,bottom=.19,wspace=.31)
    fig.savefig(FIGURE/"protection_gap_sensitivity.png",dpi=170,facecolor="white")
    plt.close(fig)


def main():
    TABLE.mkdir(parents=True,exist_ok=True)
    FIGURE.mkdir(parents=True,exist_ok=True)
    currency, fob, corporate, half_total, turnover, positions = currency_and_derivatives()
    clients = client_risk()
    bop, grid = scenarios(currency)
    render(currency, corporate, turnover, positions, grid)
    gb = grid.loc[grid.hypothetical_uptake_of_uncovered.eq(.01)]
    print(f"CBR {len(currency)} currency rows ({currency.period_end.max()}), {len(fob)} goods FOB rows, "
          f"{len(turnover)} turnover rows, {len(positions)} outstanding rows and 144 deal counts.")
    print("FX Forward/NDF H1:", half_total.loc["2025 H1","fx_forward_and_ndf"],
          "->",half_total.loc["2026 H1","fx_forward_and_ndf"])
    print(bop[["period_end","sum_goods_services_usd_mn","rub_settlement_pct","rub_pool_proxy_usd_mn"]].to_string(index=False))
    print(gb[["scenario","gap_usd_bn","potential_served_usd_bn","uptake_to_serve_0_1_bn"]].to_string(index=False))
    print(clients[["profile","strategy","first_entry","last_payment","cvar95_rub","mean_model_cost_rub"]].to_string(index=False))


if __name__ == "__main__":
    main()
