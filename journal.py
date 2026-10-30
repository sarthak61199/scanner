"""Paper-trading journal: every trade plan becomes a paper trade, managed with the backtest's exact exit rules,
so live results can be compared with the backtest. Updated by every scan."""
import json
import pandas as pd
from config import GO_LIVE, MAX_OPEN
from backtest import risk_stats, simulate_trade
from db import connect, rows
from research import latest_validated


def _now():
    return f"{pd.Timestamp.now():%Y-%m-%d %H:%M:%S}"


def update_trades(frames):
    """Replay every open paper trade from its entry bar through the latest data; close the ones that exited."""
    from data import download, enrich
    open_ = rows("SELECT * FROM paper_trades WHERE status = 'open'")
    missing = sorted({t["symbol"] for t in open_} - set(frames))
    if missing:  # dropped out of the NIFTY 500: fetch their prices separately
        extra = {s: enrich(d) for s, d in download(missing).items()}
        weak = next(iter(frames.values()))["mkt_weak"] if frames else None
        for d in extra.values():
            d["mkt_weak"] = weak.reindex(d.index).fillna(False).astype(bool).values if weak is not None else False
        frames = {**frames, **extra}
    closed = 0
    with connect() as c:
        for t in open_:
            d = frames.get(t["symbol"])
            day = pd.Timestamp(t["signal_date"])
            if d is None or day not in d.index:
                print(f"  [warn] journal: no prices for {t['symbol']} on {t['signal_date']}, left as is")
                continue
            s = simulate_trade(d, d.index.get_loc(day), t["stop_atr"], t["exit_rule"], partial=True)
            if s is None:
                continue
            if s["status"] == "closed":
                closed += 1
                c.execute("UPDATE paper_trades SET status = 'closed', exit_date = ?, exit = ?, reason = ?, days = ?, "
                          "gross_R = ?, R = ?, last_close = ?, updated = ? WHERE id = ?",
                          (f"{s['exit_date']:%Y-%m-%d}", s["exit"], s["reason"], s["days"], s["gross_R"], s["R"],
                           s["exit"], _now(), t["id"]))
            else:
                c.execute("UPDATE paper_trades SET current_stop = ?, last_close = ?, days = ?, gross_R = ?, R = ?, "
                          "updated = ? WHERE id = ?",
                          (s["stop"], s["last"], s["days"], s["gross_R"], s["R"], _now(), t["id"]))
    print(f"  journal: {len(open_)} open paper trades replayed, {closed} closed")


def open_trades(scan_id, all_plans, plans, rejected, frames, validated):
    """Record today's plans as paper trades: accepted ones (taken while a MAX_OPEN slot is free, in score order)
    and fundamentals-rejected ones (never taken; tracked to test whether the red-flag filter helps)."""
    if all_plans.empty:
        return
    rules = {v["key"]: v for v in validated}
    why = {(s, k): w for s, k, w in rejected}
    accepted = plans.set_index(["symbol", "setup"]) if not plans.empty else None
    with connect() as c:
        slots = MAX_OPEN - c.execute("SELECT COUNT(*) FROM paper_trades WHERE status = 'open' AND taken = 1").fetchone()[0]
        added = 0
        for p in all_plans.sort_values("score", ascending=False).to_dict("records"):
            sym, key = p["symbol"], p["setup"]
            day = frames[sym].index[-1]
            # like the backtest: one trade per stock and setup at a time, no new signal within 10 trading days
            recent = frames[sym].index[max(0, len(frames[sym]) - 10)]
            if c.execute("SELECT 1 FROM paper_trades WHERE symbol = ? AND variant = ? AND (status = 'open' OR signal_date >= ?)",
                         (sym, key, f"{recent:%Y-%m-%d}")).fetchone():
                continue
            rej = why.get((sym, key))
            a = accepted.loc[(sym, key)].to_dict() if accepted is not None and (sym, key) in accepted.index else {}
            conv = a.get("conviction") if a.get("conviction") in ("HIGH", "MEDIUM", "LOW") else None
            note = a.get("note") if isinstance(a.get("note"), str) else None
            taken = int(rej is None and slots > 0)
            v = rules[key]
            cur = c.execute(
                "INSERT OR IGNORE INTO paper_trades (scan_id, symbol, sector, variant, setup, filters, exit_rule, stop_atr, "
                "signal_date, entry, initial_stop, qty, score, conviction, note, rejected, taken, status, current_stop, "
                "last_close, days, gross_R, R, updated, backtest_slot_r) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, 0, 0, 0, ?, ?)",
                (scan_id, sym, p["sector"], key, v["setup"], json.dumps(v["filters"]), v["exit"], v["stop_atr"],
                 f"{day:%Y-%m-%d}", p["entry"], p["stop"], int(p["qty"]), p["score"],
                 conv, note, rej, taken,
                 p["stop"], p["entry"], _now(), v["test"]["taken_avg_r"]))
            if cur.rowcount:
                added += 1
                slots -= taken
    print(f"  journal: {added} new paper trades")


