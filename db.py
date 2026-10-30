"""SQLite storage: NSE/fundamentals/news caches and scan/research outputs, in one file (config.DB_PATH)."""
import json
import math
import sqlite3
from contextlib import contextmanager
from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS fetched_days (kind TEXT, date TEXT, PRIMARY KEY (kind, date));
CREATE TABLE IF NOT EXISTS delivery (date TEXT, symbol TEXT, deliv_per REAL, PRIMARY KEY (date, symbol));
CREATE TABLE IF NOT EXISTS deals (date TEXT, kind TEXT, symbol TEXT, client TEXT, side TEXT, qty REAL, price REAL);
CREATE INDEX IF NOT EXISTS deals_date ON deals (date);
CREATE INDEX IF NOT EXISTS deals_symbol ON deals (symbol, date);
CREATE TABLE IF NOT EXISTS results_fetched (symbol TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS results_dates (symbol TEXT, announced_at TEXT, PRIMARY KEY (symbol, announced_at));
CREATE TABLE IF NOT EXISTS fundamentals (symbol TEXT PRIMARY KEY, date TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY, day TEXT, published TEXT, feed TEXT, title TEXT, summary TEXT,
                                 category TEXT, impact INTEGER, sectors TEXT);
CREATE INDEX IF NOT EXISTS news_day ON news (day);
CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, kind TEXT, status TEXT, created TEXT, started TEXT,
                                 finished TEXT, error TEXT, log TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, job_id INTEGER, created TEXT, sectors TEXT, plans TEXT,
                                  watchlist TEXT, rejected TEXT, funds TEXT, mood TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS backtest_trades (scan_id INTEGER, symbol TEXT, setup TEXT, variant TEXT, mom REAL, date TEXT,
                                            exit_date TEXT, entry REAL, exit REAL, reason TEXT, days INTEGER,
                                            gross_R REAL, R REAL, sector TEXT);
CREATE INDEX IF NOT EXISTS trades_scan ON backtest_trades (scan_id, variant);
CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY, scan_id INTEGER, symbol TEXT, sector TEXT, variant TEXT, setup TEXT, filters TEXT,
    exit_rule TEXT, stop_atr REAL, signal_date TEXT, entry REAL, initial_stop REAL, qty INTEGER, score REAL,
    conviction TEXT, note TEXT, rejected TEXT, taken INTEGER, status TEXT, current_stop REAL, last_close REAL,
    exit_date TEXT, exit REAL, reason TEXT, days INTEGER, gross_R REAL, R REAL, updated TEXT, backtest_slot_r REAL,
    UNIQUE (symbol, variant, signal_date));
CREATE TABLE IF NOT EXISTS research_runs (id INTEGER PRIMARY KEY, job_id INTEGER, created TEXT, test_start TEXT,
                                          rows TEXT, validated TEXT);
"""


@contextmanager
def connect():
    """New connection per use, safe across the API's threads: `with connect() as c:` commits and closes."""
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    try:
        with c:
            yield c
    finally:
        c.close()


def _backfill_slot_r(c):
    """Give existing paper trades the 5-slot test avgR of the newest research run on or before their signal date."""
    runs = [(r["created"][:10], json.loads(r["validated"]))
            for r in c.execute("SELECT created, validated FROM research_runs ORDER BY id")]
    for t in c.execute("SELECT id, variant, signal_date FROM paper_trades").fetchall():
        past = [v for day, v in runs if day <= t["signal_date"]]
        if past:
            s = next((s for s in past[-1]["setups"] if "+".join([s["setup"], *s["filters"]]) == t["variant"]), None)
            if s:
                c.execute("UPDATE paper_trades SET backtest_slot_r = ? WHERE id = ?", (s["test"]["taken_avg_r"], t["id"]))


def init_db():
    with connect() as c:
        c.executescript(SCHEMA)
        if "trigger" not in {r["name"] for r in c.execute("PRAGMA table_info(jobs)")}:  # added after the first release
            c.execute("ALTER TABLE jobs ADD COLUMN trigger TEXT DEFAULT 'manual'")
        if "backtest_slot_r" not in {r["name"] for r in c.execute("PRAGMA table_info(paper_trades)")}:  # added later too
            c.execute("ALTER TABLE paper_trades ADD COLUMN backtest_slot_r REAL")
            _backfill_slot_r(c)


def clean(x):
    """NaN/inf -> None, recursively, so stored JSON is valid."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x


def dumps(x):
    return json.dumps(clean(x), default=str)


def loads(s):
    return None if s is None else json.loads(s)


def rows(sql, params=()):
    with connect() as c:
        return [dict(r) for r in c.execute(sql, params)]


init_db()
