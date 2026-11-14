from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlencode
from xml.etree import ElementTree

import openpyxl
from lxml import html

from data_pipeline.core import Run, Raw, SourceError


def russian_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value).strip(), "%d.%m.%Y").date()


def decimal(value) -> Decimal:
    return Decimal("".join(str(value).split()).replace(",", "."))


def fx_url(run: Run, identifier: str) -> str:
    args = {
        "date_req1": run.start.strftime("%d/%m/%Y"),
        "date_req2": run.end.strftime("%d/%m/%Y"),
        "VAL_NM_RQ": identifier,
    }
    return run.sources["cbr_fx"]["endpoint"] + "?" + urlencode(args)


def cbr_table_url(run: Run, source_id: str) -> str:
    args = {"UniDbQuery.Posted": "True", "UniDbQuery.From": run.start.strftime("%d.%m.%Y"),
            "UniDbQuery.To": run.end.strftime("%d.%m.%Y")}
    return run.sources[source_id]["url"] + "?" + urlencode(args)


def ruonia_xlsx_url(run: Run) -> str:
    args = {"FromDate": run.start.strftime("%m/%d/%Y"), "ToDate": run.end.strftime("%m/%d/%Y"),
            "posted": "True", "backUrl": "/hd_base/ruonia/dynamics/"}
    return "https://www.cbr.ru/Queries/UniDbQuery/DownloadExcel/14315?" + urlencode(args)


def collect_fx(run: Run) -> None:
    failures = []
    for currency, (identifier, _) in run.sources["cbr_fx"]["codes"].items():
        try:
            raw = run.fetch("cbr_fx", currency, fx_url(run, identifier), ".xml")
            if not list(spot_rows(raw, currency, identifier, run.sources["cbr_fx"]["codes"][currency][1])):
                raise SourceError(f"CBR returned no official rates for {currency}")
        except SourceError as exc:
            failures.append(exc)
    if failures:
        raise SourceError(" | ".join(str(exc) for exc in failures), failures[0].status)


def collect_rate(run: Run, source_id: str) -> None:
    raw = run.fetch(source_id, "history", cbr_table_url(run, source_id), ".html")
    if not list(rate_rows(raw)):
        raise SourceError(f"No rate observations recognized for {source_id}")
    if source_id == "cbr_ruonia":
        run.fetch(source_id, "xlsx_history", ruonia_xlsx_url(run), ".xlsx")


def spot_rows(raw: Raw, currency: str, identifier: str, currency_code: str):
    if raw.path.suffix == ".xml":
        root = ElementTree.parse(raw.path).getroot()
        if root.tag != "ValCurs" or root.get("ID") != identifier:
            raise SourceError(f"Wrong CBR XML instrument for {currency}")
        previous_date = None
        for row in root.findall("Record"):
            if row.get("Id") != identifier:
                raise SourceError(f"Unexpected CBR record Id for {currency}")
            dt = russian_date(row.attrib["Date"])
            if previous_date and dt < previous_date:
                raise SourceError(f"Out-of-order CBR XML at {currency} {dt}")
            previous_date = dt
            yield spot_row(raw, dt, currency, identifier, currency_code,
                           row.findtext("Nominal"), row.findtext("Value"), row.findtext("VunitRate"))
        return
    if raw.path.suffix != ".xlsx":
        raise SourceError(f"Unknown CBR FX format: {raw.path.suffix}")
    for row in sheet_rows(raw):
        # The CBR historical XLSX exports the rate as printed, and can include VunitRate.
        if len(row) < 3:
            continue
        try:
            dt = russian_date(row[0])
        except (TypeError, ValueError):
            continue
        yield spot_row(raw, dt, currency, identifier, currency_code,
                       row[1], row[2], row[3] if len(row) > 3 else None)


def spot_row(raw: Raw, dt: date, currency: str, identifier: str, currency_code: str,
             nominal_value, rate_value, unit_value) -> dict:
    nominal = decimal(nominal_value)
    original = decimal(rate_value)
    if nominal <= 0 or nominal != int(nominal) or original <= 0:
        raise SourceError(f"Invalid FX rate or nominal for {currency} on {dt}")
    unit = original / nominal
    if unit_value is not None and abs(decimal(unit_value) - unit) > Decimal("0.00001"):
        raise SourceError(f"Unit-rate disagreement for {currency} on {dt}")
    return {
        "date": dt, "currency": currency, "currency_code": currency_code,
        "cbr_currency_id": identifier, "nominal": int(nominal),
        "rate_original": float(original), "rub_per_unit": float(unit),
        "publication_date": None, "date_role": "official_effective_date", **raw.reference(),
    }


def sheet_rows(raw: Raw):
    workbook = openpyxl.load_workbook(raw.path, read_only=True, data_only=True)
    try:
        yield from workbook.worksheets[0].values
    finally:
        workbook.close()


def rate_rows(raw: Raw):
    ruonia = raw.source_id == "cbr_ruonia"
    rows = sheet_rows(raw)
    if raw.path.suffix == ".html":
        doc = html.parse(raw.path)
        tables = doc.xpath("//table[.//th[contains(., 'RUONIA') or contains(., 'Ставка')]]")
        if not tables:
            raise SourceError(f"Rate table not found in {raw.path.name}")
        rows = ([cell.text_content().strip() for cell in row.xpath("./td|./th")]
                for row in tables[-1].xpath(".//tr"))
    for row in rows:
        if len(row) < 2 or row[0] is None or row[1] is None:
            continue
        try:
            dt = russian_date(row[0])
        except (TypeError, ValueError):
            continue
        rate = decimal(row[1])
        published = None
        if ruonia and len(row) >= 11 and row[10] not in (None, "", "—", "-"):
            published = russian_date(row[10])
        if published and published < dt:
            raise SourceError(f"RUONIA publication precedes the rate date: {dt}")
        yield {
            "date": dt, "rate_name": "RUONIA" if ruonia else "CBR_KEY_RATE",
            "tenor": "ON" if ruonia else None, "rate": float(rate), "rate_unit": "pct_pa",
            "publication_date": published, **raw.reference(),
        }
