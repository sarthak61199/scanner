"""Trade simulation: entry at close, stop/target/trailing exits, costs, drawdown, 5-slot account."""
import pandas as pd
import numpy as np
from config import COST_PCT, MAX_OPEN


def simulate_trade(d, i, stop_atr=2.0, exit_rule="fixed", rr=2.0):
    """Buy at close of day i. Initial stop = stop_atr x ATR below entry. Gaps fill at the open.
    Exit rules:
      fixed       target at rr x risk, exit after 30 days
      breakeven   fixed, but stop moves to entry once the trade is up 1R
      ema_trail   no target; exit on a close below the 20-day EMA (max 60 days)
      chandelier  no target; stop trails highest high - 3 x ATR, only moves up (max 60 days)
      +mkt        also exit at the close when NIFTY closes below its 50-day average"""
    entry, atr = d["Close"].iat[i], d["atr"].iat[i]
    risk = stop_atr * atr
    if not risk > 0:
        return None
    rule, mkt = exit_rule.split("+")[0], exit_rule.endswith("+mkt")
    has_target = rule in ("fixed", "breakeven")
    max_days = 30 if has_target else 60
    stop, tgt = entry - risk, entry + rr * risk
    sl = slice(i + 1, i + 1 + max_days)
    o, h, l, c = (d[k].values[sl] for k in ("Open", "High", "Low", "Close"))
    ema, atrs, weak = d["ema20"].values[sl], d["atr"].values[sl], d["mkt_weak"].values[sl]
    if not len(c):
        return None
    exit_px, reason, days, hh = c[-1], "time", len(c), entry
    for k in range(len(c)):
        if o[k] <= stop:                                   # gapped through the stop
            exit_px, reason, days = o[k], "stop_gap", k + 1; break
        if has_target and o[k] >= tgt:                     # gapped over the target
            exit_px, reason, days = o[k], "target_gap", k + 1; break
        if l[k] <= stop:                                   # stop first if both touched (conservative)
            exit_px, reason, days = stop, "stop", k + 1; break
        if has_target and h[k] >= tgt:
            exit_px, reason, days = tgt, "target", k + 1; break
        # end-of-day checks and stop updates (apply from the next day)
        if rule == "ema_trail" and c[k] < ema[k]:
            exit_px, reason, days = c[k], "trail", k + 1; break
        if mkt and weak[k]:
            exit_px, reason, days = c[k], "market", k + 1; break
        if rule == "breakeven" and h[k] >= entry + risk:
            stop = max(stop, entry)
        if rule == "chandelier":
            hh = max(hh, h[k])
            stop = max(stop, hh - 3 * atrs[k])
    if reason == "time" and len(c) < max_days:            # still open at the end of the data
        return None
    gross = (exit_px - entry) / risk
    cost = entry * COST_PCT / 100 / risk                   # round-trip costs, in R
    return {"date": d.index[i], "exit_date": d.index[i + days], "entry": round(entry, 2), "exit": round(float(exit_px), 2),
            "reason": reason, "days": days, "gross_R": round(gross, 3), "R": round(gross - cost, 3)}


def backtest(frames, setup, filters=(), **kw):
    """Simulate every historical signal of a setup (+ filters). Returns summary stats and the trade list.
    kw goes to simulate_trade (stop_atr, exit_rule)."""
    trades, variant = [], "+".join([setup, *filters])
    for sym, d in frames.items():
        mask = d[setup].values.copy()
        for f in filters:
            mask &= d[f].values.astype(bool)
        last = -999
        for i in np.where(mask)[0]:
            if i - last < 10:                  # de-duplicate clustered signals
                continue
            last = i
            t = simulate_trade(d, i, **kw)
            if t:
                trades.append({"symbol": sym, "setup": setup, "variant": variant,
                               "mom": round(float(d["ret63"].iat[i]), 4), **t})  # 3m return, ranks same-day signals
    return summarize(trades), trades


def risk_stats(t):
    """Max drawdown (in R, trades taken in date order, 1R each) and longest losing streak."""
    if not len(t):
        return None, None
    r = t.sort_values("date")["R"].values
    cum = np.cumsum(r)
    dd = float((np.maximum.accumulate(np.maximum(cum, 0)) - cum).max())
    streak = run = 0
    for x in r:
        run = run + 1 if x <= 0 else 0
        streak = max(streak, run)
    return round(dd, 1), streak


def capped_trades(t, max_open=MAX_OPEN):
    """Trades a real account would have taken: in date order, skip signals while max_open trades are open.
    Same-day signals are taken strongest 3-month momentum first (as the daily scan ranks them)."""
    taken, open_exits = [], []
    for _, r in t.sort_values(["date", "mom"], ascending=[True, False]).iterrows():
        open_exits = [x for x in open_exits if x > r["date"]]
        if len(open_exits) < max_open:
            open_exits.append(r["exit_date"])
            taken.append(r)
    return pd.DataFrame(taken)


EXIT_RULES = {
    "fixed": "target at 2R; exit after 30 trading days if neither stop nor target is hit",
    "breakeven": "target at 2R; move the stop to entry once the trade is up 1R; exit after 30 trading days",
    "ema_trail": "no target; exit at the close when price closes below the 20-day EMA (max 60 trading days)",
    "chandelier": "no target; trail the stop at highest high since entry minus 3 x ATR, only moving up (max 60 trading days)",
}


def summarize(trades):
    if not trades:
        return {"n": 0, "win%": 0, "avgR": 0, "grossR": 0, "by_year": {}}
    t = pd.DataFrame(trades)
    by_year = {int(y): {"n": len(g), "avgR": round(g["R"].mean(), 2)}
               for y, g in t.groupby(pd.to_datetime(t["date"]).dt.year)}
    return {"n": len(t), "win%": round(100 * (t["R"] > 0).mean(), 1),
            "avgR": round(t["R"].mean(), 2), "grossR": round(t["gross_R"].mean(), 2), "by_year": by_year}
