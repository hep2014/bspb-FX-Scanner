from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

import httpx
import openpyxl
import pytest

from data_pipeline.core import Raw, Run, SourceError, digest
from data_pipeline.sources.cbr import spot_rows
from data_pipeline.sources.contracts import annotation_template, candidate_spans, document, review_label
from data_pipeline.sources.economics import forward_turnover, trade_period
from data_pipeline.sources.moex import observations
from data_pipeline.validation.checks import validate

ROOT = Path(__file__).resolve().parents[1]


def raw(path: Path, key: str, source_id: str) -> Raw:
    return Raw(key, source_id, "https://example.test/data", path, digest(path), path.stat().st_size,
               "2026-11-13T12:00:00+03:00", "test")


@pytest.fixture
def run(tmp_path):
    shutil.copytree(ROOT / "configs", tmp_path / "configs")
    item = Run(tmp_path)
    try:
        yield item
    finally:
        item.close()


def test_cbr_fx_nominal_and_dates(tmp_path):
    path = tmp_path / "cbr.xml"
    path.write_text(
        '<ValCurs ID="R01375"><Record Id="R01375" Date="10.01.2019"><Nominal>10</Nominal>'
        '<Value>98,1498</Value><VunitRate>9,81498</VunitRate></Record>'
        '<Record Id="R01375" Date="12.01.2019"><Nominal>1</Nominal>'
        '<Value>9,9000</Value><VunitRate>9,9000</VunitRate></Record></ValCurs>',
        encoding="utf-8",
    )
    rows = list(spot_rows(raw(path, "CNY", "cbr_fx"), "CNY", "R01375", "156"))
    assert [row["date"] for row in rows] == [date(2019, 1, 10), date(2019, 1, 12)]
    assert [row["nominal"] for row in rows] == [10, 1]
    assert rows[0]["rub_per_unit"] == pytest.approx(9.81498)
    assert rows[0]["publication_date"] is None


def test_cbr_incorrect_instrument_is_rejected(tmp_path):
    path = tmp_path / "cbr.xml"
    path.write_text('<ValCurs ID="R01235"/>', encoding="utf-8")
    with pytest.raises(SourceError, match="Wrong CBR XML instrument"):
        list(spot_rows(raw(path, "CNY", "cbr_fx"), "CNY", "R01375", "156"))


def test_raw_import_is_idempotent_and_detects_tampering(run, tmp_path):
    path = tmp_path / "input.xml"
    path.write_text('<ValCurs ID="R01235"/>')
    source = "https://example.test/fx"
    first = run.import_raw("cbr_fx", "USD", source, path)
    assert run.import_raw("cbr_fx", "USD", source, path) == first
    assert len(run.downloads) == 1
    first.path.write_text("changed")
    with pytest.raises(SourceError, match="SHA-256 has changed"):
        run.raw("cbr_fx", "USD")
    assert validate(run) == 1


def test_http_retries_and_preserves_response(tmp_path, run, monkeypatch):
    responses = iter((429, 200))
    monkeypatch.setattr("data_pipeline.core.time.sleep", lambda *_: None)
    request_count = 0

    def server(request):
        nonlocal request_count
        request_count += 1
        return httpx.Response(next(responses), content=b'{"data":[1]}', headers={"Retry-After": "0"})

    run.http.close()
    run.http = httpx.Client(transport=httpx.MockTransport(server))
    url = "https://example.test/dataset"
    result = run.fetch("moex", "history", url, ".json")
    assert result.path.read_bytes() == b'{"data":[1]}'
    assert run.fetch("moex", "history", url, ".json").sha256 == result.sha256
    assert request_count == 2


