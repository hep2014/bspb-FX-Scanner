from __future__ import annotations

import re
from datetime import date
from urllib.parse import quote, urlencode

from data_pipeline.core import Run, Raw, SourceError, read_json


def endpoint(run: Run, path: str, **parameters) -> str:
    query = {"iss.meta": "off", **parameters}
    return f"{run.sources['moex']['endpoint']}/{path}.json?{urlencode(query)}"


def block(raw: Raw, name: str) -> list[dict]:
    payload = read_json(raw.path, {})
    if not isinstance(payload, dict) or name not in payload:
        raise SourceError(f"MOEX response is missing {name}: {raw.key}")
    return [dict(zip(map(str.upper, payload[name]["columns"]), row, strict=True))
            for row in payload[name]["data"]]


def history_url(run: Run, spec: dict, start: int, candles: bool = False) -> str:
    market = f"engines/{spec['engine']}/markets/{spec['market']}/boards/{spec['board']}"
    name = f"{market}/securities/{quote(spec['secid'], safe='')}"
    if candles:
        return endpoint(run, f"{name}/candles", **{
            "from": run.start.isoformat(), "till": run.end.isoformat(), "start": start,
            "interval": 24, "iss.only": "candles",
        })
    return endpoint(run, f"history/{name}", **{
        "from": run.start.isoformat(), "till": run.end.isoformat(), "start": start,
        "iss.only": "history,history.cursor",
    })


def search_url(run: Run, query: str, start: int = 0) -> str:
    return endpoint(run, "securities", q=query, start=start, **{"iss.only": "securities"})


def detail_url(run: Run, secid: str) -> str:
    return endpoint(run, f"securities/{quote(secid, safe='')}",
                    **{"iss.only": "description,boards"})


def derivatives_board_url(run: Run) -> str:
    return endpoint(run, "engines/futures/markets/forts/boards/RFUD/securities",
                    **{"iss.only": "securities,marketdata"})


def iso_date(value) -> date | None:
    return date.fromisoformat(str(value)[:10]) if value and str(value) != "0000-00-00" else None


def pick(row: dict, *names):
    return next((row[n] for n in names if row.get(n) not in (None, "")), None)


def listing(run: Run):
    config = run.settings["moex"]
    for symbol, (currency, settlement) in config["spot"].items():
        yield symbol, currency, "spot", settlement
    for symbol, currency in config["perpetual"].items():
        yield symbol, currency, "perpetual_future", None
    for symbol, currency in config["expiring"].items():
        yield symbol, currency, "dated_future", None


def selected(candidate: dict, query: str, kind: str) -> bool:
    secid = str(candidate["SECID"])
    if kind == "dated_future":
        return re.fullmatch(re.escape(query) + r"[FGHJKMNQUVXZ]\d{1,2}", secid, re.I) is not None
    return secid.upper() == query.upper()


def spec_rows(raw: Raw, run: Run):
    candidates = block(raw, "boards")
    description = {str(row.get("NAME", "")).upper(): row.get("VALUE")
                   for row in block(raw, "description")}
    secid = raw.key.removeprefix("detail_")
    matched = next(((currency, kind, settlement) for query, currency, kind, settlement in listing(run)
                    if selected({"SECID": secid}, query, kind)), None)
    if matched is None:
        return
    currency, kind, settlement = matched
    for b in candidates:
        engine = str(b.get("ENGINE", ""))
        market = str(b.get("MARKET", ""))
        board = str(b.get("BOARDID", ""))
        if (engine, market) != (("currency", "selt") if kind == "spot" else ("futures", "forts")):
            continue
        if board not in ({"CETS"} if kind == "spot" else {"RFUD"}):
            continue
        end = iso_date(pick(b, "HISTORY_TILL", "LISTED_TILL"))
        start = iso_date(pick(b, "HISTORY_FROM", "LISTED_FROM"))
        if (end and end < run.start) or (start and start > run.end):
            continue
        expiry = pick(description, "LSTDELDATE", "EXPIRATIONDATE", "LASTTRADEDATE")
        if kind != "dated_future":
            expiry = None
        price_unit = pick(description, "UNIT", "QUOTATION", "PRICEUNIT")
        if price_unit is None and kind == "spot" and description.get("FACEVALUE"):
            price_unit = f"RUB per {description['FACEVALUE']} {currency}"
        yield {
            "secid": secid, "instrument_name": pick(description, "NAME", "SHORTNAME"),
            "underlying": f"{currency}/RUB", "contract_type": kind,
            "expiration_date": iso_date(expiry),
            "settlement_type": settlement or pick(description, "EXECTYPE", "SETTLETYPE", "SETTLEMENTTYPE"),
            "currency": currency, "quote_currency": pick(b, "CURRENCYID") or "RUB",
            "price_unit": price_unit, "contract_size": pick(description, "LOTSIZE", "LOTVOLUME"),
            "price_tick": pick(description, "MINSTEP", "MINSTEPVAL"),
            "settlement_rule": pick(description, "DELIVERYTYPE", "SETTLEMENTPROCEDURE"),
            "initial_margin_long": pick(description, "BUYDEPO"),
            "initial_margin_short": pick(description, "SELLDEPO"),
            "margin_as_of": None, "history_from": start, "history_till": end,
            "listed_from": iso_date(pick(description, "FRSTTRADE") or pick(b, "LISTED_FROM")),
            "last_trade_date": iso_date(pick(description, "LSTTRADE") or pick(b, "LISTED_TILL")),
            "engine": engine, "market": market, "board": board, **raw.reference(),
        }


