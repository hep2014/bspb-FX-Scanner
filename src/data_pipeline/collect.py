from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from lxml import html

from data_pipeline.core import (
    Run, SourceError, STATUS_ABSENT, STATUS_OK, STATUS_RESTRICTED, STATUS_UNVERIFIED, STATUS_WARN,
)
from data_pipeline.sources import cbr, contracts, economics, moex

LOG = logging.getLogger(__name__)
GROUPS = {
    "cbr": ("cbr_fx", "cbr_ruonia", "cbr_key_rate"),
    "moex": ("moex",),
    "contracts": ("cuad", "contractnli", "eis", "sec", "stanford_mcc", "russian_court"),
    "economics": ("cbr_trade_structure", "cbr_trade_volume", "cbr_derivatives"),
    "bspb": ("bspb_ifrs", "bspb_ras", "bspb_release", "case_workbook"),
}
RAW_KEYS = {
    "cbr_trade_structure": ("currency_structure", ".xlsx"),
    "cbr_trade_volume": ("trade_volume", ".xls"),
}


def fetch_derivatives(run: Run) -> str:
    index = run.fetch("cbr_derivatives", "index", run.sources["cbr_derivatives"]["url"], ".html")
    failures = []
    count = 0
    for key, url in dict(economics.discover_derivatives(index, run)).items():
        try:
            run.fetch("cbr_derivatives", key, url, ".xlsx")
            count += 1
        except SourceError as exc:
            failures.append(f"{key}: {exc}")
    if count == 0:
        failures.append("No published BIS/CBR turnover workbooks were obtained")
    for key, url in run.sources["cbr_derivatives"]["reviews"].items():
        try:
            run.fetch("cbr_derivatives", key, url, ".pdf")
        except SourceError as exc:
            failures.append(f"{key}: {exc}")
    return " | ".join(failures)


def bank_links(index, run: Run):
    from urllib.parse import urljoin
    import re

    seen = set()
    tree = html.parse(index.path)
    for anchor in tree.xpath("//a[@href]"):
        url = urljoin(index.url, anchor.get("href"))
        name = Path(urlsplit(url).path).name
        suffix = Path(name).suffix.lower()
        if suffix not in {".pdf", ".zip", ".7z", ".xlsx", ".xls"} or url in seen:
            continue
        label = economics.cleaned(anchor.text_content())
        context = label
        table = anchor.xpath("ancestor::table[1]")
        if table:
            context += " " + economics.cleaned(table[0].xpath("string(.//tr[1])"))
        years = {int(y) for y in re.findall(r"20(?:1[0-9]|2[0-9]|3[0-9])", context)}
        if not years:
            continue
        first_year = run.start.year + (1 if "на 1 января" in label.lower() else 0)
        if not any(first_year <= year <= run.end.year + 1 for year in years):
            continue
        seen.add(url)
        yield Path(name).stem, url, suffix


def fetch_reports(run: Run, source_id: str) -> str:
    source = run.sources[source_id]
    index = run.fetch(source_id, "index", source["url"], ".html")
    failures = []
    count = 0
    for key, url, suffix in bank_links(index, run):
        try:
            run.fetch(source_id, key, url, suffix)
            count += 1
        except SourceError as exc:
            failures.append(f"{key}: {exc}")
    if count == 0:
        failures.append("No primary financial report was downloaded")
    return " | ".join(failures)


def collect_one(run: Run, source_id: str) -> tuple[str, str]:
    source = run.sources[source_id]
    if source_id == "cbr_fx":
        cbr.collect_fx(run)
        for day in (run.start + timedelta(days=9), run.end):
            if day > run.end:
                continue
            url = "https://www.cbr.ru/scripts/XML_daily.asp?" + urlencode({"date_req": day.strftime("%d/%m/%Y")})
            run.fetch(source_id, f"daily_{day}", url, ".xml")
        run.fetch(source_id, "currency_dictionary", "https://www.cbr.ru/scripts/XML_valFull.asp", ".xml")
    elif source_id in {"cbr_ruonia", "cbr_key_rate"}:
        cbr.collect_rate(run, source_id)
    elif source_id == "moex":
        message = moex.collect(run)
        return (STATUS_WARN, message) if message else (STATUS_OK, "")
    elif source_id == "cuad":
        contracts.download_cuad(run)
    elif source_id in {"eis", "sec", "stanford_mcc"}:
        message = contracts.collect_external(run, source_id)
        if message:
            if source_id == "sec":
                return STATUS_RESTRICTED, message
            run.fetch(source_id, "public_index", source["url"], ".html")
            return (STATUS_WARN if run.raw(source_id) else STATUS_UNVERIFIED), message
    elif source_id == "russian_court":
        for key, url in source["documents"].items():
            if not run.raw(source_id, key, url) or run.refresh:
                run.fetch(source_id, key, url, ".html")
        return STATUS_WARN, "Судебные выдержки описывают договорные условия. Оригиналы договоров отсутствуют."
    elif source_id == "contractnli":
        if not run.raw(source_id, "archive"):
            return STATUS_RESTRICTED, source["manual"]
    elif source_id in RAW_KEYS:
        key, suffix = RAW_KEYS[source_id]
        run.fetch(source_id, key, source["endpoint"], suffix)
    elif source_id == "cbr_derivatives":
        message = fetch_derivatives(run)
        return (STATUS_WARN, message) if message else (STATUS_OK, "")
    elif source_id in {"bspb_ifrs", "bspb_ras"}:
        message = fetch_reports(run, source_id)
        return (STATUS_WARN, message) if message else (STATUS_OK, "")
    elif source_id == "bspb_release":
        for key, (url, _) in source["releases"].items():
            run.fetch(source_id, key, url, ".html")
    elif source_id == "case_workbook":
        if not run.raw(source_id, "workbook"):
            return STATUS_UNVERIFIED, source["manual"]
    else:
        raise ValueError(f"No collector for {source_id}")
    return STATUS_OK, ""


def collect(run: Run, selected: list[str]) -> int:
    failed = 0
    source_ids = dict.fromkeys(source_id for group in selected for source_id in GROUPS.get(group, (group,)))
    for source_id in source_ids:
        LOG.info("Collect %s", source_id)
        try:
            status, detail = collect_one(run, source_id)
        except SourceError as exc:
            status, detail = exc.status, str(exc)
            if run.raw(source_id):
                status = STATUS_WARN
            LOG.warning("%s: %s", source_id, exc)
        run.source_result(source_id, status, detail)
        if status in {STATUS_ABSENT, STATUS_UNVERIFIED, STATUS_RESTRICTED}:
            failed += 1
    return failed
