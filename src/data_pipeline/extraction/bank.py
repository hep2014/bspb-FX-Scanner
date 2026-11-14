from __future__ import annotations

import csv
import locale
import re
import shutil
import subprocess
from datetime import date, timedelta
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

import openpyxl
from openpyxl.utils import get_column_letter

from data_pipeline.core import Raw, Run, SourceError
from data_pipeline.sources.economics import MONTHS, bank_value, cleaned, period_bounds

PDF_METRICS = (
    ("net_interest_income", r"^Чистые процентные доходы(?:\s+\d+)?$"),
    ("gross_fee_income", r"^Комиссионные доходы(?:\s+\d+)?$"),
    ("fee_expense", r"^Комиссионные расходы(?:\s+\d+)?$"),
    ("fx_derivatives_metals_income", r"^Чистые .+операций с иностранной валютой.+производными финансовыми инструментами.+металлами"),
    ("net_financial_securities_income", r"^Чистые .+операций с ценными бумагами"),
    ("staff_expense", r"^[-–]?\s*[Рр]асходы на персонал"),
    ("administrative_expenses", r"^[-–]?\s*(?:другие )?административные и прочие операционные расходы(?:\s+\d+)?$"),
    ("net_profit", r"^Прибыль за (?:(?:отчетный )?год|(?:отчетный )?период)(?:\s+\d+)?$"),
    ("assets", r"^(?:Итого|Всего)(?: по разделу)? [Аа]ктивов(?:\s+\d+)?$"),
    ("equity", r"^(?:Итого|Всего)(?: собственный)? капитал(?:а)?(?:\s+\d+)?$"),
)
RAS_METRICS = {
    "806": (("assets", r"^Всего активов"), ("equity", r"^Всего источников собственных средств")),
    "807": (
        ("net_interest_income", r"^Чистые процентные доходы \(отрицательная процентная маржа\)$"),
        ("fx_operations_income", r"^Чистые доходы от операций с иностранной валютой$"),
        ("fx_revaluation_income", r"^Чистые доходы от переоценки иностранной валюты$"),
        ("gross_fee_income", r"^Комиссионные доходы$"),
        ("fee_expense", r"^Комиссионные расходы$"),
        ("operating_expenses", r"^Операционные расходы$"),
        ("net_profit", r"^Прибыль \(убыток\) за отчетный период$"),
        ("profit_loss_fv_assets", r"^Чистые доходы от операций с финансовыми активами, оцениваемыми по справедливой стоимости через прибыль или убыток"),
    ),
    "808": (
        ("regulatory_common_equity", r"^Базовый капитал, итого"),
        ("tier1_capital", r"^Основной капитал, итого"),
        ("regulatory_total_capital", r"^(?:Собственные средства \(капитал\), итого|Собственные средства \(капитал\) \(сумма)"),
        ("capital_adequacy_n1_0", r"^Норматив достаточности собственных средств \(капитала\).+Н1\.0"),
    ),
}
SOURCE_NA = {"", "X", "Х", "-", "—", "…", "Н/П", "неприменимо"}
NUMERIC = r"(?:\(?-?\d[\d ]*(?:[,.]\d+)?\)?|[-–—])"
METRICS_WITH_POINT_IN_TIME = {"assets", "equity", "tier1_capital", "regulatory_common_equity",
                              "regulatory_total_capital", "capital_adequacy_n1_0"}


def financial_row(raw: Raw, standard: str, start: date, end: date, published: date | None,
                  code: str, original: str, value: float | None, unit: str, locator: str,
                  page: int | None, document_type: str, verification_status: str) -> dict:
    if code in METRICS_WITH_POINT_IN_TIME:
        start = end
    return {
        "standard": standard, "period_start": start, "period_end": end,
        "publication_date": published, "indicator": code, "indicator_original": original,
        "value": value, "unit": unit, "document_type": document_type, "locator": locator,
        "page": page, "verification_status": verification_status, **raw.reference(),
    }


def ifrs_reports(run: Run):
    try:
        from pypdf import PdfReader
    except ImportError:
        return
    for raw in run.raw("bspb_ifrs"):
        if raw.path.suffix != ".pdf":
            continue
        reader = PdfReader(raw.path)
        first_pages = []
        for i, page in enumerate(reader.pages[:14], 1):
            if i > 2:
                text = page.extract_text(extraction_mode="layout", layout_mode_space_vertically=False) or ""
                first_pages.append((i, text))
        published = ifrs_publication(run, raw)
        for row in extract_ifrs(raw, first_pages):
            row["publication_date"] = published
            yield row


