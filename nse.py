"""NSE data: delivery %, bulk/block deals, results dates, fundamentals (XBRL), announcements and PDFs."""
import io
import json
import re
import pandas as pd
import numpy as np
import requests
from config import BIG_BUYER_CR, BIG_BUYER_DAYS, EARNINGS_GAP_PCT, MAX_DE, MAX_PDFS, MAX_PLEDGE, MAX_STAKE_DROP, PDF_CHARS
from db import connect


def _save_day(kind, d, df):
    """Replace one day's rows in table `kind` (delivery/deals) and mark the day fetched (also when empty: holiday)."""
    day = f"{d:%Y-%m-%d}"
    with connect() as c:
        c.execute(f"DELETE FROM {kind} WHERE date = ?", (day,))
        if len(df):
            cols = list(df.columns)
            c.executemany(f"INSERT OR REPLACE INTO {kind} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                          df.astype(object).where(df.notna(), None).itertuples(index=False, name=None))
        c.execute("INSERT OR IGNORE INTO fetched_days VALUES (?, ?)", (kind, day))


def _fetch_days(kind, days, fetch_one):
    """Fetch per-day data into table `kind`, skipping days already fetched.
    The last 2 days are always refetched (data may still be published late)."""
    from concurrent.futures import ThreadPoolExecutor
    recent = set(sorted(days)[-2:])
    blocked = []
    with connect() as c:
        done = {r[0] for r in c.execute("SELECT date FROM fetched_days WHERE kind = ?", (kind,))}
    todo = [d for d in days if d in recent or f"{d:%Y-%m-%d}" not in done]
    if todo:
        print(f"  fetching {kind} for {len(todo)} days...")

    def job(d):
        import time
        if blocked:  # NSE denied access: stop, missing days are retried on a later run
            return
        for attempt in range(4):  # NSE rate-limits bursts; back off and retry
            try:
                _save_day(kind, d, fetch_one(d))
                return
            except PermissionError:
                blocked.append(d)
                return
            except Exception as e:
                err = e
                time.sleep(2 * 2 ** attempt)
        if d not in recent:
            print(f"  [warn] {kind} {d:%Y-%m-%d}: {err}")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(job, todo))
    with connect() as c:
        if blocked:
            done = {r[0] for r in c.execute("SELECT date FROM fetched_days WHERE kind = ?", (kind,))}
            missing = sum(f"{d:%Y-%m-%d}" not in done for d in days)
            print(f"  [warn] NSE denied access to {kind} (403); {missing} days missing, will retry next run")
        return pd.read_sql(f"SELECT * FROM {kind} WHERE date >= ?", c, params=(f"{min(days):%Y-%m-%d}",))


def load_delivery(days):
    """Daily delivery % for every EQ stock, from NSE's full bhavcopy. Returns dates x symbols."""
    def one(d):
        r = _session().get(f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv",
                           timeout=30)
        if r.status_code == 404 or r.content[:2] == b"PK":  # holiday, or a one-off Excel file: cache as empty
            return pd.DataFrame(columns=["date", "symbol", "deliv_per"])
        r.raise_for_status()
        b = pd.read_csv(io.StringIO(r.text), skipinitialspace=True)
        b.columns = b.columns.str.strip()
        b = b[b["SERIES"].str.strip() == "EQ"]
        return pd.DataFrame({"date": f"{d:%Y-%m-%d}", "symbol": b["SYMBOL"].str.strip(),
                             "deliv_per": pd.to_numeric(b["DELIV_PER"], errors="coerce")})
    df = _fetch_days("delivery", days, one)
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index=pd.to_datetime(df["date"]), columns="symbol", values="deliv_per")


def load_deals(days):
    """Bulk + block deals per day (API returns at most 70 rows per call, so one call per day per kind)."""
    def one(d):
        rows = []
        for kind in ("bulk_deals", "block_deals"):
            r = _session().get("https://www.nseindia.com/api/historicalOR/bulk-block-short-deals",
                               params={"optionType": kind, "from": f"{d:%d-%m-%Y}", "to": f"{d:%d-%m-%Y}"},
                               timeout=30)
            if r.status_code == 403:
                raise PermissionError("403")
            j = r.json()
            rows += [{"date": f"{d:%Y-%m-%d}", "kind": kind, "symbol": x["BD_SYMBOL"], "client": x["BD_CLIENT_NAME"],
                      "side": x["BD_BUY_SELL"], "qty": x["BD_QTY_TRD"], "price": x["BD_TP_WATP"]}
                     for x in j.get("data", [])]
        return pd.DataFrame(rows, columns=["date", "kind", "symbol", "client", "side", "qty", "price"])
    return _fetch_days("deals", days, one)


def _is_result(x):
    return "financial result" in f"{x.get('desc', '')} {x.get('attchmntText', '')}".lower()


