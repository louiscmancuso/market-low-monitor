"""Publish public SEC research or run a price screen for private personal use."""
import argparse
import concurrent.futures
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import exchange_calendars as xc
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
SEC = "https://data.sec.gov"
TICKERS = "https://www.sec.gov/files/company_tickers.json"
SP = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NDX = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
WIKI = "https://en.wikipedia.org/w/rest.php/v1/page/"
PROJECT = "https://github.com/louiscmancuso/market-low-monitor"
UA = "MarketLowMonitor/1.0 (" + os.getenv("SEC_CONTACT", PROJECT) + ")"
lock = threading.Lock()
last_request = 0.0


def fetch(url, headers=None, html=False, min_interval=.22):
    global last_request
    for attempt in range(3):
        with lock:
            time.sleep(max(0, min_interval - (time.monotonic() - last_request)))
            last_request = time.monotonic()
        try:
            with urlopen(Request(url, headers={"User-Agent": UA, **(headers or {})}),
                         timeout=20) as response:
                return response.read() if html else json.load(response)
        except OSError as error:
            status = getattr(error, "code", None)
            if attempt == 2 or status in {400, 401, 403, 404, 422}:
                raise RuntimeError(f"Source request failed for {url.split('?')[0]} (HTTP {status or 'unavailable'})") from None
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def parallel(fn, values):
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(fn, values))


def roster_page(source, index):
    # Prefer the Wikimedia REST endpoint. The article URL is a compatibility fallback.
    page = source.rsplit("/", 1)[1]
    try:
        body = fetch(WIKI + page + "/html", html=True)
    except RuntimeError:
        body = fetch(source, html=True)
    matches = []
    for table in BeautifulSoup(body, "html.parser").find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        columns = [re.sub(r"\s+", " ", x.get_text(" ", strip=True)).lower()
                   for x in rows[0].find_all(["th", "td"])]
        symbol = next((x for x in ("symbol", "ticker") if x in columns), None)
        name = next((x for x in ("security", "company", "company name") if x in columns), None)
        if not symbol or not name:
            continue
        result = {}
        for row in rows[1:]:
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) != len(columns):
                continue
            for cell in cells:
                for note in cell.select("sup"):
                    note.decompose()
            record = dict(zip(columns, (cell.get_text(" ", strip=True) for cell in cells)))
            ticker = record[symbol].upper().replace(".", "-")
            if re.fullmatch(r"[A-Z][A-Z0-9-]{0,9}", ticker) and record[name]:
                result[ticker] = {"ticker": ticker, "name": record[name], "indexes": [index],
                                  "sector": record.get("gics sector") or record.get("sector") or "",
                                  "industry": record.get("gics sub-industry") or record.get("industry") or "",
                                  "cik": re.sub(r"[^0-9]", "", record.get("cik", ""))}
        if result:
            matches.append(result)
    candidates = [group for group in matches if (495 <= len(group) <= 510 if index == "S&P 500" else 99 <= len(group) <= 106)]
    if len(candidates) != 1:
        raise ValueError(f"Unexpected {index} membership table sizes: {[len(group) for group in matches]}")
    return candidates[0]


def universe(lookup_ciks=True):
    sp, ndx = parallel(lambda args: roster_page(*args), [(SP, "S&P 500"), (NDX, "Nasdaq-100")])
    for ticker, item in ndx.items():
        if ticker in sp:
            sp[ticker]["indexes"] += item["indexes"]
        else:
            sp[ticker] = item
    if not lookup_ciks:
        return sp
    seed = json.loads((ROOT / "sec_ticker_seed.json").read_text())
    mapping = seed["tickers"].copy()
    try:
        mapping.update({item["ticker"].upper().replace(".", "-"): str(item["cik_str"])
                        for item in fetch(TICKERS).values()})
    except RuntimeError as error:
        print(f"{error}. Using the SEC ticker snapshot observed {seed['observed']} for Nasdaq-100 identifiers.", file=sys.stderr)
    for row in sp.values():
        row["cik"] = (row["cik"] or mapping.get(row["ticker"], "")).lstrip("0")
    if sum(not row["cik"] for row in sp.values()) > 5:
        raise ValueError("Unexpected number of missing SEC company identifiers")
    return sp


