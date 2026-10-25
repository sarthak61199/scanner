"""REST API for the React UI (no auth). Run: uvicorn api:app --reload   Docs: http://localhost:8000/docs"""
from contextlib import asynccontextmanager
from typing import Literal
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import config
import jobs
from backtest import EXIT_RULES
from db import clean, loads, rows
from news import list_news, market_mood
from nse import fundamentals, red_flags
from research import latest_validated


@asynccontextmanager
async def lifespan(app):
    jobs.recover()
    yield


app = FastAPI(title="NSE swing-trade scanner", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


SCAN_JSON = ("sectors", "plans", "watchlist", "rejected", "funds", "mood", "notes")


def _one(sql, params=()):
    r = rows(sql, params)
    if not r:
        raise HTTPException(404, "not found")
    return r[0]


def _since(days):
    return f"{pd.Timestamp.now() - pd.Timedelta(days=days):%Y-%m-%d}"


@app.get("/health")
def health():
    counts = {t: rows(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"]
              for t in ("delivery", "deals", "results_dates", "news", "scans", "research_runs", "jobs")}
    last = rows("SELECT created FROM scans ORDER BY id DESC LIMIT 1")
    return {"ok": True, "rows": counts, "last_scan": last[0]["created"] if last else None, "active_job": jobs.active()}


@app.get("/config")
def get_config():
    keys = ("CAPITAL", "RISK_PCT", "MAX_OPEN", "MIN_TURNOVER_CR", "TOP", "HISTORY_YEARS", "TEST_MONTHS", "COST_PCT",
            "SETUPS", "FILTERS", "EXITS", "STOP_WIDTHS", "MACRO", "MOOD_DAYS")
    return {**{k.lower(): getattr(config, k) for k in keys}, "exit_rules": EXIT_RULES}


# ---------- jobs ----------
class JobIn(BaseModel):
    kind: Literal["scan", "research"]


def _job(job_id, tail=None):
    j = _one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if tail is not None:
        j["log"] = "\n".join(j["log"].splitlines()[-tail:])
    return j


@app.post("/jobs", status_code=202)
def create_job(body: JobIn):
    job_id = jobs.submit(body.kind)
    if job_id is None:
        raise HTTPException(409, f"job {jobs.active()} is already running")
    return _job(job_id)


@app.get("/jobs")
def list_jobs(limit: int = 20):
    return rows("SELECT id, kind, status, created, started, finished, error FROM jobs ORDER BY id DESC LIMIT ?", (limit,))


@app.get("/jobs/{job_id}")
def get_job(job_id: int, tail: int | None = Query(None, ge=1)):
    return _job(job_id, tail)


# ---------- scans ----------
def _scan(where, params=()):
    s = _one(f"SELECT * FROM scans {where}", params)
    for k in SCAN_JSON:
        s[k] = loads(s[k])
    notes = s.pop("notes") or {}
    for p in s["plans"]:
        p["note"] = notes.get(f"{p['symbol']}|{p['setup']}")
    return s


@app.get("/scans")
def list_scans(limit: int = 20):
    out = []
    for s in rows("SELECT id, job_id, created, plans, mood FROM scans ORDER BY id DESC LIMIT ?", (limit,)):
        plans, mood = loads(s.pop("plans")), loads(s.pop("mood"))
        out.append({**s, "n_plans": len(plans), "symbols": [p["symbol"] for p in plans],
                    "mood_score": mood["score"] if mood else None})
    return out


@app.get("/scans/latest")
def latest_scan():
    return _scan("ORDER BY id DESC LIMIT 1")


@app.get("/scans/{scan_id}")
def get_scan(scan_id: int):
    return _scan("WHERE id = ?", (scan_id,))


@app.get("/scans/{scan_id}/trades")
def scan_trades(scan_id: int, setup: str | None = None, symbol: str | None = None):
    sql, params = "SELECT * FROM backtest_trades WHERE scan_id = ?", [scan_id]
    if setup:
        sql, params = sql + " AND variant = ?", params + [setup]
    if symbol:
        sql, params = sql + " AND symbol = ?", params + [symbol.upper()]
    return rows(sql + " ORDER BY date", params)


# ---------- research ----------
@app.get("/setups/validated")
def validated_setups():
    v = latest_validated()
    if v is None:
        raise HTTPException(404, "no research run yet")
    return {**v, "age_days": (pd.Timestamp.today() - pd.Timestamp(v["generated"])).days}


@app.get("/research")
def list_research(limit: int = 20):
    return [{**r, "validated": loads(r["validated"])}
            for r in rows("SELECT id, job_id, created, test_start, validated FROM research_runs ORDER BY id DESC LIMIT ?", (limit,))]


def _research(where, params=()):
    r = _one(f"SELECT * FROM research_runs {where}", params)
    return {**r, "rows": loads(r["rows"]), "validated": loads(r["validated"])}


@app.get("/research/latest")
def latest_research():
    return _research("ORDER BY id DESC LIMIT 1")


@app.get("/research/{run_id}")
def get_research(run_id: int):
    return _research("WHERE id = ?", (run_id,))


# ---------- news ----------
@app.get("/news")
def news(days: int = Query(config.MOOD_DAYS, ge=1, le=60), category: str | None = None):
    return list_news(days, category)


@app.get("/news/mood")
def news_mood(days: int = Query(config.MOOD_DAYS, ge=1, le=60)):
    return clean(market_mood(days))


# ---------- stocks ----------
@app.get("/stocks/{symbol}/fundamentals")
def stock_fundamentals(symbol: str, sector: str = ""):
    """Fetched from NSE on first request each day (slow), then cached. `sector` only affects the debt/equity flag."""
    f = fundamentals(symbol.upper())
    return {**f, "red_flags": red_flags(f, sector)}


@app.get("/stocks/{symbol}/delivery")
def stock_delivery(symbol: str, days: int = Query(60, ge=1, le=2000)):
    return rows("SELECT date, deliv_per FROM delivery WHERE symbol = ? AND date >= ? ORDER BY date",
                (symbol.upper(), _since(days)))


@app.get("/stocks/{symbol}/deals")
def stock_deals(symbol: str, days: int = Query(30, ge=1, le=2000)):
    return rows("SELECT * FROM deals WHERE symbol = ? AND date >= ? ORDER BY date DESC", (symbol.upper(), _since(days)))