def load_results_dates(symbols, recent_days=10):
    """Datetimes of financial-results announcements per symbol. Full history is fetched once per stock;
    after that, one call for all companies over the last `recent_days` keeps it current."""
    from concurrent.futures import ThreadPoolExecutor
    with connect() as c:
        have = {r[0] for r in c.execute("SELECT symbol FROM results_fetched")}
        known = {}
        for sym, ts in c.execute("SELECT symbol, announced_at FROM results_dates"):
            known.setdefault(sym, []).append(ts)

    def full(sym):
        try:
            a = _session().get("https://www.nseindia.com/api/corporate-announcements",
                               params={"index": "equities", "symbol": sym}, timeout=30).json()
            return sym, sorted({x["an_dt"] for x in a if _is_result(x)})
        except Exception as e:
            print(f"  [warn] results dates {sym}: {e}")
            return sym, None

    out = {sym: sorted(known.get(sym, [])) if sym in have else None for sym in symbols}
    missing = [sym for sym, v in out.items() if v is None]
    if missing:
        print(f"  fetching results history for {len(missing)} stocks...")
        with ThreadPoolExecutor(3) as ex:
            for sym, dates in ex.map(full, missing):
                out[sym] = dates or []
    try:  # recent announcements for all companies in one call
        today = pd.Timestamp.now()
        a = _session().get("https://www.nseindia.com/api/corporate-announcements",
                           params={"index": "equities", "from_date": f"{today - pd.Timedelta(days=recent_days):%d-%m-%Y}",
                                   "to_date": f"{today:%d-%m-%Y}"}, timeout=30).json()
        for x in a:
            if x.get("symbol") in out and _is_result(x):
                out[x["symbol"]] = sorted(set(out[x["symbol"]]) | {x["an_dt"]})
    except Exception as e:
        print(f"  [warn] recent results announcements: {e}")
    with connect() as c:
        c.executemany("INSERT OR IGNORE INTO results_fetched VALUES (?)", [(s,) for s in out])
        c.executemany("INSERT OR IGNORE INTO results_dates VALUES (?, ?)", [(s, t) for s, ds in out.items() for t in ds])
    return out


def add_nse_signals(frames):
    """Add deliv_high / big_buyer filters and the earnings_gap setup from NSE history."""
    days = sorted({d for f in frames.values() for d in f.index})
    print("\nLoading NSE history (first run downloads ~5 years; later runs only new days)...")
    deliv = load_delivery(days)
    deals = load_deals(days)
    results = load_results_dates(list(frames))

    # big_buyer: clients that only bought a stock that day (filters out same-day HFT/arbitrage round trips)
    buys = pd.Series(dtype=float)
    if not deals.empty:
        deals["value"] = deals["qty"] * deals["price"]
        g = deals.groupby(["date", "symbol", "client"])
        per = pd.DataFrame({"buy": g.apply(lambda x: x.loc[x["side"] == "BUY", "value"].sum()),
                            "sold": g.apply(lambda x: (x["side"] == "SELL").any())})
        net = per[(per["buy"] > 0) & ~per["sold"]].groupby(level=["date", "symbol"])["buy"].sum()
        buys = net[net >= BIG_BUYER_CR * 1e7]

    for sym, d in frames.items():
        # delivery % above its own 50-day median
        dp = deliv[sym].reindex(d.index) if sym in deliv else pd.Series(np.nan, index=d.index)
        d["deliv_per"] = dp.values
        med = dp.rolling(50, min_periods=20).median()
        d["deliv_high"] = (dp > med).values
        # accumulation: above-normal delivery on 3 of the last 5 days while price rose over those 5 days
        d["accumulation"] = (((dp > med).astype(int).rolling(5).sum() >= 3) & (d["Close"] > d["Close"].shift(5))).values
        # deliv_not_low: avoid signals on days when delivery is well below normal (mostly speculative volume)
        d["deliv_not_low"] = (dp >= 0.8 * med).values
        # big_buyer: a large net buyer in bulk/block deals within the last BIG_BUYER_DAYS
        hit = pd.Series(0.0, index=d.index)
        if len(buys):
            b = buys.xs(sym, level="symbol") if sym in buys.index.get_level_values("symbol") else None
            if b is not None:
                b.index = pd.to_datetime(b.index)
                hit = hit.add(b.reindex(d.index).fillna(0), fill_value=0)
        d["big_buyer"] = (hit.rolling(BIG_BUYER_DAYS, min_periods=1).max() > 0).values
        # earnings_gap: results reaction day (same day if announced before 15:30, else next trading day)
        # closes >EARNINGS_GAP_PCT% up on 2x volume, in the upper half of the day's range
        react = np.zeros(len(d), dtype=bool)
        for ts in pd.to_datetime(results.get(sym, []), format="%d-%b-%Y %H:%M:%S"):
            day = ts.normalize() + (pd.Timedelta(days=1) if ts.hour * 60 + ts.minute >= 930 else pd.Timedelta(0))
            k = d.index.searchsorted(day)
            if k < len(d):
                react[k] = True
        c, prev = d["Close"], d["Close"].shift()
        upper = (c - d["Low"]) >= 0.5 * (d["High"] - d["Low"])
        d["earnings_gap"] = (react & (c / prev - 1 > EARNINGS_GAP_PCT / 100)
                             & (d["Volume"] > 2 * d["vol50"]) & upper).values
    return deals


