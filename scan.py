"""
MVP: Indian stock discovery + timing scanner.

  pip install yfinance pandas requests anthropic python-dotenv pypdf fonttools fastapi uvicorn
  python scan.py                 # scan, print report, save to trading.db
  RESEARCH=true in .env          # instead: test all setups, save a research run
  cd ui && npm install && npm run build   # once, and after UI changes
  uvicorn api:app                # UI at http://localhost:8000, REST API under /api (scan/research as jobs)
  Settings: edit config.py. Files: config, data, nse, backtest, research, llm.

Pipeline: universe -> sector strength -> stock ranking -> setup detection
          -> backtested stats per setup -> trade plan -> (optional) Claude notes
Set ANTHROPIC_API_KEY to get LLM explanations for the top picks; USE_CLAUDE=false turns them off.
Not investment advice. Research tool.
"""
import os
import re
import pandas as pd
from config import MAX_OPEN, MIN_TURNOVER_CR, RISK_PCT, TAG_DAYS, TEST_MONTHS, TOP
from data import add_filters, download, enrich, load_macro, load_nifty, load_universe
from nse import add_nse_signals, fundamentals, red_flags
from backtest import backtest, position_size
from research import load_validated, run_research
from llm import llm_notes
from news import fetch_news, market_mood, mood_text, tag_news
from db import connect, dumps
from journal import open_trades, update_trades


def load_data():
    """Universe, prices with indicators/filters/NSE signals for every stock, and bulk/block deals."""
    uni = load_universe()
    print(f"Downloading {len(uni)} stocks (takes a minute)...")
    frames = {s: enrich(d) for s, d in download(list(uni)).items()}
    add_filters(frames, uni, load_nifty(), load_macro())
    deals = add_nse_signals(frames)
    print(f"Got data for {len(frames)} stocks\n")
    return uni, frames, deals


def research_job(job_id=None):
    return run_research(load_data()[1], job_id)


