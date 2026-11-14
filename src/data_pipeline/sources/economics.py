from __future__ import annotations

import calendar
import csv
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import openpyxl
import xlrd
from lxml import html
from openpyxl.utils import get_column_letter

from data_pipeline.core import Raw, Run, SourceError
from data_pipeline.sources.cbr import decimal

MONTHS = ("янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")
CURRENCY_GROUPS = {
    "в российских рублях": "rub",
    "в валютах государств и территорий по перечню": "listed_430r",
    "в прочих валютах": "other_fx",
}
BANK_LINES = {
    "чистый процентный доход": ("net_interest_income", "rub_bn"),
    "чистый комиссионный доход": ("net_fee_income", "rub_bn"),
    "чистый доход от операций на финансовых рынках": ("net_financial_markets_income", "rub_bn"),
    "выручка": ("revenue", "rub_bn"),
    "операционные расходы": ("operating_expenses", "rub_bn"),
    "расходы на резервы по кредитам клиентам": ("loan_provision_expense", "rub_bn"),
    "чистая прибыль": ("net_profit", "rub_bn"),
    "чистая процентная маржа": ("net_interest_margin", "pct"),
    "отношение издержек к доходам": ("cost_income_ratio", "pct"),
    "стоимость риска": ("cost_of_risk", "pct"),
    "рентабельность капитала": ("roe", "pct"),
    "рентабельность активов": ("roa", "pct"),
    "прибыль на 1 обыкновенную акцию": ("eps", "rub"),
    "акционерный капитал на 1 обыкновенную акцию": ("equity_per_share", "rub"),
    "активы": ("assets", "rub_bn"),
    "собственные средства": ("equity", "rub_bn"),
    "кредитный портфель": ("gross_loan_portfolio", "rub_bn"),
    "корпоративный кредитный портфель": ("corporate_loans", "rub_bn"),
    "кредиты корпоративным клиентам": ("corporate_loans", "rub_bn"),
    "средства корпоративных клиентов": ("corporate_funding", "rub_bn"),
    "основной капитал": ("tier1_capital", "rub_bn"),
    "акционерный капитал": ("equity", "rub_bn"),
    "собственный капитал": ("regulatory_total_capital", "rub_bn"),
    "достаточность основного капитала": ("capital_adequacy_n1_2", "pct"),
    "достаточность капитала": ("capital_adequacy_n1_0", "pct"),
    "капитал": ("equity", "rub_bn"),
    "общий капитал": ("regulatory_total_capital", "rub_bn"),
    "число корпоративных клиентов": ("corporate_customer_count", "customers"),
    "количество корпоративных клиентов": ("corporate_customer_count", "customers"),
}


def cleaned(value) -> str:
    return " ".join(str(value or "").split())


def period_bounds(year: int, start_month: int, span: int) -> tuple[date, date]:
    end_month = start_month + span - 1
    return date(year, start_month, 1), date(year, end_month, calendar.monthrange(year, end_month)[1])


def trade_period(value, frequency: str) -> tuple[date, date]:
    label = cleaned(value).lower()
    if frequency == "month":
        month, year = label.split(".", 1)
        return period_bounds(2000 + int(year), MONTHS.index(month[:3]) + 1, 1)
    if frequency == "quarter":
        quarter, _, year = label.split()
        return period_bounds(int(year), (int(quarter) - 1) * 3 + 1, 3)
    return period_bounds(int(label), 1, 12)


def workbook_date(sheet) -> date | None:
    for row in sheet.values:
        for value in row[:1]:
            if isinstance(value, str) and "последнего обновления" in value.lower():
                found = re.search(r"\d{2}\.\d{2}\.\d{4}", value)
                if found:
                    day, month, year = map(int, found[0].split("."))
                    return date(year, month, day)
    return None