_nse = None


def _session():
    """Shared requests session with browser-like headers for nseindia.com."""
    global _nse
    if _nse is None:
        _nse = requests.Session()
        _nse.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements"})
        try:
            _nse.get("https://www.nseindia.com", timeout=15)  # picks up cookies when allowed
        except Exception:
            pass
    return _nse


REV = ("RevenueFromOperations", "Income")  # banks only report total Income


PAT = ("ProfitLossForPeriod", "ProfitLossForThePeriod",
       "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates")


EPS = ("BasicEarningsLossPerShareFromContinuingOperations",
       "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations")


def _xval(x, tags, ctx):
    for t in tags:
        m = re.search(rf'<in-capmkt:{t} contextRef="{ctx}"[^>]*>([^<]*)<', x)
        if m and m.group(1).strip():
            return float(m.group(1))
    return None


def _cr(v):
    return None if v is None else round(v / 1e7, 1)  # rupees -> crore


def fundamentals(symbol, quarters=5):
    """Last few quarters of results, promoter holding and pledge from NSE. Cached for the day."""
    today = str(pd.Timestamp.now().date())
    with connect() as c:
        r = c.execute("SELECT data FROM fundamentals WHERE symbol = ? AND date = ?", (symbol, today)).fetchone()
    if r:
        return json.loads(r[0])
    s = _session()
    out = {"date": today, "symbol": symbol, "quarters": [], "promoter": [], "pledge_pct": None}

    try:  # quarterly results; one series (consolidated if filed, else standalone) so quarters compare
        fil = s.get("https://www.nseindia.com/api/integrated-filing-results",
                    params={"index": "equities", "symbol": symbol}, timeout=20).json()["data"]
        fil = [f for f in fil if f.get("type") == "Integrated Filing- Financials" and f.get("xbrl")
               and f.get("consolidated")]
        kind = "Consolidated" if any(f["consolidated"] == "Consolidated" for f in fil) else "Standalone"
        by_q = {}
        for f in fil:
            if f["consolidated"] == kind:
                by_q.setdefault(f["qe_Date"], f)  # newest filing per quarter comes first
        for q in sorted(by_q, key=pd.to_datetime, reverse=True)[:quarters]:
            x = s.get(by_q[q]["xbrl"], timeout=40).text
            eq = _xval(x, ("Equity",), "OneI")  # balance sheet: half-yearly only
            debt = (_xval(x, ("BorrowingsCurrent",), "OneI") or 0) + (_xval(x, ("BorrowingsNoncurrent",), "OneI") or 0)
            out["quarters"].append({"quarter": q, "type": kind,
                                    "revenue_cr": _cr(_xval(x, REV, "OneD")), "profit_cr": _cr(_xval(x, PAT, "OneD")),
                                    "eps": _xval(x, EPS, "OneD"),
                                    "debt_equity": round(debt / eq, 2) if eq else None})
    except Exception as e:
        print(f"[warn] results unavailable for {symbol}: {e}")

    try:  # promoter holding history + pledge from the latest shareholding XBRL
        shp = s.get("https://www.nseindia.com/api/corporate-share-holdings-master",
                    params={"index": "equities", "symbol": symbol}, timeout=20).json()
        out["promoter"] = [(h["date"], float(h["pr_and_prgrp"])) for h in shp[:5]
                           if h.get("pr_and_prgrp") not in (None, "", "-")]
        x = s.get(shp[0]["xbrl"], timeout=40).text
        ctx = "ShareholdingOfPromoterAndPromoterGroup_ContextI"
        pledged = re.search(rf'<in-bse-shp:NumberOfSharesEncumberedUnderPledged contextRef="{ctx}"[^>]*>([\d.]+)<', x)
        held = re.search(rf'<in-bse-shp:NumberOfShares contextRef="{ctx}"[^>]*>([\d.]+)<', x)
        if held:
            out["pledge_pct"] = round(100 * float(pledged.group(1)) / float(held.group(1)), 1) if pledged else 0.0
    except Exception as e:
        print(f"[warn] shareholding unavailable for {symbol}: {e}")

    with connect() as c:
        c.execute("INSERT OR REPLACE INTO fundamentals VALUES (?, ?, ?)", (symbol, today, json.dumps(out)))
    return out


