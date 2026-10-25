"""REST API under /api plus the built React UI (ui/dist) on the same origin, no auth.
Run: uvicorn api:app --reload   UI: http://localhost:8000   Docs: http://localhost:8000/docs"""
import os
from contextlib import asynccontextmanager
from typing import Literal
import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import config
import jobs
import scheduler
from backtest import EXIT_RULES
from db import clean, loads, rows
from journal import journal_stats
from news import list_news, market_mood
from nse import fundamentals, red_flags
from research import latest_validated


@asynccontextmanager
async def lifespan(app):
    jobs.recover()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="NSE swing-trade scanner", lifespan=lifespan)
api = APIRouter(prefix="/api")
UI_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "dist")


SCAN_JSON = ("sectors", "plans", "watchlist", "rejected", "funds", "mood", "notes")


def _one(sql, params=()):
    r = rows(sql, params)
    if not r:
        raise HTTPException(404, "not found")
    return r[0]


def _since(days):
    return f"{pd.Timestamp.now() - pd.Timedelta(days=days):%Y-%m-%d}"


@api.get("/health")
def health():
    counts = {t: rows(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"]
              for t in ("delivery", "deals", "results_dates", "news", "scans", "research_runs", "jobs")}
    last = rows("SELECT created FROM scans ORDER BY id DESC LIMIT 1")
    return {"ok": True, "rows": counts, "last_scan": last[0]["created"] if last else None, "active_job": jobs.active()}


@api.get("/config")
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


@api.post("/jobs", status_code=202)
def create_job(body: JobIn):
    job_id = jobs.submit(body.kind)
    if job_id is None:
        raise HTTPException(409, f"job {jobs.active()} is already running")
    return _job(job_id)


@api.get("/jobs")
def list_jobs(limit: int = 20):
    return rows("SELECT id, kind, status, trigger, created, started, finished, error FROM jobs ORDER BY id DESC LIMIT ?",
                (limit,))


@api.get("/jobs/{job_id}")
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


@api.get("/scans")
def list_scans(limit: int = 20):
    out = []
    for s in rows("SELECT id, job_id, created, plans, mood FROM scans ORDER BY id DESC LIMIT ?", (limit,)):
        plans, mood = loads(s.pop("plans")), loads(s.pop("mood"))
        out.append({**s, "n_plans": len(plans), "symbols": [p["symbol"] for p in plans],
                    "mood_score": mood["score"] if mood else None})
    return out


@api.get("/scans/latest")
def latest_scan():
    return _scan("ORDER BY id DESC LIMIT 1")


@api.get("/scans/{scan_id}")
def get_scan(scan_id: int):
    return _scan("WHERE id = ?", (scan_id,))


@api.get("/scans/{scan_id}/trades")
def scan_trades(scan_id: int, setup: str | None = None, symbol: str | None = None):
    sql, params = "SELECT * FROM backtest_trades WHERE scan_id = ?", [scan_id]
    if setup:
        sql, params = sql + " AND variant = ?", params + [setup]
    if symbol:
        sql, params = sql + " AND symbol = ?", params + [symbol.upper()]
    return rows(sql + " ORDER BY date", params)


# ---------- research ----------
@api.get("/setups/validated")
def validated_setups():
    v = latest_validated()
    if v is None:
        raise HTTPException(404, "no research run yet")
    return {**v, "age_days": (pd.Timestamp.today() - pd.Timestamp(v["generated"])).days}


@api.get("/research")
def list_research(limit: int = 20):
    return [{**r, "validated": loads(r["validated"])}
            for r in rows("SELECT id, job_id, created, test_start, validated FROM research_runs ORDER BY id DESC LIMIT ?", (limit,))]


def _research(where, params=()):
    r = _one(f"SELECT * FROM research_runs {where}", params)
    return {**r, "rows": loads(r["rows"]), "validated": loads(r["validated"])}


@api.get("/research/latest")
def latest_research():
    return _research("ORDER BY id DESC LIMIT 1")


@api.get("/research/{run_id}")
def get_research(run_id: int):
    return _research("WHERE id = ?", (run_id,))


# ---------- journal & schedule ----------
@api.get("/journal")
def journal(status: Literal["open", "closed"] | None = None, variant: str | None = None, taken: bool | None = None):
    sql, params = "SELECT * FROM paper_trades WHERE 1 = 1", []
    for col, val in (("status", status), ("variant", variant), ("taken", None if taken is None else int(taken))):
        if val is not None:
            sql, params = sql + f" AND {col} = ?", params + [val]
    out = rows(sql + " ORDER BY signal_date DESC, score DESC", params)
    for t in out:
        t["filters"], t["taken"] = loads(t["filters"]), bool(t["taken"])
    return out


@api.get("/journal/stats")
def journal_summary():
    return clean(journal_stats())


@api.get("/schedule")
def schedule():
    n = scheduler.next_runs()
    return {"enabled": scheduler.enabled(), **config.SCHEDULE,
            "next_scan": f"{n['scan']:%Y-%m-%d %H:%M} IST", "next_research": f"{n['research']:%Y-%m-%d %H:%M} IST",
            "last_scheduled": rows("SELECT id, kind, status, created FROM jobs WHERE trigger = 'schedule' "
                                   "ORDER BY id DESC LIMIT 5")}


# ---------- news ----------
@api.get("/news")
def news(days: int = Query(config.MOOD_DAYS, ge=1, le=60), category: str | None = None):
    return list_news(days, category)


@api.get("/news/mood")
def news_mood(days: int = Query(config.MOOD_DAYS, ge=1, le=60)):
    return clean(market_mood(days))


# ---------- stocks ----------
@api.get("/stocks/{symbol}/fundamentals")
def stock_fundamentals(symbol: str, sector: str = ""):
    """Fetched from NSE on first request each day (slow), then cached. `sector` only affects the debt/equity flag."""
    f = fundamentals(symbol.upper())
    return {**f, "red_flags": red_flags(f, sector)}


@api.get("/stocks/{symbol}/delivery")
def stock_delivery(symbol: str, days: int = Query(60, ge=1, le=2000)):
    return rows("SELECT date, deliv_per FROM delivery WHERE symbol = ? AND date >= ? ORDER BY date",
                (symbol.upper(), _since(days)))


@api.get("/stocks/{symbol}/deals")
def stock_deals(symbol: str, days: int = Query(30, ge=1, le=2000)):
    return rows("SELECT * FROM deals WHERE symbol = ? AND date >= ? ORDER BY date DESC", (symbol.upper(), _since(days)))


app.include_router(api)


@app.get("/{path:path}", include_in_schema=False)
def ui(path: str):
    """Built UI files; any other path gets index.html so client-side routes work on reload."""
    if path.startswith("api/"):
        raise HTTPException(404, "not found")
    f = os.path.realpath(os.path.join(UI_DIST, path))
    if path and f.startswith(os.path.realpath(UI_DIST) + os.sep) and os.path.isfile(f):
        return FileResponse(f)
    index = os.path.join(UI_DIST, "index.html")
    if not os.path.isfile(index):
        raise HTTPException(404, "UI not built: run `npm run build` in ui/")
    return FileResponse(index)
