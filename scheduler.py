"""Daily scheduler, running inside the API server: a scan every weekday after market close and a weekly research run.
Times are IST (config.SCHEDULE). Jobs go through jobs.submit, so only one runs at a time."""
import os
import sys
import threading
from datetime import datetime
import pandas as pd
from config import SCHEDULE
import jobs
from db import rows
from research import latest_validated


IST = "Asia/Kolkata"


def enabled():
    return os.getenv("SCHEDULER", "true").strip().lower() in ("1", "true", "yes", "on")


def _at(day, hhmm):
    h, m = map(int, hhmm.split(":"))
    return day.normalize() + pd.Timedelta(hours=h, minutes=m)


def next_runs(now=None):
    """Next scheduled scan and research times (IST)."""
    now = now or pd.Timestamp.now(tz=IST)
    scan = _at(now, SCHEDULE["scan_time"])
    while scan <= now or scan.weekday() >= 5:
        scan = _at(scan + pd.Timedelta(days=1), SCHEDULE["scan_time"])
    research = _at(now + pd.Timedelta(days=(SCHEDULE["research_day"] - now.weekday()) % 7), SCHEDULE["research_time"])
    if research <= now:
        research += pd.Timedelta(days=7)
    return {"scan": scan, "research": research}


def _ran_since(kind, since):
    """A job of this kind was created at or after `since` (IST), whatever its outcome."""
    local = since.tz_convert(datetime.now().astimezone().tzinfo).tz_localize(None)  # jobs.created is machine-local time
    return bool(rows("SELECT 1 FROM jobs WHERE kind = ? AND created >= ? LIMIT 1", (kind, f"{local:%Y-%m-%d %H:%M:%S}")))


def due(now=None):
    """The job kind that should start now, or None. Missed runs (server was off) are caught up the same day."""
    now = now or pd.Timestamp.now(tz=IST)
    if now.weekday() < 5 and now >= _at(now, SCHEDULE["scan_time"]) and not _ran_since("scan", _at(now, SCHEDULE["scan_time"])):
        return "scan"
    research_at = _at(now - pd.Timedelta(days=(now.weekday() - SCHEDULE["research_day"]) % 7), SCHEDULE["research_time"])
    v = latest_validated()
    stale = v is None or (now.tz_localize(None) - pd.Timestamp(v["generated"])).days > SCHEDULE["research_max_age"]
    if (now >= research_at or stale) and not _ran_since("research", research_at if not stale else now.normalize()):
        return "research"
    return None


def _loop(stop):
    while not stop.wait(60):
        try:
            kind = due()
            if kind and jobs.submit(kind, trigger="schedule"):
                print(f"[scheduler] started {kind}", file=sys.__stderr__)
        except Exception as e:  # never let one bad tick kill the scheduler
            print(f"[scheduler] error: {e}", file=sys.__stderr__)


_stop = threading.Event()


def start():
    if enabled():
        threading.Thread(target=_loop, args=(_stop,), daemon=True, name="scheduler").start()


def stop():
    _stop.set()