def ifrs_publication(run: Run, raw: Raw) -> date | None:
    from lxml import html
    from urllib.parse import urljoin

    indexes = run.raw("bspb_ifrs", "index")
    if not indexes:
        return None
    index = indexes[-1]
    for anchor in html.parse(index.path).xpath("//a[@href]"):
        if urljoin(index.url, anchor.get("href")) != raw.url:
            continue
        for node in list(anchor.iterancestors())[:4]:
            label = cleaned(node.text_content())
            if len(label) > 550:
                break
            match = re.search(r"Дата размещения.+?(\d{2})\.(\d{2})\.(20\d{2})", label)
            if match:
                day, month, year = map(int, match.groups())
                return date(year, month, day)
    return None


def header_period(text: str) -> tuple[date, date] | None:
    head = " ".join(line.strip() for line in text.splitlines()[:7]).lower()
    date_match = re.search(r"(\d{1,2})\s+(января|марта|июня|сентября|декабря)\s+(20\d{2})", head)
    if not date_match:
        return None
    day, month_text, year_text = date_match.groups()
    year = int(year_text)
    month = {"января": 1, "марта": 3, "июня": 6, "сентября": 9, "декабря": 12}[month_text]
    end = date(year, month, int(day))
    if month == 1 and int(day) == 1:
        end -= timedelta(days=1)
    return date(end.year, 1, 1), end


def extract_ifrs(raw: Raw, pages: list[tuple[int, str]]):
    seen = set()
    for page, text in pages:
        if not re.search(r"\(в\s+(тысячах|миллионах)\s+российских\s+рубл(?:ей|ях)\)", text, re.I):
            continue
        top = " ".join(line.strip() for line in text.splitlines()[:6]).lower()
        balance = "финансовом положении" in top
        income = "совокупном доходе" in top or "прибылях и убытках" in top
        if not balance and not income:
            continue
        period = header_period(text)
        if period is None:
            continue
        unit = "rub_mn" if re.search(r"в\s+миллионах\s+российских", text, re.I) else "rub_th"
        pending = []
        for line_number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                pending.clear()
                continue
            # Layout PDF text separates note numbers and accounting columns by runs of spaces.
            chunks = re.split(r"\s{2,}", stripped)
            if len(chunks) == 1 or not re.fullmatch(NUMERIC, chunks[1].strip()):
                if len(chunks) == 1 and len(pending) < 4:
                    pending.append(chunks[0])
                else:
                    pending = [chunks[0]]
                continue
            numeric_fields = [s for s in chunks[1:] if re.fullmatch(NUMERIC, s.strip())]
            if len(numeric_fields) < 2:
                pending.clear()
                continue
            candidates = [cleaned(" ".join([*pieces, chunks[0]]))
                          for pieces in (pending[-3:], pending[-2:], pending[-1:], [])]
            pending.clear()
            mapping = next(((code, label) for code, expression in PDF_METRICS for label in candidates
                            if re.search(expression, label, re.I)), None)
            if mapping is None:
                continue
            code, label = mapping
            if balance != (code in METRICS_WITH_POINT_IN_TIME) or code in seen:
                continue
            values_count = 4 if "3 и 6 месяцев" in top or "3 и 9 месяцев" in top else 2
            value_token = numeric_fields[-values_count] if len(numeric_fields) >= values_count else None
            if not value_token or value_token in SOURCE_NA:
                continue
            value = bank_value(value_token)
            if value is not None:
                seen.add(code)
                yield financial_row(raw, "IFRS", *period, None, code, label, value, unit,
                                    f"PDF page {page}, extracted line {line_number}", page,
                                    "official_primary_statement", "extracted_from_statement")


def ras_period(member: str, sheet) -> tuple[date, date] | None:
    head = " ".join(cleaned(x) for row in sheet.iter_rows(max_row=16, max_col=14, values_only=True)
                    for x in row if x is not None).lower()
    match = re.search(r"за\s+(3|6|9|12)\s+месяц\w*\s+(20\d{2})\s+г", head)
    if match:
        months, year = map(int, match.groups())
        return period_bounds(year, 1, months)
    match = re.search(r"за\s+(20\d{2})\s+год", head)
    if match:
        return period_bounds(int(match[1]), 1, 12)
    match = re.search(r"(?<!\d)(01)(01|04|07|10)(20\d{2})(?!\d)", member)
    if match:
        _, month, year = map(int, match.groups())
        end = date(year, month, 1) - timedelta(days=1)
        return date(end.year, 1, 1), end
    return None


def ras_reports(run: Run):
    for raw in run.raw("bspb_ras"):
        for name, form, data in ras_members(raw):
            workbook = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
            try:
                for sheet in workbook:
                    yield from extract_ras(raw, name, form, sheet)
            finally:
                workbook.close()


def ras_form(filename: str) -> str | None:
    name = PurePosixPath(filename).name
    found = re.search(r"(?:0409|[FfФф])?(80[678])(?=\D|$)", name)
    return found[1] if found and name.lower().endswith(".xlsx") else None


