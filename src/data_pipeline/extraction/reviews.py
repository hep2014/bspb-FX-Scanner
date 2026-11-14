from __future__ import annotations

import re
from datetime import date

from data_pipeline.core import Raw, SourceError
from data_pipeline.sources.economics import period_bounds

INSTRUMENTS = {
    "FX Forward, NDF": "fx_forward_and_ndf",
    "FX Swap": "fx_swap",
    "FX Option": "fx_option",
    "Cross-Currency Swap (CCS)": "cross_currency_swap",
}
PARTICIPANTS = {"Корпоративный": "corporate", "Розничный": "retail"}


def count_table(raw: Raw):
    from pypdf import PdfReader

    page = 6
    pdf = PdfReader(raw.path)
    text = pdf.pages[page - 1].extract_text(extraction_mode="layout", layout_mode_space_vertically=False)
    if not re.search(r"Табл\.\s*1\.\s*Количество внебиржевых сделок", text) or "(шт.)" not in text:
        raise SourceError("Expected count table at PDF page 6")
    periods = [period_bounds(year, month, 1) for year, last in ((2025, 12), (2026, 6))
               for month in range(1, last + 1)]
    seen = set()
    for index, line in enumerate(text.splitlines(), 1):
        fields = re.split(r"\s{2,}", line.strip())
        if len(fields) < 3 or fields[0] not in INSTRUMENTS or fields[1] not in PARTICIPANTS:
            continue
        title, client, *tokens = fields
        if len(tokens) != len(periods) or any(not re.fullmatch(r"\d(?:[\d ]*\d)?", x) for x in tokens):
            raise SourceError(f"Unexpected columns in the derivatives review table for {title} {client}")
        if (title, client) in seen:
            raise SourceError(f"Duplicate PDF row for {title} {client}")
        seen.add((title, client))
        for (start, end), token in zip(periods, tokens, strict=True):
            yield {
                "period_start": start, "period_end": end, "publication_date": date(2026, 9, 30),
                "indicator": "otc_deals_count", "instrument": INSTRUMENTS[title],
                "currency_pair": "ALL", "measure_type": "deal_count",
                "participant_scope": PARTICIPANTS[client], "value": int(token.replace(" ", "")),
                "unit": "contracts", "sheet": "PDF page 6, table 1", "cell": f"line {index}",
                "methodology_note": "Данные НКО АО НРД, отчётность по Указанию Банка России № 4104-У.",
                **raw.reference(),
            }
    if len(seen) != len(INSTRUMENTS) * len(PARTICIPANTS):
        raise SourceError("Missing instruments or segments in the derivatives review")
