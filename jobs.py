"""Background jobs for the API: one scan or research run at a time, output captured into jobs.log."""
import contextlib
import io
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from db import connect


_pool = ThreadPoolExecutor(1)  # one at a time: both jobs hit NSE rate limits
_lock = threading.Lock()


def _now():
    return f"{pd.Timestamp.now():%Y-%m-%d %H:%M:%S}"


class _Log(io.TextIOBase):
    """stdout replacement that appends each completed line to the job's log column."""
    def __init__(self, job_id):
        self.job_id, self.buf = job_id, ""

    def write(self, s):
        self.buf += s
        if "\n" in self.buf:
            done, self.buf = self.buf.rsplit("\n", 1)
            with connect() as c:
                c.execute("UPDATE jobs SET log = log || ? WHERE id = ?", (done + "\n", self.job_id))
        return len(s)

    def flush(self):
        if self.buf:
            self.write("\n")


def recover():
    """At API startup: jobs left running/queued by a crash or restart can't finish, so mark them failed."""
    with connect() as c:
        c.execute("UPDATE jobs SET status = 'failed', finished = ?, error = 'interrupted (server restarted)' "
                  "WHERE status IN ('queued', 'running')", (_now(),))


def active():
    with connect() as c:
        r = c.execute("SELECT id FROM jobs WHERE status IN ('queued', 'running') LIMIT 1").fetchone()
    return r[0] if r else None


def submit(kind):
    """Queue a 'scan' or 'research' job. Returns the new job id, or None if one is already queued/running."""
    with _lock:
        if active():
            return None
        with connect() as c:
            job_id = c.execute("INSERT INTO jobs (kind, status, created) VALUES (?, 'queued', ?)", (kind, _now())).lastrowid
    _pool.submit(_run, job_id, kind)
    return job_id


def _run(job_id, kind):
    from scan import research_job, scan_job
    with connect() as c:
        c.execute("UPDATE jobs SET status = 'running', started = ? WHERE id = ?", (_now(), job_id))
    status, error, log = "done", None, _Log(job_id)
    try:
        # redirect_stdout is process-wide: fine with a single worker, but API request logging must not use print
        with contextlib.redirect_stdout(log):
            (scan_job if kind == "scan" else research_job)(job_id)
    except BaseException as e:
        status, error = "failed", f"{type(e).__name__}: {e}"
        log.write(traceback.format_exc())
    finally:
        log.flush()
        with connect() as c:
            c.execute("UPDATE jobs SET status = ?, finished = ?, error = ? WHERE id = ?", (status, _now(), error, job_id))