def test_moex_expiration_and_no_trade_quotes(tmp_path):
    file = tmp_path / "iss.json"
    file.write_text(json.dumps({"history": {"columns": [
        "TRADEDATE", "OPEN", "HIGH", "LOW", "CLOSE", "SETTLEPRICE", "NUMTRADES"
    ], "data": [["2020-03-19", 0, 0, 0, 0, 86000, 0], ["2020-03-20", None, None, None, None, 86390, 0]]}}))
    spec = dict(secid="SiH0", instrument_name="Si", underlying="USD/RUB", contract_type="dated_future",
                expiration_date=date(2020, 3, 19), settlement_type="cash", currency="USD",
                price_unit="RUB per lot", board="RFUD")
    rows = list(observations(raw(file, "history_SiH0_RFUD_0", "moex"), spec))
    assert rows[0]["close"] is None and rows[0]["settlement_price"] == 86000
    assert rows[0]["quality_flag"] == "no_trades_zero_price"
    assert rows[1]["quality_flag"] == "post_expiration_settlement_only"
    assert not rows[1]["usable_for_backtest"]


def test_moex_spot_restriction_keeps_observation_but_excludes_backtest(tmp_path):
    file = tmp_path / "iss.json"
    file.write_text(json.dumps({"history": {"columns": ["TRADEDATE", "OPEN", "CLOSE", "NUMTRADES"],
                                            "data": [["2026-10-01", 81, 82, 3]]}}))
    spec = dict(secid="USD000UTSTOM", instrument_name="USD", underlying="USD/RUB", contract_type="spot",
                expiration_date=None, settlement_type="TOM", currency="USD", price_unit="RUB per USD",
                board="CETS")
    row, = observations(raw(file, "history_USD000UTSTOM_CETS_0", "moex"), spec,
                        date(2024, 6, 13), ("USD", "EUR"))
    assert row["traded"] and row["close"] == 82
    assert not row["usable_for_backtest"]
    assert row["quality_flag"] == "exchange_spot_restriction"


def test_contract_candidate_offsets_are_unreviewed(tmp_path):
    file = tmp_path / "contract.txt"
    text = "Payment currency is USD. Contact review@example.test for details."
    file.write_text(text)
    row = document(raw(file, "sample", "cuad"), "sample", text, "agreement", "https://example.test/1",
                   None, "txt", "test", "cc-by-4.0", "automated_pii_scan_only")
    assert "review@example.test" not in row["text"]
    assert len(row["text"]) == len(text)
    hit = next(candidate_spans(row, 20))
    assert row["text"][hit["start"]:hit["end"]] == "Payment currency"
    task = annotation_template(row, hit)
    assert task["exposure_exists"] is None
    assert task["reviewer_status"] == "unreviewed"
    assert task["proposed_span"] == [hit["start"], hit["end"]]


def test_reviewed_example_is_pinned_to_text(tmp_path):
    row = {"document_id": "a", "text_hash": hashlib.sha256(b"aaa").hexdigest(),
           "text": "aaa", "source_id": "cuad", "source_sha256": "source"}
    note = {"text_hash": row["text_hash"], "reviewed_label": "confirmed_fx", "start": "0", "end": "2",
            "review_note": "checked manually"}
    assert review_label(row, note)["evidence"] == "aa"
    with pytest.raises(SourceError, match="document changed"):
        review_label(row, {**note, "text_hash": "other"})


def test_monthly_turnover_keeps_currency_sections_separate(tmp_path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "ALL_TOTAL"
    sheet.append(["Все валюты"])
    sheet.append(["январь", 100])
    sheet.append(["Российский рубль"])
    sheet.append(["январь", 75])
    file = tmp_path / "turnover.xlsx"
    workbook.save(file)
    rows = list(forward_turnover(raw(file, "forward_2022", "cbr_derivatives"), workbook))
    assert [(x["currency_pair"], x["value"], x["unit"]) for x in rows] == [
        ("ALL", 100, "usd_mn_per_day"), ("RUB", 75, "usd_mn_per_day")
    ]


@pytest.mark.parametrize(("raw_period", "frequency", "expected"), [
    ("фев.20", "month", date(2020, 2, 29)),
    ("2 квартал\n2026", "quarter", date(2026, 6, 30)),
    ("2025", "year", date(2025, 12, 31)),
])
def test_trade_period_end(raw_period, frequency, expected):
    assert trade_period(raw_period, frequency)[1] == expected