def session_info(date=None, now=None, latest=False):
    now = now or dt.datetime.now(ET)
    cal = xc.get_calendar("XNYS")
    date = date or now.date().isoformat()
    if latest:
        date = cal.date_to_session(date, direction="previous").date().isoformat()
        if now < cal.session_close(date):
            date = cal.previous_session(date).date().isoformat()
    if not cal.is_session(date):
        return None
    if now < cal.session_close(date):
        raise ValueError(f"Regular session {date} has not closed")
    return cal, date


def filings(cik, session):
    if not cik:
        return []
    payload = fetch(f"{SEC}/submissions/CIK{int(cik):010d}.json")
    recent = payload["filings"]["recent"]
    cutoff = (dt.date.fromisoformat(session) - dt.timedelta(days=14)).isoformat()
    result = []
    for form, filed, accession, document, items in zip(
            recent["form"], recent["filingDate"], recent["accessionNumber"],
            recent["primaryDocument"], recent["items"], strict=True):
        if cutoff <= filed <= session and form in {"8-K", "10-K", "10-Q", "6-K", "20-F", "40-F"}:
            result.append({"form": form, "filed": filed, "items": items,
                           "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"})
    return result[:6]


METRICS = {
    "Revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "Net income": ("NetIncomeLoss", "ProfitLoss"),
    "Operating income": ("OperatingIncomeLoss",),
    "Operating cash flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "Noncurrent debt": ("LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"),
    "Cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "Current assets": ("AssetsCurrent",),
    "Current liabilities": ("LiabilitiesCurrent",),
}