def scan_job(job_id=None):
    """Full scan; saves it to the scans table. Returns the scan id."""
    uni, frames, deals = load_data()
    validated = load_validated()

    # 1. Sector strength: median 3m & 6m return of members
    rows = []
    for s, d in frames.items():
        last = d.iloc[-1]
        rows.append({"sym": s, "sector": uni[s], "ret63": last["ret63"], "ret126": last["ret126"],
                     "turnover_cr": last["turnover_cr"], "close": last["Close"], "atr": last["atr"],
                     "above200": last["Close"] > last["sma200"],
                     **{v["key"]: bool(last[v["setup"]]) and all(bool(last[f]) for f in v["filters"])
                        for v in validated}})
    df = pd.DataFrame(rows)
    sec = df.groupby("sector").agg(ret63=("ret63", "median"), ret126=("ret126", "median"),
                                   breadth=("above200", "mean"), n=("sym", "count"))
    sec["score"] = sec["ret63"].rank(pct=True) * 0.5 + sec["ret126"].rank(pct=True) * 0.3 + sec["breadth"].rank(pct=True) * 0.2
    sec = sec.sort_values("score", ascending=False)
    print("=== SECTOR STRENGTH (where to look) ===")
    print(sec.head(10).assign(ret63=lambda x: (x.ret63 * 100).round(1), ret126=lambda x: (x.ret126 * 100).round(1),
                              breadth=lambda x: (x.breadth * 100).round(0), score=lambda x: x.score.round(2)).to_string())

    # 2. Stock ranking: own momentum + sector score, liquidity filter
    df = df[df["turnover_cr"] >= MIN_TURNOVER_CR]
    df["sector_score"] = df["sector"].map(sec["score"])
    df["score"] = df["ret63"].rank(pct=True) * 0.4 + df["ret126"].rank(pct=True) * 0.2 + df["sector_score"] * 0.4

    # 3. Trade history of each validated setup (with its own filters, exit and stop), for Claude's context
    last_day = max(d.index[-1] for d in frames.values())
    test_start = last_day - pd.DateOffset(months=TEST_MONTHS)
    stats, all_trades = {}, []
    for v in validated:
        stats[v["key"]], tr = backtest(frames, v["setup"], v["filters"], stop_atr=v["stop_atr"], exit_rule=v["exit"])
        all_trades += [{**t, "sector": uni[t["symbol"]]} for t in tr]
        print(f"  {v['key']:28s} {v['exit']:10s} stop {v['stop_atr']}xATR  test avgR {v['test']['avg_r']}  "
              f"{MAX_OPEN}-slot test avgR {v['test']['taken_avg_r']}")

    # 4. Trade plans: stocks where a validated setup triggered today, ranked by score
    plans = []
    for _, r in df.sort_values("score", ascending=False).iterrows():
        for v in validated:
            if r[v["key"]]:
                stop = r["close"] - v["stop_atr"] * r["atr"]
                qty = position_size(r["close"], r["close"] - stop)
                if not qty:  # one share is over the 20% position cap
                    print(f"  skipped {r['sym']} ({v['key']}): too expensive at {r['close']:.0f}")
                    continue
                has_target = v["exit"] in ("fixed", "breakeven")
                plans.append({"symbol": r["sym"], "sector": r["sector"], "setup": v["key"], "score": round(r["score"], 2),
                              "entry": round(r["close"], 1), "stop": round(stop, 1),
                              "target": round(r["close"] + 2 * (r["close"] - stop), 1) if has_target else "trail",
                              "exit": v["exit"], "qty": qty,
                              "test_avgR": v["test"]["avg_r"], "slot_test_avgR": v["test"]["taken_avg_r"]})
    plans = pd.DataFrame(plans).head(TOP)
    if not validated:
        print("\nNo validated setups: no edge right now, sit out.")

    # 5. Fundamental filter: drop plans whose company shows red flags in NSE filings
    funds, rejected, all_plans = {}, [], plans
    if not plans.empty:
        print("\nChecking fundamentals from NSE filings...")
        funds = {sym: fundamentals(sym) for sym in plans["symbol"].unique()}
        flags = [red_flags(funds[p["symbol"]], p["sector"]) for _, p in plans.iterrows()]
        all_plans = plans.copy()
        rejected = [(p["symbol"], p["setup"], "; ".join(f)) for (_, p), f in zip(plans.iterrows(), flags) if f]
        plans = plans[[not f for f in flags]].reset_index(drop=True)
        for sym, setup, why in rejected:
            print(f"  rejected {sym} ({setup}): {why}")

    print("\n=== TODAY'S TRADE PLANS (setup triggered, ranked) ===")
    if plans.empty:
        print("No live setups today. Top-ranked watchlist instead:")
        print(df.sort_values("score", ascending=False).head(TOP)[["sym", "sector", "score", "close"]].to_string(index=False))
    else:
        print(plans.to_string(index=False))

    # 6. Market mood from Mint headlines (archived every run; tagging needs Claude)
    notes, mood = {}, None
    use_claude = os.getenv("USE_CLAUDE", "true").strip().lower() in ("1", "true", "yes", "on")
    print("\nFetching Mint news...")
    fetch_news()
    if use_claude and os.getenv("ANTHROPIC_API_KEY"):
        try:
            tag_news(set(uni.values()), days=TAG_DAYS)
            mood = market_mood()
            print(f"\n=== MARKET MOOD (news, context only) ===\n{mood_text(mood)}")
        except Exception as e:
            print(f"\n[warn] news tagging skipped: {e}")

    # 7. Optional LLM commentary
    if use_claude and os.getenv("ANTHROPIC_API_KEY") and not plans.empty:
        try:
            notes = llm_notes(plans.head(5), funds, stats, validated, pd.DataFrame(all_trades), frames, deals, test_start, mood)
            conv = {i: (re.search(r"Conviction:\**\s*(HIGH|MEDIUM|LOW)", t, re.I) or [None, "?"])[1].upper()
                    for i, t in notes.items()}
            plans["conviction"] = pd.Series(conv).reindex(plans.index).fillna("-")
        except Exception as e:
            print(f"\n[warn] Claude notes skipped: {e}")

    scan_id = save_scan(job_id, sec, plans, df, rejected, funds, mood, notes, all_trades)
    print(f"\nSaved scan {scan_id}")

    # 8. Paper-trading journal: manage open paper trades first (frees slots), then record today's plans
    print("\nUpdating paper-trading journal...")
    update_trades(frames)
    if not plans.empty:
        plans["note"] = pd.Series(notes).reindex(plans.index)
    open_trades(scan_id, all_plans, plans, rejected, frames, validated)
    print(f"\nRules: max {MAX_OPEN} open trades, {RISK_PCT}% risk each; exits per EXIT_RULES. Not investment advice.")
    return scan_id


def save_scan(job_id, sec, plans, df, rejected, funds, mood, notes, trades):
    watch = df.sort_values("score", ascending=False).head(TOP)[["sym", "sector", "score", "close"]]
    cols = ["symbol", "setup", "variant", "mom", "date", "exit_date", "entry", "exit", "reason", "days", "gross_R", "R", "sector"]
    t = pd.DataFrame(trades, columns=cols)
    for c in ("date", "exit_date"):
        t[c] = pd.to_datetime(t[c]).dt.strftime("%Y-%m-%d")
    with connect() as c:
        scan_id = c.execute(
            "INSERT INTO scans (job_id, created, sectors, plans, watchlist, rejected, funds, mood, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, f"{pd.Timestamp.now():%Y-%m-%d %H:%M:%S}", dumps(sec.reset_index().to_dict("records")),
             dumps(plans.to_dict("records")), dumps(watch.to_dict("records")),
             dumps([{"symbol": s, "setup": k, "red_flags": w} for s, k, w in rejected]), dumps(funds), dumps(mood),
             dumps({plans.loc[i, "symbol"] + "|" + plans.loc[i, "setup"]: v for i, v in notes.items()}))).lastrowid
        c.executemany(f"INSERT INTO backtest_trades VALUES (?, {', '.join('?' * len(cols))})",
                      [(scan_id, *r) for r in t.astype(object).where(t.notna(), None).itertuples(index=False, name=None)])
    return scan_id


def main():
    if os.getenv("RESEARCH", "false").strip().lower() in ("1", "true", "yes", "on"):
        research_job()
    else:
        scan_job()


if __name__ == "__main__":
    main()