def red_flags(f, sector):
    flags, q = [], f["quarters"]
    prof = [x["profit_cr"] for x in q if x["profit_cr"] is not None]
    if prof and prof[0] < 0:
        flags.append("loss in latest quarter")
    if sum(p < 0 for p in prof[:4]) >= 2:
        flags.append("losses in 2+ of last 4 quarters")
    if f["pledge_pct"] and f["pledge_pct"] > MAX_PLEDGE:
        flags.append(f"{f['pledge_pct']}% of promoter shares pledged")
    pr = [p for _, p in f["promoter"]]  # newest first
    if len(pr) >= 2 and pr[-1] - pr[0] > MAX_STAKE_DROP:
        flags.append(f"promoter stake down {pr[-1] - pr[0]:.1f} pts ({pr[-1]}% -> {pr[0]}%)")
    de = next((x["debt_equity"] for x in q if x["debt_equity"] is not None), None)
    if de is not None and de < 0:
        flags.append("negative net worth")
    elif de is not None and de > MAX_DE and "financ" not in sector.lower():
        flags.append(f"debt/equity {de}")
    return flags


def fund_summary(f):
    q = f["quarters"]
    if not q and not f["promoter"]:
        return "(no fundamentals available)"
    lines = []
    if q:
        lines.append(f"Quarterly results ({q[0]['type'].lower()}, Rs crore, newest first):")
        lines += [f"- {x['quarter']}: revenue {x['revenue_cr']}, net profit {x['profit_cr']}, EPS {x['eps']}" for x in q]
        if len(q) >= 5 and q[0]["revenue_cr"] and q[4]["revenue_cr"]:
            lines.append(f"Revenue YoY: {100 * (q[0]['revenue_cr'] / q[4]['revenue_cr'] - 1):.1f}%")
        if len(q) >= 5 and q[0]["profit_cr"] and q[4]["profit_cr"] and q[4]["profit_cr"] > 0:
            lines.append(f"Net profit YoY: {100 * (q[0]['profit_cr'] / q[4]['profit_cr'] - 1):.1f}%")
        de = next((x for x in q if x["debt_equity"] is not None), None)
        if de:
            lines.append(f"Debt/equity ({de['quarter']}): {de['debt_equity']}")
    if f["promoter"]:
        lines.append("Promoter holding: " + ", ".join(f"{d} {p}%" for d, p in f["promoter"]))
    if f["pledge_pct"] is not None:
        lines.append(f"Promoter shares pledged: {f['pledge_pct']}%")
    return "\n".join(lines)


# routine compliance filings that rarely move a stock
NOISE = ("trading window", "newspaper", "certificate under", "regulation 74", "loss of share",
         "duplicate share", "esop", "esos", "copy of", "change in registrar")


# filings worth opening the PDF for
IMPORTANT = ("financial result", "press release", "investor presentation", "outcome of board", "order", "award",
             "contract", "acquisition", "general updates", "guidance", "credit rating", "resignation")


def pdf_text(url, max_pages=8):
    """Download a filing PDF and return its text, trimmed. Empty for scanned/unreadable PDFs."""
    from pypdf import PdfReader
    try:
        r = _session().get(url, timeout=30)
        reader = PdfReader(io.BytesIO(r.content))
        text = " ".join((pg.extract_text() or "") for pg in reader.pages[:max_pages])
        return " ".join(text.split())[:PDF_CHARS]
    except Exception as e:
        print(f"[warn] PDF read failed {url}: {e}")
        return ""


def nse_announcements(symbol, n=12):
    """Latest NSE corporate announcements for a symbol, minus routine filings."""
    try:
        r = _session().get("https://www.nseindia.com/api/corporate-announcements",
                     params={"index": "equities", "symbol": symbol}, timeout=15)
        items = []
        for a in r.json():
            text = f"{a.get('desc', '')}: {a.get('attchmntText', '')}"
            if any(w in text.lower() for w in NOISE):
                continue
            items.append([f"- [NSE filing {a.get('an_dt', '')}] {text.strip()}", text.lower(), a.get("attchmntFile") or ""])
            if len(items) >= n:
                break
        # open PDFs in order of importance (earlier in IMPORTANT = more important), not date
        rank = lambda t: next((k for k, w in enumerate(IMPORTANT) if w in t), None)
        cands = sorted((it for it in items if it[2].lower().endswith(".pdf") and rank(it[1]) is not None),
                       key=lambda it: rank(it[1]))
        pdfs = 0
        for it in cands:
            if pdfs >= MAX_PDFS:
                break
            body = pdf_text(it[2])
            if body:
                it[0] += f"\n  PDF excerpt: {body}"
                pdfs += 1
        return [it[0] for it in items]
    except Exception as e:
        print(f"[warn] NSE announcements failed for {symbol}: {e}")
        return []