def collect(run: Run) -> str:
    discovered = set()
    failures = []
    total_history = 0
    total_specs = 0
    for query, _, kind, _ in listing(run):
        if kind == "dated_future":
            # Probe quarterly codes using the exchange naming convention. A series
            # enters the catalog only if ISS confirms its metadata and period.
            months = [x.strip() for x in run.settings["moex"]["quarterly_month_codes"].split(",")]
            discovered.update(f"{query}{month}{year % 10}" for year in range(run.start.year, run.end.year + 2)
                              for month in months)
            continue
        try:
            for offset in range(0, 2000, 100):
                raw = run.fetch("moex", f"search_{query}_{offset}", search_url(run, query, offset), ".json")
                matches = block(raw, "securities")
                if not matches:
                    break
                for row in matches:
                    if selected(row, query, kind):
                        discovered.add(str(row["SECID"]))
                # SECID search is normally capped at 100 results per page.
                if len(matches) < 100:
                    break
            else:
                failures.append(f"Search page bound reached for {query}")
        except SourceError as exc:
            if not discovered:
                raise
            failures.append(f"{query}: {exc}")
    if not discovered:
        raise SourceError("No configured instruments were confirmed by ISS")
    try:
        run.fetch("moex", "rfud_board", derivatives_board_url(run), ".json")
    except SourceError as exc:
        failures.append(f"RFUD snapshot: {exc}")
    for secid in sorted(discovered):
        try:
            info = run.fetch("moex", f"detail_{secid}", detail_url(run, secid), ".json")
            for spec in spec_rows(info, run):
                total_specs += 1
                mode = "history"
                for index in range(int(run.settings["moex"]["history_page_limit"])):
                    start = 0 if index == 0 else next_offset
                    try:
                        raw = run.fetch("moex", f"{mode}_{secid}_{spec['board']}_{start}",
                                        history_url(run, spec, start, mode == "candles"), ".json")
                        rows = block(raw, mode)
                        if index == 0 and not rows and mode == "history":
                            raise SourceError("ISS history returned no rows")
                    except SourceError as exc:
                        if index or mode != "history":
                            raise
                        failures.append(f"{secid}: {exc}; checking daily candles")
                        mode = "candles"
                        raw = run.fetch("moex", f"{mode}_{secid}_{spec['board']}_0",
                                        history_url(run, spec, 0, True), ".json")
                        rows = block(raw, mode)
                    if not rows:
                        break
                    total_history += len(rows)
                    next_offset = start + len(rows)
                    if mode == "history":
                        payload = read_json(raw.path, {})
                        if "history.cursor" in payload:
                            cursor = block(raw, "history.cursor")
                            if cursor and next_offset >= int(cursor[0]["TOTAL"]):
                                break
                else:
                    failures.append(f"{secid}: pagination limit reached")
        except SourceError as exc:
            failures.append(f"{secid}: {exc}")
    if total_specs == 0:
        failures.append("No instruments with a confirmed CETS or RFUD board and eligible dates")
    if total_history == 0:
        failures.append("No eligible public daily trading rows")
    return " | ".join(failures)


