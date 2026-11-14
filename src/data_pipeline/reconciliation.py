from __future__ import annotations

import math
from datetime import datetime

import openpyxl
from openpyxl.utils import get_column_letter

from data_pipeline.core import Run, atomic_write
from data_pipeline.datasets import ECON, csv_bytes, read_dataset

SHARES = (
    ("FX доля в экспорте", "export"),
    ("FX доля в импорте", "import"),
)
GROUPS = ("rub", "listed_430r", "other_fx")
UNITS_SHEETS = (
    "Чистые продажи топ экспортеров", "Чистые продажи нефин комп",
    "Чистые покупки нефин комп", "Покупки ЮЛ", "Валютизация требований к ЮЛ",
)
COUNTS_INSTRUMENTS = {
    "FX Forward, NDF": "fx_forward_and_ndf", "FX Swap": "fx_swap",
    "FX Option": "fx_option", "Cross-Currency Swap (CCS)": "cross_currency_swap",
}


def workbook_audit(run: Run) -> None:
    path = run.root / "reports/source_reconciliation.md"
    text = ["# Сверка материалов кейса", ""]
    inputs = run.raw("case_workbook", "workbook")
    if not inputs:
        text.append("Исходный Excel отсутствует. Статус переноса указан в реестре источников.")
        atomic_write(path, ("\n".join(text) + "\n").encode())
        return
    if not all(run.path(ECON + name).exists() for name in (
        "foreign_trade_currency_structure.csv", "fx_derivatives_market.csv",
    )):
        text.append("Для сверки нужно сначала сформировать экономические витрины.")
        atomic_write(path, ("\n".join(text) + "\n").encode())
        return
    raw = inputs[-1]
    trade = read_dataset(run.path(ECON + "foreign_trade_currency_structure.csv"))
    truth = {
        (row.direction, row.period_end, row.currency_group): float(row.value)
        for row in trade.itertuples()
        if row.geography == "Всего" and row.frequency == "month"
        and row.indicator == "settlement_currency_share" and row.value is not None
    }
    derivatives = read_dataset(run.path(ECON + "fx_derivatives_market.csv"))
    counts = {
        (row.instrument, row.participant_scope, row.period_start): int(float(row.value))
        for row in derivatives.itertuples()
        if row.measure_type == "deal_count"
    }
    results = []
    workbook = openpyxl.load_workbook(raw.path, read_only=True, data_only=True)
    try:
        text += [f"Книга содержит {len(workbook.sheetnames)} листов. SHA-256 {raw.sha256}.", "",
                 "| Лист | Сверено | Совпало | Расхождения | Без сопоставимого значения |",
                 "|---|---:|---:|---:|---:|"]
        for name, direction in SHARES:
            sheet = workbook[name]
            checks = []
            for number, row in enumerate(sheet.iter_rows(min_row=4, min_col=5, max_col=8, values_only=True), 4):
                if not isinstance(row[0], datetime):
                    continue
                day = row[0].date().isoformat()
                for column, (group, value) in zip("FGH", zip(GROUPS, row[1:], strict=True), strict=True):
                    if isinstance(value, (float, int)):
                        checks.append(compare(name, f"{column}{number}", day, group, value,
                                              truth.get((direction, day, group))))
            text.append(summary(name, checks))
            results.extend(checks)
        sheet = workbook["OTC сделки табл"]
        date_row = next(sheet.iter_rows(min_row=3, max_row=3, values_only=True))
        checks = []
        for i, row in enumerate(sheet.iter_rows(min_row=4, values_only=True), 4):
            instrument = COUNTS_INSTRUMENTS.get(row[0])
            scope = {"Корпоративный": "corporate", "Розничный": "retail"}.get(row[1])
            if not instrument or not scope:
                continue
            for col, (dt, value) in enumerate(zip(date_row[2:], row[2:]), 3):
                if isinstance(dt, datetime) and isinstance(value, (float, int)):
                    day = dt.date().isoformat()
                    checks.append(compare(sheet.title, f"{get_column_letter(col)}{i}", day, instrument,
                                          value, counts.get((instrument, scope, day))))
        text.append(summary(sheet.title, checks))
        results.extend(checks)
        approximations = [sheet.title for sheet in workbook if any(
            "использованием ии" in str(value).lower()
            for row in sheet.iter_rows(max_row=2, max_col=5, values_only=True) for value in row
        )]
        text += ["", "## Применимость листов", "",
                 "- Официальные группы валют — рубль, валюты перечня № 430-р и прочие. "
                 "Подпись «Дружественные» в кейсе относится к колонке «прочие валюты» первоисточника.",
                 "- Таблица числа OTC-сделок сверена по типу клиента, инструменту и месяцу. "
                 "Квартальная агрегация из листа «Кол-во ПФИ сделок» не входит в эталон.",
                 "- Листы с маркировкой аппроксимации ИИ исключены из расчётных наборов — "
                 + ", ".join(approximations) + ".",
                 "- Дополнительной сверки требуют " + ", ".join(UNITS_SHEETS) + ". "
                 "В частности, колонка «Чистые покупки нефин комп» подписана в млрд долларов США, "
                 "а масштаб опубликованных в книге чисел требует проверки первоисточника.",
                 "- Доля валюты платежа описывает расчёты. Для оценки валютной экспозиции договоров нужен отдельный корпус.",
                 "", "Результаты на уровне ячеек — @data/metadata/source_reconciliation.csv@."]
    finally:
        workbook.close()
    fields = ("sheet", "cell", "date", "indicator", "workbook_value", "official_value", "result")
    atomic_write(run.metadata / "source_reconciliation.csv", csv_bytes(results, fields))
    atomic_write(path, ("\n".join(text).replace("@", chr(96)) + "\n").encode())


def compare(sheet: str, cell: str, date: str, metric: str, value: float, reference: float | None) -> dict:
    result = "unavailable" if reference is None else "match" if math.isclose(
        value, reference, rel_tol=0, abs_tol=1e-8) else "different"
    return dict(sheet=sheet, cell=cell, date=date, indicator=metric, workbook_value=value,
                official_value=reference, result=result)


def summary(name: str, checks: list[dict]) -> str:
    available = sum(x["result"] != "unavailable" for x in checks)
    matches = sum(x["result"] == "match" for x in checks)
    return f"| {name} | {available} | {matches} | {available - matches} | {len(checks) - available} |"