def _range(r):
    """95% range for an average R (mean +- 1.96 standard errors); None below 2 trades."""
    if len(r) < 2:
        return None, None
    margin = 1.96 * r.std() / len(r) ** 0.5
    return round(float(r.mean() - margin), 3), round(float(r.mean() + margin), 3)


def _go_live(t):
    """The GO_LIVE checklist over trades the account really took: accepted, taken, closed since GO_LIVE['start']."""
    g = GO_LIVE
    c = t[t["rejected"].isna() & (t["taken"] == 1) & (t["status"] == "closed")]
    c = c[c["exit_date"] >= g["start"]]
    avg = round(float(c["R"].mean()), 3) if len(c) else None
    low, high = _range(c["R"])
    exp = c["backtest_slot_r"].dropna().astype(float) if len(c) else c["R"]
    expected = round(float(exp.mean()), 3) if len(exp) else None
    dd = risk_stats(c.assign(date=c["exit_date"]))[0]
    months = round(max((pd.Timestamp.now() - pd.Timestamp(g["start"])).days, 0) / 30.44, 1)
    need = None if expected is None else round(g["min_backtest_ratio"] * expected, 3)
    checks = [
        {"key": "closed", "label": "Closed trades", "value": len(c), "target": f">= {g['min_closed']}", "ok": len(c) >= g["min_closed"]},
        {"key": "months", "label": "Months running", "value": months, "target": f">= {g['min_months']}", "ok": months >= g["min_months"]},
        {"key": "avg_r", "label": "Average R", "value": avg, "target": f"> {g['min_avg_r']}", "ok": avg is not None and avg > g["min_avg_r"]},
        {"key": "backtest", "label": "Average R vs backtest", "value": avg,
         "target": "no backtest figure" if need is None else f">= {need} ({g['min_backtest_ratio']:.0%} of {expected})",
         "ok": avg is not None and need is not None and avg >= need},
        {"key": "drawdown", "label": "Max drawdown (R)", "value": dd, "target": f"<= {g['max_dd_r']}", "ok": dd is not None and dd <= g["max_dd_r"]},
    ]
    return {"ready": all(x["ok"] for x in checks), "start": g["start"], "checks": checks,
            "avg_r": avg, "low": low, "high": high, "expected_r": expected}


def _group(t):
    if not len(t):
        return {"n": 0, "closed": 0, "open": 0, "avg_r": None, "low": None, "high": None, "win": None, "total_r": 0}
    cl = t[t["status"] == "closed"]
    low, high = _range(cl["R"])
    return {"n": len(t), "closed": len(cl), "open": int((t["status"] == "open").sum()),
            "avg_r": round(cl["R"].mean(), 3) if len(cl) else None, "low": low, "high": high,
            "win": round((cl["R"] > 0).mean(), 3) if len(cl) else None,
            "total_r": round(cl["R"].sum(), 2)}


def journal_stats():
    """Live results by setup (all signals vs the MAX_OPEN-slot account) next to the backtest test period,
    plus by Claude conviction and accepted vs rejected-on-fundamentals."""
    t = pd.DataFrame(rows("SELECT * FROM paper_trades"))
    v = latest_validated() or {"setups": []}
    bt = {"+".join([s["setup"], *s["filters"]]): s["test"] for s in v["setups"]}
    if not len(t):
        t = pd.DataFrame(columns=["variant", "status", "R", "taken", "rejected", "conviction", "exit_date", "backtest_slot_r"])
    acc = t[t["rejected"].isna()]
    by_setup = []
    for key in sorted(set(t["variant"]) | set(bt)):
        g = acc[acc["variant"] == key]
        by_setup.append({"variant": key, "validated": key in bt, "all": _group(g), "taken": _group(g[g["taken"] == 1]),
                         "backtest_test_avg_r": bt.get(key, {}).get("avg_r"),
                         "backtest_slot_avg_r": bt.get(key, {}).get("taken_avg_r")})
    return {"go_live": _go_live(t),
            "overall": {"accepted": _group(acc), "taken": _group(acc[acc["taken"] == 1]),
                        "rejected": _group(t[t["rejected"].notna()])},
            "by_setup": by_setup,
            "by_conviction": {k: _group(acc[acc["conviction"].fillna("none") == k])
                              for k in ("HIGH", "MEDIUM", "LOW", "none")}}