def observations(raw: Raw, spec: dict, restriction_date: date | None = None,
                 restricted_currencies: tuple[str, ...] = ()):
    mode = raw.key.split("_", 1)[0]
    for row in block(raw, mode):
        dt = iso_date(pick(row, "TRADEDATE", "BEGIN"))
        if dt is None:
            raise SourceError(f"Missing trade date for {raw.key}")
        trades = pick(row, "NUMTRADES")
        quotes = {k: pick(row, k.upper()) for k in ("open", "high", "low", "close")}
        zero_price = any(value is not None and value <= 0 for value in quotes.values())
        quotes = {key: value if value is None or value > 0 else None for key, value in quotes.items()}
        post_expiration = bool(spec["expiration_date"] and dt > spec["expiration_date"])
        flags = []
        if zero_price:
            flags.append("no_trades_zero_price" if trades == 0 else "nonpositive_source_price")
        if post_expiration and trades == 0 and pick(row, "SETTLEPRICE") is not None:
            flags.append("post_expiration_settlement_only")
        traded = bool(trades > 0) if trades is not None else all(v is not None for v in quotes.values())
        if spec["contract_type"] == "spot" and traded and not any(value is not None for value in quotes.values()):
            flags.append("spot_activity_without_prices")
            traded = False
        restriction_conflict = (spec["contract_type"] == "spot" and spec["board"] == "CETS"
                                and spec["currency"] in restricted_currencies and restriction_date is not None
                                and dt >= restriction_date)
        if restriction_conflict:
            flags.append("exchange_spot_restriction")
        usable = traded and not restriction_conflict and not post_expiration and not zero_price
        yield {
            "trade_date": dt, "secid": spec["secid"], "instrument_name": spec["instrument_name"],
            "underlying": spec["underlying"], "contract_type": spec["contract_type"],
            "expiration_date": spec["expiration_date"], "settlement_type": spec["settlement_type"],
            **quotes, "settlement_price": pick(row, "SETTLEPRICE"),
            "volume": pick(row, "VOLUME", "VOLTODAY"), "open_interest": pick(row, "OPENPOSITION", "OPENINTEREST"),
            "volume_unit": "contracts" if spec["contract_type"] != "spot" and mode == "history" else None,
            "num_trades": trades, "traded": traded, "usable_for_backtest": usable,
            "quality_flag": "|".join(flags) or None,
            "currency": spec["currency"], "price_unit": spec["price_unit"], "board": spec["board"],
            "history_kind": mode, **raw.reference(),
        }


def prepare(run: Run):
    inputs = run.raw("moex")
    specifications = [spec for raw in inputs if raw.key.startswith("detail_")
                      for spec in spec_rows(raw, run)]
    history = {}
    warnings = []
    restriction_date = iso_date(run.settings["moex"].get("spot_restriction_date"))
    restricted = tuple(run.settings["moex"].get("spot_restricted_currencies", ()))
    board_inputs = [raw for raw in inputs if raw.key == "rfud_board"]
    if board_inputs:
        board = board_inputs[-1]
        rows = {row["SECID"]: row for row in block(board, "securities")}
        live = {row["SECID"]: row for row in block(board, "marketdata")}
        for spec in specifications:
            current = rows.get(spec["secid"], {})
            data = live.get(spec["secid"], {})
            spec["price_tick"] = spec["price_tick"] or pick(current, "MINSTEP")
            spec["initial_margin_exchange"] = pick(current, "INITIALMARGIN")
            spec["initial_margin_long"] = spec["initial_margin_long"] or pick(current, "BUYDEPO")
            spec["initial_margin_short"] = spec["initial_margin_short"] or pick(current, "SELLDEPO")
            if any(spec.get(k) is not None for k in ("initial_margin_exchange", "initial_margin_long", "initial_margin_short")):
                spec["margin_as_of"] = pick(data, "TRADEDATE") or board.fetched_at[:10]
                spec["margin_source_sha256"] = board.sha256
    for spec in specifications:
        for mode in ("candles", "history"):
            prefix = f"{mode}_{spec['secid']}_{spec['board']}_"
            for raw in [item for item in inputs if item.key.startswith(prefix)]:
                for row in observations(raw, spec, restriction_date, restricted):
                    dt = row["trade_date"]
                    if run.start <= dt <= run.end:
                        k = (row["secid"], row["board"], dt)
                        if k in history and history[k]["history_kind"] == mode and history[k] != row:
                            warnings.append(f"Conflicting ISS observations for {k}")
                        history[k] = row
    if specifications:
        warnings.append("MOEX terms require a contract for commercial use or redistribution")
    if any(row["history_kind"] == "candles" for row in history.values()):
        warnings.append("Daily candle fallback omits settlement price and open interest where unpublished")
    if any(row["contract_type"] == "dated_future" and not row["expiration_date"] for row in specifications):
        warnings.append("Some dated futures lack explicit expiration metadata")
    futures = [row for row in history.values() if row["contract_type"] != "spot"]
    spot = [row for row in history.values() if row["contract_type"] == "spot"]
    return spot, futures, specifications, warnings
