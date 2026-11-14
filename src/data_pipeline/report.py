from __future__ import annotations

from collections import Counter
from pathlib import Path

from data_pipeline.core import Run, STATUS_UNVERIFIED, atomic_write
from data_pipeline.datasets import csv_bytes
from data_pipeline.reconciliation import workbook_audit

FIELDS = ("source_id", "name", "organization", "url", "checked_at", "period_from", "period_to",
          "format", "license_or_terms", "method", "status", "records", "raw_files", "bytes",
          "paths", "limitations", "quality_status")


def table(*values) -> str:
    return "| " + " | ".join(str(x if x not in (None, "") else "—").replace("|", r"\|").replace("\n", " ")
                             for x in values) + " |"


def write(path: Path, lines: list[str]) -> None:
    atomic_write(path, ("\n".join(lines).rstrip() + "\n").encode())


def reports(run: Run) -> None:
    state = run.state
    folder = run.root / "reports"
    datasets, quality = state["datasets"], state["quality"]
    if datasets:
        workbook_audit(run)
    sources = []
    for identifier, source in run.sources.items():
        result = state["sources"].get(identifier, {})
        raw = {x["path"]: x for x in run.downloads if x["source_id"] == identifier}
        available = [q for path, q in quality.items() if not path.endswith("fx_spot_daily.csv")
                     and identifier in q.get("source_rows", {})]
        periods = [q["source_periods"][identifier] for q in available
                   if identifier in q.get("source_periods", {})]
        sources.append({
            "source_id": identifier, "name": source["name"], "organization": source["organization"],
            "url": source["url"], "checked_at": result.get("checked_at"),
            "period_from": min((period["min"] for period in periods), default=None),
            "period_to": max((period["max"] for period in periods), default=None),
            "format": source["formats"], "license_or_terms": source["terms"],
            "method": " / ".join(sorted({x["method"] for x in raw.values()})),
            "status": result.get("status", STATUS_UNVERIFIED),
            "records": sum(q["source_rows"][identifier] for q in available),
            "raw_files": len(raw), "bytes": sum(x["size"] for x in raw.values()),
            "paths": " | ".join(raw), "limitations": result.get("detail") or source.get("manual"),
            "quality_status": ("ERROR" if any(q["errors"] for q in available) else
                               "WARNINGS" if any(q["warnings"] for q in available) else
                               "PASSED" if available else "NO_PROCESSED_ROWS"),
        })
    atomic_write(run.metadata / "source_registry.csv", csv_bytes(sources, FIELDS))
    write(folder / "data_sources.md", [
        "# Источники данных", "", "| Источник | Организация | Статус | Файлы | Строки | Условия |",
        "|---|---|---|---:|---:|---|",
        *(table(f"[{s['name']}]({s['url']})", s["organization"], s["status"],
                s["raw_files"], s["records"], s["license_or_terms"]) for s in sources),
        "", "Точные URL, SHA-256 и размеры первичных файлов содержатся в `data/metadata/downloads.json`.",
        "Строки источника суммируются по выходам без CSV-копии курсов.",
    ])
    rows = []
    catalog_details = []
    for path, meta in sorted(datasets.items()):
        q = quality.get(path, {})
        period = f"{q['date_min']} — {q['date_max']}" if q.get("date_min") else None
        rows.append(table(f"`{path}`", meta["rows"], period, meta["bytes"], ", ".join(meta["sources"])))
        catalog_details += ["", f"## {Path(path).name}", "",
                            ", ".join(f"`{field}`" for field in meta["fields"]),
                            "", f"SHA-256 `{meta['sha256']}`."]
    write(folder / "dataset_catalog.md", [
        "# Каталог данных БСПБ FX Control", "", "| Файл | Строки | Даты | Байт | Источники |",
        "|---|---:|---|---:|---|", *rows, *catalog_details,
    ])
    write(run.metadata / "data_dictionary.md", [
        "# Словарь данных", "",
        "- Даты ISO 8601. Временные метки сбора используют Europe/Moscow.",
        "- Дата официального курса означает дату действия. XML не публикует время объявления.",
        "- `currency_code` — числовой код ISO 4217. `cbr_currency_id` — идентификатор Банка России.",
        "- `rub_per_unit = rate_original / nominal`. Календарь источника сохранён.",
        "- `rate` хранит проценты годовых. `publication_date` у RUONIA учитывает лаг публикации.",
        "- `price_unit` определяет цену MOEX за единицу или лот. `settlement_price` и `close` — разные поля.",
        "- `open_interest` измеряется в контрактах. Истории хранятся по SECID, борду и дате.",
        "- `traded` показывает наличие сделок. Нулевые заглушки OHLC переводятся в null. Для клиринга после экспирации есть отдельный флаг.",
        "- `unreviewed_no_hit` означает отсутствие совпадений по правилам. Эталонный статус требует проверки.",
        "- Смещения `start` и `end` считаются по символам Unicode. Правая граница исключается.",
        "- `dedup_group` объединяет совпадающие нормализованные тексты. Перед экспериментом учесть семьи шаблонов.",
        "- `rub_th` — тыс. рублей, `rub_mn` — млн рублей, `rub_bn` — млрд рублей, `usd_mn` — млн долларов.",
        "- `publication_date` у внешней торговли содержит дату редакции. История прежних редакций недоступна.",
        "- `measure_type` различает месячный и среднедневной обороты и открытые позиции. NDF входит в форварды.",
        "- `listed_430r` соответствует перечню в распоряжении № 430-р. `other_fx` — прочие валюты по источнику.",
        "- `source_id` и `source_sha256` указывают на первичный файл. `cell`, `page` и `locator` — место в источнике.",
        "- Для тестов на истории использовать данные с учётом даты доступности. Дневные цены MOEX доступны после сессии.",
    ])
    raw_qc = state.get("raw_integrity", {})
    errors = sum(len(q["errors"]) for q in quality.values()) + len(raw_qc.get("errors", []))
    warnings = sum(len(q["warnings"]) for q in quality.values())
    qc_lines = ["# Контроль качества", "", f"Ошибок **{errors}**, предупреждений **{warnings}**.",
                "", f"Проверены SHA-256 **{raw_qc.get('files', 0)}** первичных файлов.",
                *(f"- {x}" for x in raw_qc.get("errors", []))]
    for path, q in sorted(quality.items()):
        qc_lines += ["", f"## {Path(path).name}", "",
                     f"- Строк {q.get('rows', 0)}. Уникальных дат {q.get('unique_dates', '—')}."]
        qc_lines.extend(f"- Ошибка. {item}" for item in q["errors"])
        qc_lines.extend(f"- Предупреждение. {item}" for item in q["warnings"])
        if q.get("missing_pct"):
            qc_lines.append("- Пропуски, % — " + ", ".join(f"{k} {v}" for k, v in q["missing_pct"].items()) + ".")
        for name, series in q.get("series", {}).items():
            qc_lines.append(f"- {name} — {series['rows']} строк, {series['from']} — {series['to']}.")
            if series.get("last_trade"):
                qc_lines.append(f"  - Последняя дата со сделками и опубликованной ценой закрытия {series['last_trade']}.")
                if series.get("eligible_last_trade") != series["last_trade"]:
                    qc_lines.append(f"  - Последняя пригодная для бэктеста дата {series['eligible_last_trade']}.")
            if series.get("longest_gap_days"):
                qc_lines.append(f"  - Максимальный интервал {series['longest_gap_days']} календарных дней.")
            for event in series.get("nominal_changes", []):
                qc_lines.append(f"  - {event['date']} — номинал {event['nominal']}.")
            for event in series.get("flagged_jumps", []):
                qc_lines.append(f"  - {event['date']} — изменение {event['pct_change']:+g}%.")
        if "cbr_independent_crosscheck_rows" in q:
            qc_lines.append(f"- Сверено {q['cbr_independent_crosscheck_rows']} значений с XML_daily.")
        if "ruonia_crosschecked_rows" in q:
            qc_lines.append(f"- HTML и XLSX RUONIA сверены по {q['ruonia_crosschecked_rows']} наблюдениям.")
        for field in ("contract_classes", "languages", "measure_types"):
            if field in q:
                qc_lines.append("- " + ", ".join(f"{k} — {v}" for k, v in q[field].items()) + ".")
    write(folder / "data_quality.md", qc_lines)

    totals = Counter(s["status"] for s in sources)
    raw_sizes = {item["path"]: item["size"] for item in run.downloads}
    total_bytes = sum(raw_sizes.values()) + sum(m["bytes"] for m in datasets.values())
    write(folder / "data_collection_report.md", [
        "# БСПБ FX Control — сбор и подготовка данных", "",
        f"Период запроса **{run.start.isoformat()} — {run.end.isoformat()}**.", "",
        f"Первичных файлов **{len(raw_sizes)}**. Выходных файлов **{len(datasets)}**, "
        f"с данными **{sum(m['rows'] > 0 for m in datasets.values())}**. Общий объём **{total_bytes:,} байт**.",
        "", "| Статус | Источников |", "|---|---:|", *(table(k, v) for k, v in sorted(totals.items())),
        "", "## Файлы и покрытие", "", "| Файл | Строки | Фактические даты | Байт | Источники |",
        "|---|---:|---|---:|---|", *rows, "", "## Ограничения источников", "",
        *(f"- **{s['source_id']}**. {s['limitations']}" for s in sources if s["limitations"]),
        "", "## Проверки и повторный запуск", "",
        f"- Ошибок качества **{errors}**. Предупреждений качества **{warnings}**.",
        "- Реестр находится в `data/metadata/source_registry.csv`. Команды запуска приведены в `README.md`.",
        "- Сверка с материалами кейса описана в `source_reconciliation.md`.",
        "- Ограничения по каждому компоненту приведены в `research_notes.md`.",
    ])