def ras_members(raw: Raw):
    limit = 20 * 1024**2
    if raw.path.suffix == ".zip":
        with ZipFile(raw.path) as archive:
            for entry in archive.infolist():
                form = ras_form(entry.filename)
                if form and entry.file_size <= limit:
                    yield entry.filename, form, archive.read(entry)
    elif raw.path.suffix == ".7z":
        tar = shutil.which("tar")
        if tar is None:
            return
        listed = subprocess.run([tar, "-tf", str(raw.path)], capture_output=True, check=False, timeout=30)
        if listed.returncode:
            return
        for name in listed.stdout.decode(locale.getpreferredencoding(False), errors="replace").splitlines():
            form = ras_form(name)
            if not form:
                continue
            result = subprocess.run([tar, "-xOf", str(raw.path), name], capture_output=True,
                                    check=False, timeout=30)
            if not result.returncode and result.stdout.startswith(b"PK") and len(result.stdout) <= limit:
                yield name, form, result.stdout


def extract_ras(raw: Raw, member: str, form: str, sheet):
    period = ras_period(member, sheet)
    if period is None:
        return
    column = None
    seen = set()
    for index, row in enumerate(sheet.iter_rows(max_col=16, values_only=True), 1):
        if column is None:
            for j, item in enumerate(row):
                label = cleaned(item).lower()
                if "тыс. руб" in label and ("за отчетный период" in label or "на отчетную дату" in label):
                    column = j
                    break
            continue
        for code, expression in RAS_METRICS[form]:
            if code in seen:
                continue
            label = next((cleaned(x) for x in row[:column] if re.search(expression, cleaned(x), re.I)), None)
            if label is None:
                continue
            original = row[column]
            value = bank_value(str(original)) if original is not None else None
            if value is None and cleaned(original) not in SOURCE_NA:
                continue
            unit = "pct" if code == "capital_adequacy_n1_0" else "rub_th"
            locator = f"{member} / {sheet.title}!{get_column_letter(column + 1)}{index}"
            seen.add(code)
            yield financial_row(raw, "RAS", *period, None, code, label, value, unit, locator, None,
                                f"CBR_form_0409{form}",
                                "withheld_in_public_form" if value is None else "extracted_from_statement")


def reviewed_pdf_rows(run: Run):
    file = run.root / "configs/bspb_pdf_observations.csv"
    if not file.exists():
        return
    try:
        from pypdf import PdfReader
    except ImportError:
        return

    pages = {}
    with file.open(encoding="utf-8-sig", newline="") as stream:
        for entry in csv.DictReader(stream):
            candidates = run.raw(entry["source_id"], entry["raw_key"])
            if not candidates:
                continue
            raw = candidates[-1]
            page = int(entry["page"])
            key = raw.sha256, page
            if key not in pages:
                pages[key] = PdfReader(raw.path).pages[page - 1].extract_text(extraction_mode="layout")
            expected = cleaned(entry["expected_line"])
            expected_value = cleaned(entry["expected_value"])
            if not any(expected in cleaned(line) and expected_value in cleaned(line)
                       for line in pages[key].splitlines()):
                raise SourceError(f"Reviewed statement line changed: {entry['raw_key']} page {page}")
            value = bank_value(expected_value)
            if value is None:
                raise SourceError(f"Reviewed statement value invalid: {entry['raw_key']} page {page}")
            yield financial_row(raw, "IFRS", date.fromisoformat(entry["period_start"]),
                                date.fromisoformat(entry["period_end"]),
                                date.fromisoformat(entry["publication_date"]), entry["indicator"],
                                entry["label"], value, entry["unit"],
                                f"PDF page {page}, reviewed table line", page, "official_primary_statement",
                                "crosschecked_pdf_line")


def financial_report_rows(run: Run):
    yield from ifrs_reports(run)
    yield from ras_reports(run)
    yield from reviewed_pdf_rows(run)
    with (run.root / "configs/bspb_balance_observations.csv").open(encoding="utf-8-sig", newline="") as stream:
        for entry in csv.DictReader(stream):
            raws = run.raw("bspb_ifrs", entry["raw_key"])
            if not raws:
                continue
            raw = raws[-1]
            if raw.sha256 != entry["sha256"]:
                raise SourceError(f"Source scan changed: {entry['raw_key']}. Check the reported balance cells.")
            point = date.fromisoformat(entry["as_of"])
            page = int(entry["page"])
            yield financial_row(raw, "IFRS", point, point, date.fromisoformat(entry["publication_date"]),
                                entry["indicator"], entry["label"], float(entry["value"]), "rub_mn",
                                f"PDF page {page}, balance sheet", page, "official_primary_statement",
                                "visually_verified_source_scan")
