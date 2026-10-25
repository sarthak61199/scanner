"""One-time import of the old file caches (nse_data/, fund_cache/, news_cache/, validated_setups.json) into trading.db.
Safe to rerun: existing rows are kept. Delete the old folders yourself once the counts look right."""
import glob
import json
import os
import pandas as pd
from config import FUND_CACHE, NEWS_CACHE, NSE_DATA, VALIDATED
from db import connect, dumps


def days(kind):
    """nse_data/<kind>/YYYYMMDD.csv -> rows, and every file's day (empty files are holidays, still 'fetched')."""
    files = sorted(glob.glob(os.path.join(NSE_DATA, kind, "*.csv")))
    with connect() as c:
        for f in files:
            day = pd.to_datetime(os.path.basename(f)[:8], format="%Y%m%d").strftime("%Y-%m-%d")
            df = pd.read_csv(f)
            if len(df):
                cols = list(df.columns)
                verb = "INSERT OR IGNORE" if kind == "delivery" else "INSERT"
                if kind == "deals" and c.execute("SELECT 1 FROM deals WHERE date = ? LIMIT 1", (day,)).fetchone():
                    continue  # deals have no key: skip days already imported
                c.executemany(f"{verb} INTO {kind} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                              df.astype(object).where(df.notna(), None).itertuples(index=False, name=None))
            c.execute("INSERT OR IGNORE INTO fetched_days VALUES (?, ?)", (kind, day))
    print(f"{kind}: {len(files)} day files")


def results():
    files = glob.glob(os.path.join(NSE_DATA, "results", "*.json"))
    with connect() as c:
        for f in files:
            sym = os.path.basename(f)[:-5]
            with open(f) as fh:
                dates = json.load(fh)["dates"]
            c.execute("INSERT OR IGNORE INTO results_fetched VALUES (?)", (sym,))
            c.executemany("INSERT OR IGNORE INTO results_dates VALUES (?, ?)", [(sym, d) for d in dates])
    print(f"results: {len(files)} stocks")


def funds():
    files = glob.glob(os.path.join(FUND_CACHE, "*.json"))
    with connect() as c:
        for f in files:
            with open(f) as fh:
                x = json.load(fh)
            c.execute("INSERT OR IGNORE INTO fundamentals VALUES (?, ?, ?)", (x["symbol"], x["date"], json.dumps(x)))
    print(f"fundamentals: {len(files)} stocks")


def news():
    files = glob.glob(os.path.join(NEWS_CACHE, "*.json"))
    n = 0
    with connect() as c:
        for f in files:
            day = os.path.basename(f)[:-5]
            with open(f) as fh:
                items = json.load(fh)
            c.executemany("INSERT OR IGNORE INTO news VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          [(k, day, v["published"], v["feed"], v["title"], v["summary"], v.get("category"),
                            v.get("impact"), json.dumps(v["sectors"]) if "sectors" in v else None) for k, v in items.items()])
            n += len(items)
    print(f"news: {n} headlines in {len(files)} day files")


def validated():
    if not os.path.exists(VALIDATED):
        return
    with open(VALIDATED) as f:
        v = json.load(f)
    with connect() as c:
        if c.execute("SELECT 1 FROM research_runs LIMIT 1").fetchone():
            print("research: runs already in the database, skipped validated_setups.json")
            return
        # the full combination table was only in research.md, so this run has no rows
        c.execute("INSERT INTO research_runs (created, test_start, rows, validated) VALUES (?, ?, NULL, ?)",
                  (f"{v['generated']} 00:00:00", v["test_start"], dumps(v)))
    print(f"research: imported validated_setups.json ({len(v['setups'])} setups)")


if __name__ == "__main__":
    days("delivery")
    days("deals")
    results()
    funds()
    news()
    validated()
    with connect() as c:
        for t in ("fetched_days", "delivery", "deals", "results_dates", "fundamentals", "news", "research_runs"):
            print(f"  {t}: {c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]} rows")