def trade_structure(raw: Raw):
    workbook = openpyxl.load_workbook(raw.path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            flow, period_type = sheet.title.split()
            direction = {"ЭКСПОРТ": "export", "ИМПОРТ": "import"}[flow]
            frequency = {"месяцы": "month", "кварталы": "quarter", "годы": "year"}[period_type]
            matrix = list(sheet.values)
            dates = {i: trade_period(x, frequency) for i, x in enumerate(matrix[1]) if i >= 2 and x}
            publication = workbook_date(sheet)
            notes = " ".join(cleaned(row[0]) for row in matrix if isinstance(row[0], str)
                             and (row[0].startswith("*") or "M.49" in row[0]))
            geography = None
            for index, row in enumerate(matrix[2:], 3):
                if row[0] and row[1]:
                    geography = cleaned(row[0])
                currency_label = cleaned(row[1])
                code = CURRENCY_GROUPS.get(currency_label.rstrip("*").strip())
                if code is None or not geography:
                    continue
                for col, (start, end) in dates.items():
                    value = row[col]
                    yield {
                        "period_start": start, "period_end": end, "frequency": frequency,
                        "publication_date": publication, "direction": direction, "geography": geography,
                        "indicator": "settlement_currency_share", "currency_group": code,
                        "currency_group_label": currency_label,
                        "value": float(value) if isinstance(value, (int, float)) else None,
                        "unit": "pct", "sheet": sheet.title,
                        "cell": f"{get_column_letter(col + 1)}{index}",
                        "methodology_note": notes, **raw.reference(),
                    }
    finally:
        workbook.close()


def trade_volume(raw: Raw):
    workbook = xlrd.open_workbook(raw.path, on_demand=True)
    try:
        sheet = workbook.sheet_by_name("Ежемесячные")
        head = cleaned(sheet.cell_value(4, 2)) + " " + cleaned(sheet.cell_value(4, 8))
        if "Экспорт" not in head or "Импорт" not in head:
            raise SourceError("CBR trade volume columns have changed")
        publication = None
        for value in sheet.col_values(0, max(0, sheet.nrows - 20)):
            found = re.search(r"обновления:\s*(\d{1,2})\s+([а-яё]+)\s+(\d{4})", str(value), re.I)
            if found:
                day, month, year = found.groups()
                publication = date(int(year), MONTHS.index(month[:3]) + 1, int(day))
        for index in range(7, sheet.nrows):
            year, month = sheet.row_values(index, 0, 2)
            if not isinstance(year, (int, float)) or str(month).lower()[:3] not in MONTHS:
                continue
            start, end = period_bounds(int(year), MONTHS.index(month.lower()[:3]) + 1, 1)
            for flow, col in (("export", 2), ("import", 8)):
                value = sheet.cell_value(index, col)
                yield {
                    "period_start": start, "period_end": end, "frequency": "month",
                    "publication_date": publication, "direction": flow, "geography": "Всего",
                    "indicator": "goods_trade_value_fob", "currency_group": None,
                    "currency_group_label": None, "value": float(value) if isinstance(value, (int, float)) else None,
                    "unit": "usd_mn", "sheet": sheet.name,
                    "cell": f"{get_column_letter(col + 1)}{index + 1}",
                    "methodology_note": "Торговля товарами ФОБ по методологии платёжного баланса, возможны ревизии.",
                    **raw.reference(),
                }
    finally:
        workbook.release_resources()


def discover_derivatives(raw: Raw, run: Run):
    tree = html.parse(raw.path)
    for anchor in tree.xpath("//a[@href]"):
        url = urljoin(raw.url, anchor.get("href"))
        pattern = (r"/(?:Turnover_BIS_public_(\d{2})(20\d{2})|turnover-f_(20\d{2})|"
                   r"Outstanding_(\d{2})(\d{2})(20\d{2})|Triennial_Survey_outstanding_(20\d{2}))\.xlsx$")
        match = re.search(pattern, url, re.I)
        if not match:
            continue
        month, year, annual, pos_day, pos_month, pos_year, survey_year = match.groups()
        year_number = int(year or annual or pos_year or survey_year)
        if not run.start.year <= year_number <= run.end.year:
            continue
        if pos_year:
            key = f"positions_{pos_year}_{pos_month}_{pos_day}"
        elif survey_year:
            key = f"triennial_positions_{survey_year}"
        else:
            key = f"bis_{year}_{month}" if month else f"forward_{annual}"
        yield key, url


def derivative_turnover(raw: Raw):
    workbook = openpyxl.load_workbook(raw.path, read_only=True, data_only=True)
    try:
        if raw.key.startswith("bis_"):
            yield from bis_turnover(raw, workbook)
        elif raw.key.startswith("forward_"):
            yield from forward_turnover(raw, workbook)
        elif raw.key.startswith(("positions_", "triennial_positions_")):
            yield from outstanding_positions(raw, workbook)
    finally:
        workbook.close()


def bis_turnover(raw: Raw, workbook):
    _, year, month = raw.key.split("_")
    start, end = period_bounds(int(year), int(month), 1)
    headings = {
        "A1_RUS": ((r"^форвардные контракты", "fx_forward"), (r"^валютные свопы", "fx_swap")),
        "A5_RUS": ((r"^(валютно-|)процентные свопы", "cross_currency_swap"),
                   (r"^(валютные )?опционы", "fx_option")),
    }
    for table, sections in headings.items():
        if table not in workbook.sheetnames:
            raise SourceError(f"Missing BIS table {table}: {raw.key}")
        sheet = workbook[table]
        matrix = list(sheet.iter_rows(max_col=32, max_row=120, values_only=True))
        columns, header_index = currency_columns(matrix, {"CNY", "EUR", "USD", "Всего"})
        if not columns:
            raise SourceError(f"BIS currency headers not found: {raw.key} {table}")
        scope = {code: f"{code}/RUB" if code != "Всего" else "ALL_RUB" for code in columns}
        section = None
        totals = set()
        for index, row in enumerate(matrix[header_index + 1:], header_index + 2):
            label = table_label(row)
            match = next((code for pattern, code in sections if re.match(pattern, label)), None)
            if match:
                section = match
                continue
            if not section:
                continue
            instrument = None
            participant = "reported_market_total"
            if "беспоставоч" in label and label.startswith("в том числе") and section == "fx_forward":
                instrument = "ndf"
            elif label in {"с клиентами (нефинансовыми организациями)", "с клиентами (нефинансовыми организациями)1"}:
                instrument, participant = section, "nonfinancial_clients"
            elif ((section != "fx_option" and label == "всего")
                  or (section == "fx_option" and re.match(r"^всего (?:валютных )?опционов", label))):
                instrument = section
            if not instrument or (instrument, participant) in totals:
                continue
            observations = list(market_cells(raw, sheet.title, index, row, columns, scope, start, end,
                                             "monthly_turnover", instrument, "turnover", participant,
                                             "Методология БМР, форма 0409701. NDF входит в форварды."))
            if observations:
                totals.add((instrument, participant))
                yield from observations


def table_label(row) -> str:
    return next((cleaned(value).lower() for value in row[:3]
                 if isinstance(value, str) and cleaned(value) and not cleaned(value).isdigit()), "")


def currency_columns(matrix: list, currencies: set[str]):
    for i, row in enumerate(matrix[:15]):
        names = {cleaned(value): j for j, value in enumerate(row) if cleaned(value) in currencies}
        if {"USD", "EUR"}.issubset(names):
            return names, i
    return {}, 0


def market_cells(raw: Raw, table: str, index: int, row, columns: dict, scope: dict,
                 start: date, end: date, indicator: str, instrument: str, measure: str,
                 participant: str, note: str):
    for currency, col in columns.items():
        value = row[col]
        if isinstance(value, (int, float)):
            yield {
                "period_start": start, "period_end": end, "publication_date": None,
                "indicator": indicator, "instrument": instrument, "currency_pair": scope[currency],
                "measure_type": measure, "participant_scope": participant, "value": float(value),
                "unit": "usd_mn", "sheet": table, "cell": f"{get_column_letter(col + 1)}{index}",
                "methodology_note": note, **raw.reference(),
            }


def outstanding_positions(raw: Raw, workbook):
    if raw.key.startswith("triennial_"):
        dt = date(int(raw.key.rsplit("_", 1)[1]), 7, 1)
        indicator = "triennial_gross_notional_outstanding"
    else:
        dt = date.fromisoformat(raw.key.removeprefix("positions_").replace("_", "-"))
        indicator = "monthly_gross_notional_outstanding"
    tables = [x for x in ("O1_RUS", "OUT_1RUS", "OUT_2RUS") if x in workbook.sheetnames]
    if not tables:
        raise SourceError(f"No supported FX outstanding sheet in {raw.key}")
    for table in tables:
        matrix = list(workbook[table].iter_rows(max_col=50, max_row=85, values_only=True))
        columns, header = currency_columns(matrix, {"USD", "EUR", "CNY", "RUB", "Всего", "ВСЕГО"})
        if not columns:
            continue
        scope = {currency: "ALL" if currency.casefold() == "всего" else currency for currency in columns}
        section = None
        totals = set()
        for index, row in enumerate(matrix[header + 1:], header + 2):
            label = table_label(row)
            if label.startswith("форвардные контракты и валютные свопы"):
                section = "fx_forwards_and_swaps"
            elif label.startswith("валютно-процентные свопы"):
                section = "cross_currency_swap"
            elif re.match(r"^(валютные )?опционы", label):
                section = "fx_option"
            elif label.startswith(("своп валютными депозитами", "процентные свопы")):
                section = None
            instrument = ("fx_derivatives_total" if label.startswith(("всего валютных контрактов", "всего контрактов"))
                          and table != "OUT_2RUS" and "золот" not in label else None)
            if section in {"fx_forwards_and_swaps", "cross_currency_swap"} and label == "всего":
                instrument = section
            if section == "fx_option" and label.startswith("всего опционов"):
                instrument = section
            if not instrument or instrument in totals:
                continue
            observations = list(market_cells(raw, table, index, row, columns, scope, dt, dt,
                                             indicator, instrument, "gross_notional_outstanding",
                                             "reporting_institutions", "Номинальный брутто-объём. "
                                             "Валютные разрезы включают обе стороны валютной пары."))
            if observations:
                totals.add(instrument)
                yield from observations


def forward_turnover(raw: Raw, workbook):
    year = int(raw.key.rsplit("_", 1)[1])
    sheet = workbook["ALL_TOTAL"]
    block = None
    for index, row in enumerate(sheet.values, 1):
        if cleaned(row[0]) in {"Все валюты", "Российский рубль", "Доллар США", "Евро"}:
            block = {"Все валюты": "ALL", "Российский рубль": "RUB",
                     "Доллар США": "USD", "Евро": "EUR"}[cleaned(row[0])]
        month = cleaned(row[0]).lower()[:3]
        if not block or month not in MONTHS or not isinstance(row[1], (int, float)):
            continue
        start, end = period_bounds(year, MONTHS.index(month) + 1, 1)
        yield {
            "period_start": start, "period_end": end, "publication_date": None,
            "indicator": "average_daily_interbank_term_turnover", "instrument": "term_market_total",
            "currency_pair": block, "measure_type": "average_daily_turnover",
            "participant_scope": "interbank_market", "value": float(row[1]), "unit": "usd_mn_per_day",
            "sheet": sheet.title, "cell": f"B{index}",
            "methodology_note": "Методология Банка России. Срочный межбанковский рынок, среднедневной оборот.",
            **raw.reference(),
        }


def pdf_links(raw: Raw):
    tree = html.parse(raw.path)
    for anchor in tree.xpath("//a[@href]"):
        url = urljoin(raw.url, anchor.get("href"))
        label = cleaned(anchor.text_content())
        if urlsplit(url).path.lower().endswith(".pdf") and label:
            yield url, label


def report_period(heading: str):
    s = cleaned(heading).upper().replace("КВ.", "К").replace("ПОЛУГОДИЕ", "П")
    found = re.fullmatch(r"(?:(\d)\s*([КП])\s*)?(20\d{2})", s)
    if found:
        number, kind, year = found.groups()
        if kind == "К" and 1 <= int(number) <= 4:
            return period_bounds(int(year), (int(number) - 1) * 3 + 1, 3)
        if kind == "П" and 1 <= int(number) <= 2:
            return period_bounds(int(year), (int(number) - 1) * 6 + 1, 6)
        if kind is None:
            return period_bounds(int(year), 1, 12)
    point = re.fullmatch(r"(\d{2})\.(\d{2})\.(20\d{2})", s)
    if point:
        d, m, y = map(int, point.groups())
        dt = date(y, m, d)
        if d == 1 and m in {1, 4, 7, 10}:
            dt -= timedelta(days=1)
        return dt, dt
    return None


def bank_value(value: str) -> float | None:
    cleaned_value = cleaned(value).replace("%", "").replace("*", "").replace("−", "-").strip()
    if cleaned_value.startswith("(") and cleaned_value.endswith(")"):
        cleaned_value = "-" + cleaned_value[1:-1]
    if not re.fullmatch(r"-?[\d ]+(?:[,.]\d+)?", cleaned_value):
        return None
    return float(decimal(cleaned_value))


def press_release_rows(raw: Raw, publication: date):
    tree = html.parse(raw.path)
    for table_index, table in enumerate(tree.xpath("//table"), 1):
        positions = {}
        for row_index, row in enumerate(table.xpath(".//tr"), 1):
            fields = row.xpath("./td|./th")
            if not fields:
                continue
            values = [cleaned(field.text_content()) for field in fields]
            indicator = values[0].lower()
            current = {i: p for i, heading in enumerate(values[1:], 1)
                       if (p := report_period(heading)) is not None}
            if current and len(current) >= 2:
                positions = current
                continue
            if not positions:
                continue
            match = next((item for prefix, item in BANK_LINES.items() if indicator.startswith(prefix)), None)
            if match is None:
                continue
            code, unit = match
            for col, (start, end) in positions.items():
                if col >= len(values):
                    continue
                value = bank_value(values[col])
                if value is None:
                    continue
                yield {
                    "standard": "IFRS", "period_start": start, "period_end": end,
                    "publication_date": publication, "indicator": code, "indicator_original": values[0],
                    "value": value, "unit": unit, "document_type": "official_press_release",
                    "locator": f"table {table_index}, row {row_index}, col {col + 1}", "page": None,
                    "verification_status": "official_release_rounded",
                    **raw.reference(),
                }


def reviewed_observations(run: Run, source_id: str):
    with (run.root / "configs/economics_observations.csv").open(encoding="utf-8-sig", newline="") as stream:
        entries = [row for row in csv.DictReader(stream) if row["source_id"] == source_id]
    books = {}
    try:
        for item in entries:
            raws = run.raw(source_id, item["raw_key"])
            if len(raws) != 1:
                raise SourceError(f"Expected one source file for {item['raw_key']}")
            raw = raws[0]
            if raw.path not in books:
                books[raw.path] = openpyxl.load_workbook(raw.path, read_only=True, data_only=True)
            value = books[raw.path][item["sheet"]][item["cell"]].value
            if not isinstance(value, (float, int)):
                raise SourceError(f"Reviewed source cell is not numeric: {item['sheet']}!{item['cell']}")
            yield {
                **{k: v or None for k, v in item.items() if k != "raw_key"},
                "period_start": date.fromisoformat(item["period_start"]),
                "period_end": date.fromisoformat(item["period_end"]),
                "publication_date": date.fromisoformat(item["publication_date"]) if item["publication_date"] else None,
                "value": value, **raw.reference(),
            }
    finally:
        for book in books.values():
            book.close()