def pair(facts, tags, session, instant=False):
    for tag in tags:
        periods = {}
        for fact in facts.get(tag, {}).get("units", {}).get("USD", []):
            if fact["form"] not in {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"} or fact["filed"] > session:
                continue
            end = dt.date.fromisoformat(fact["end"])
            if instant:
                if fact.get("start"):
                    continue
            elif not fact.get("start") or not 350 <= (end - dt.date.fromisoformat(fact["start"])).days <= 380:
                continue
            prior = periods.get(fact["end"])
            if not prior or (fact["filed"], fact["accn"]) > (prior["filed"], prior["accn"]):
                periods[fact["end"]] = fact
        dates = sorted(periods, reverse=True)
        if len(dates) > 1 and 350 <= (dt.date.fromisoformat(dates[0]) - dt.date.fromisoformat(dates[1])).days <= 380:
            a, b = (periods[x] for x in dates[:2])
            if (dt.date.fromisoformat(session) - dt.date.fromisoformat(a["end"])).days > 550:
                continue
            return {"value": a["val"], "prior": b["val"], "end": a["end"], "prior_end": b["end"],
                    "filed": a["filed"], "tag": tag,
                    "change": round((a["val"] / b["val"] - 1) * 100, 2) if b["val"] > 0 else None}
    return None


def research(cik, session):
    if not cik:
        return {}
    raw = fetch(f"{SEC}/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
    facts = raw["facts"].get("us-gaap", {})
    metrics = {}
    for name, tags in METRICS.items():
        result = pair(facts, tags, session, name in {"Noncurrent debt", "Cash", "Current assets", "Current liabilities"})
        if result:
            metrics[name] = result
    for label, numerator, denominator, scale in (
            ("Operating margin", "Operating income", "Revenue", 100),
            ("Current ratio", "Current assets", "Current liabilities", 1)):
        a, b = metrics.get(numerator), metrics.get(denominator)
        if a and b and (a["end"], a["prior_end"]) == (b["end"], b["prior_end"]) and min(b["value"], b["prior"]) > 0:
            metrics[label] = {"value": round(a["value"] / b["value"] * scale, 2),
                              "prior": round(a["prior"] / b["prior"] * scale, 2),
                              "end": a["end"], "prior_end": a["prior_end"], "change": None}
    signals = []
    for name in ("Revenue", "Net income", "Operating margin", "Operating cash flow", "Cash", "Noncurrent debt", "Current ratio"):
        item = metrics.get(name)
        if item and item["value"] != item["prior"]:
            signals.append(f"{name} {'increased' if item['value'] > item['prior'] else 'decreased'} versus the prior fiscal year.")
    core = [metrics.get(name) for name in ("Revenue", "Net income", "Operating cash flow")]
    priority = "Insufficient Information"
    score = None
    if all(core) and len({(m["end"], m["prior_end"]) for m in core}) == 1:
        revenue, income, cashflow = core
        score = sum([revenue["value"] > revenue["prior"], income["value"] > 0,
                     cashflow["value"] > 0, cashflow["value"] >= cashflow["prior"]])
        priority = "High" if score >= 3 and min(income["value"], cashflow["value"]) > 0 else "Low" if score <= 1 or cashflow["value"] < 0 else "Medium"
    outlook = ["Check the next earnings release for current demand, margins and management guidance."]
    if metrics.get("Operating cash flow", {}).get("value", 1) < 0:
        signals.append("Latest fiscal-year operating cash flow was negative.")
        outlook.append("Watch whether operating cash flow recovers and how management funds operations.")
    if metrics.get("Noncurrent debt", {}).get("change") and metrics["Noncurrent debt"]["change"] > 0:
        outlook.append("Review debt maturities, interest expense and refinancing terms in the next filing.")
    return {"metrics": metrics, "observations": signals, "outlook": outlook,
            "priority": priority, "score": score, "updated": max((x.get("filed", "") for x in metrics.values()), default="")}


def report_row(item, session, prices=None):
    row = {**item, **(prices or {}), "priority": "Insufficient Information"}
    cik = item["cik"]
    row["filings"] = filings(cik, session)
    return row


def enrich(row, session):
    row.update(research(row["cik"], session))
    return row


def prices_from_bars(bars, calendar, session):
    target = dt.date.fromisoformat(session)
    by_date = {}
    for bar in bars:
        date = dt.datetime.fromisoformat(bar["t"]).astimezone(ET).date()
        if date > target or not calendar.is_session(date.isoformat()) or date in by_date:
            raise ValueError("Unexpected or duplicate trading-session bar")
        close, low, high = (float(bar[key]) for key in ("c", "l", "h"))
        if not all(math.isfinite(x) for x in (close, low, high)) or not 0 < low <= close <= high:
            raise ValueError("Invalid daily prices")
        by_date[date] = (close, low, high)
    if target not in by_date:
        raise ValueError("Missing current regular-session bar")
    dates = sorted(by_date)
    window_start = target - dt.timedelta(weeks=52)
    expected = calendar.sessions_in_range(window_start.isoformat(), session)
    if any(day.date() not in by_date for day in expected if day.date() >= dates[0]):
        raise ValueError("Missing bars within the available 52-week window")
    window = [day for day in dates if day >= window_start]
    close, day_low, _ = by_date[target]
    low_day = min(window, key=lambda day: (by_date[day][1], day))
    low = by_date[low_day][1]
    high = max(by_date[day][2] for day in window)
    dollars = close - low
    percent = dollars / low * 100
    dollar_test = dollars <= 10 + 1e-9
    percent_test = percent <= 10 + 1e-9
    returns = {}
    for label, offset in (("1D", 1), ("5D", 5), ("1M", 21), ("3M", 63), ("6M", 126), ("1Y", 252)):
        if len(dates) > offset:
            base = dates[-1 - offset]
            if base.isoformat() == calendar.session_offset(session, -offset).date().isoformat():
                returns[label] = round((close / by_date[base][0] - 1) * 100, 2)
    return {"close": close, "low": low, "high": high, "lowDate": low_day.isoformat(),
            "dollars": round(dollars, 4), "percent": round(percent, 4), "dollarTest": dollar_test,
            "percentTest": percent_test, "qualified": dollar_test or percent_test,
            "fresh": len(window) > 1 and day_low < min(by_date[x][1] for x in window[:-1]),
            "shortHistory": dates[0] > expected[0].date(),
            "returns": returns, "series": [[day.isoformat(), by_date[day][0]] for day in window[::5] if day != target] + [[session, close]]}


def alpaca_prices(universe_rows, cal, session):
    key, secret = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise ValueError("Private Alpaca data credentials are missing")
    start = (dt.date.fromisoformat(session) - dt.timedelta(days=410)).isoformat()
    symbols = sorted(universe_rows)
    output = {}
    for start_index in range(0, len(symbols), 70):
        group = symbols[start_index:start_index + 70]
        vendor_names = {ticker.replace("-", "."): ticker for ticker in group}
        params = {"symbols": ",".join(vendor_names), "start": start, "end": cal.session_close(session).isoformat(),
                  "timeframe": "1Day", "feed": "sip", "adjustment": "split", "limit": 10000}
        bars = {vendor: [] for vendor in vendor_names}
        seen_tokens = set()
        while True:
            data = fetch("https://data.alpaca.markets/v2/stocks/bars?" + urlencode(params),
                         {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
            for symbol, points in (data["bars"] or {}).items():
                bars[symbol].extend(points)
            token = data.get("next_page_token")
            if not token:
                break
            if token in seen_tokens:
                raise ValueError("Price API repeated a pagination token")
            seen_tokens.add(token)
            params["page_token"] = token
        errors = []
        for vendor, ticker in vendor_names.items():
            try:
                output[ticker] = prices_from_bars(bars[vendor], cal, session)
            except ValueError as error:
                errors.append(f"{ticker}: {error}")
        if errors:
            raise ValueError("Price coverage incomplete: " + "; ".join(errors))
    return output


def massive_prices(members, calendar, session, key):
    """Request one split-adjusted daily summary per session on Stocks Basic."""
    start = dt.date.fromisoformat(session) - dt.timedelta(days=400)
    sessions = calendar.sessions_in_range(start.isoformat(), session)
    history = {ticker: [] for ticker in members}
    symbols = {ticker.replace("-", "."): ticker for ticker in members}
    print(f"Fetching {len(sessions)} trading sessions at up to 5 requests per minute.", flush=True)
    for index, day in enumerate(reversed(sessions), start=1):
        date = day.date().isoformat()
        data = fetch(f"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{date}?adjusted=true",
                     {"Authorization": f"Bearer {key}"}, min_interval=12.2)
        if data.get("status") != "OK" or data.get("adjusted") is not True or not data.get("results"):
            raise ValueError(f"Missing or invalid Massive daily summary for {date}")
        for bar in data["results"]:
            ticker = symbols.get(bar["T"])
            if ticker:
                timestamp = dt.datetime.fromtimestamp(bar["t"] / 1000, ET)
                if timestamp.date() != day.date():
                    raise ValueError(f"Massive returned an unexpected date for {ticker}: {date}")
                history[ticker].append({**bar, "t": timestamp.isoformat()})
        if index == 1:
            missing = [ticker for ticker, bars in history.items() if not bars]
            if missing:
                raise ValueError("Missing latest Massive bars: " + ", ".join(sorted(missing)))
        if index % 25 == 0 or index == len(sessions):
            print(f"Fetched {index}/{len(sessions)} sessions.", flush=True)
    results = {}
    for ticker, bars in history.items():
        try:
            results[ticker] = prices_from_bars(bars, calendar, session)
        except ValueError as error:
            raise ValueError(f"{ticker}: {error}") from None
    return results


def write_json(path, content):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    temporary.replace(path)


def archive(folder, report, calendar):
    folder.mkdir(parents=True, exist_ok=True)
    day = report["date"]
    previous = folder / f"{calendar.previous_session(day).date().isoformat()}.json"
    prior = json.loads(previous.read_text()) if previous.exists() else None
    old = {row["ticker"]: row for row in prior["rows"]} if prior else {}
    new = []
    changed = []
    for row in report["rows"]:
        before = old.get(row["ticker"])
        row["new"] = bool(before and row.get("qualified") and not before.get("qualified"))
        if prior and {(item["filed"], item["url"]) for item in row["filings"]} - {
            (item["filed"], item["url"]) for item in (before or {}).get("filings", [])
        }:
            changed.append(row["ticker"])
        if row["new"]:
            new.append(row["ticker"])
    current = {row["ticker"] for row in report["rows"] if row.get("qualified")}
    tracked = {row["ticker"] for row in report["rows"]}
    report.update({"comparable": bool(prior), "new": new, "researchChanges": changed,
                   "exited": sorted(ticker for ticker, row in old.items() if row.get("qualified") and ticker in tracked - current),
                   "removed": sorted(old.keys() - tracked)})
    write_json(folder / f"{day}.json", report)
    write_json(folder / "index.json", sorted((x.stem for x in folder.glob("????-??-??.json")), reverse=True))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=["public", "private"])
    cli.add_argument("--latest", action="store_true", help="Use the latest closed session with the roster observed today")
    cli.add_argument("--prices-only", action="store_true", help="Run a private price scan without SEC research")
    cli.add_argument("--provider", choices=["alpaca", "massive"], help="Price provider for private mode")
    args = cli.parse_args()
    if args.provider and args.mode != "private":
        cli.error("--provider requires private mode")
    if args.prices_only and args.mode != "private":
        cli.error("--prices-only requires private mode")
    key = None
    if args.provider == "massive":
        key = os.getenv("MASSIVE_API_KEY")
        if not key:
            raise ValueError("Set MASSIVE_API_KEY locally before running the private scan.")
        now = dt.datetime.now(ET)
        yesterday = (now.date() - dt.timedelta(days=1)).isoformat()
        session = session_info(date=yesterday, now=now, latest=True)
    else:
        session = session_info(latest=args.latest)
    if session is None:
        print("No regular US trading session today")
        return
    calendar, date = session
    directory = ROOT / ("site/data" if args.mode == "public" else ".private/data")
    existing = directory / f"{date}.json"
    if existing.exists() and (args.prices_only or not json.loads(existing.read_text()).get("pricesOnly")):
        write_json(directory / "index.json", sorted((x.stem for x in directory.glob("????-??-??.json")), reverse=True))
        print(f"Verified {args.mode} report already exists for {date}")
        return
    members = universe(lookup_ciks=not args.prices_only)
    if args.mode == "private":
        if args.provider == "massive":
            data = massive_prices(members, calendar, date, key)
        else:
            if os.getenv("APCA_PERSONAL_USE") != "yes":
                raise ValueError("Confirm the Alpaca feed entitlement and regular-session conventions before enabling private prices. See SETUP.md.")
            data = alpaca_prices(members, calendar, date)
        rows = parallel(lambda item: report_row(item, date, data[item["ticker"]]) if not args.prices_only and data[item["ticker"]]["qualified"]
                        else {**item, **data[item["ticker"]], "filings": []}, members.values())
        if not args.prices_only:
            parallel(lambda row: enrich(row, date), [row for row in rows if row["qualified"]])
        for row in rows:
            if not row["qualified"]:
                row["series"] = []
    else:
        rows = parallel(lambda item: report_row(item, date), members.values())
        recent = sorted((row for row in rows if row["filings"] and row["cik"]),
                        key=lambda row: (row["filings"][0]["filed"], row["ticker"]), reverse=True)
        # Keep public collection lightweight. Cover recent periodic filings first.
        recent.sort(key=lambda row: not any(f["form"] in {"10-K", "10-Q", "20-F", "40-F"} for f in row["filings"]))
        parallel(lambda row: enrich(row, date), recent[:15])
    archive(directory, {"date": date, "mode": args.mode, "updated": dt.datetime.now(ET).isoformat(),
                        "rows": rows, "pricesOnly": args.prices_only,
                        "priceProvider": (args.provider or "alpaca") if args.mode == "private" else None, "rosterObserved": dt.datetime.now(ET).date().isoformat(), "spCount": sum("S&P 500" in x["indexes"] for x in rows),
                        "ndxCount": sum("Nasdaq-100" in x["indexes"] for x in rows)}, calendar)
    print(f"Verified {args.mode} report for {date}: {len(rows)} securities")
    if args.mode == "private":
        qualifying = sorted((row for row in rows if row["qualified"]), key=lambda row: (row["percent"], row["ticker"]))
        print(f"{len(qualifying)} stocks qualified.")
        for row in qualifying[:10]:
            print(f"{row['ticker']:6}  close ${row['close']:,.2f}  low ${row['low']:,.2f}  "
                  f"${row['dollars']:,.2f} / {row['percent']:.2f}% above low")
        print(f"Full report: {directory / (date + '.json')}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError) as error:
        sys.exit(str(error))
