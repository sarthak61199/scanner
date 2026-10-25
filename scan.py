"""
MVP: Indian stock discovery + timing scanner.

  pip install yfinance pandas requests anthropic python-dotenv pypdf fonttools
  python scan.py                 # scan, print report, write report.md
  RESEARCH=true in .env          # instead: test all setups, write validated_setups.json + research.md
  Settings: edit config.py. Files: config, data, nse, backtest, research, llm, report.

Pipeline: universe -> sector strength -> stock ranking -> setup detection
          -> backtested stats per setup -> trade plan -> (optional) Claude notes
Set ANTHROPIC_API_KEY to get LLM explanations for the top picks; USE_CLAUDE=false turns them off.
Not investment advice. Research tool.
"""
import os
import re
import pandas as pd
from config import CAPITAL, MAX_OPEN, MIN_TURNOVER_CR, RISK_PCT, TEST_MONTHS, TOP
from data import add_filters, download, enrich, load_nifty, load_universe
from nse import add_nse_signals, fundamentals, red_flags
from backtest import backtest
from research import load_validated, run_research
from llm import llm_notes
from report import write_report


def main():

    uni = load_universe()
    print(f"Downloading {len(uni)} stocks (takes a minute)...")
    frames = {s: enrich(d) for s, d in download(list(uni)).items()}
    add_filters(frames, uni, load_nifty())
    deals = add_nse_signals(frames)
    print(f"Got data for {len(frames)} stocks\n")

    if os.getenv("RESEARCH", "false").strip().lower() in ("1", "true", "yes", "on"):
        run_research(frames)
        return
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
    pd.DataFrame(all_trades).to_csv("backtest_trades.csv", index=False)

    # 4. Trade plans: stocks where a validated setup triggered today, ranked by score
    risk_amt = CAPITAL * RISK_PCT / 100
    plans = []
    for _, r in df.sort_values("score", ascending=False).iterrows():
        for v in validated:
            if r[v["key"]]:
                stop = r["close"] - v["stop_atr"] * r["atr"]
                qty = int(risk_amt / (r["close"] - stop))
                qty = min(qty, int(CAPITAL * 0.2 / r["close"]))  # cap 20% capital per position
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
    funds, rejected = {}, []
    if not plans.empty:
        print("\nChecking fundamentals from NSE filings...")
        funds = {sym: fundamentals(sym) for sym in plans["symbol"].unique()}
        flags = [red_flags(funds[p["symbol"]], p["sector"]) for _, p in plans.iterrows()]
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

    # 6. Optional LLM commentary
    notes = {}
    use_claude = os.getenv("USE_CLAUDE", "true").strip().lower() in ("1", "true", "yes", "on")
    if use_claude and os.getenv("ANTHROPIC_API_KEY") and not plans.empty:
        try:
            notes = llm_notes(plans.head(5), funds, stats, validated, pd.DataFrame(all_trades), frames, deals, test_start)
            conv = {i: (re.search(r"Conviction:\**\s*(HIGH|MEDIUM|LOW)", t, re.I) or [None, "?"])[1].upper()
                    for i, t in notes.items()}
            plans["conviction"] = pd.Series(conv).reindex(plans.index).fillna("-")
        except Exception as e:
            print(f"\n[warn] Claude notes skipped: {e}")

    write_report(sec, validated, plans, df, notes, TOP, funds, rejected)
    print("\nSaved report.md")
    print(f"\nRules: max {MAX_OPEN} open trades, {RISK_PCT}% risk each; exits per EXIT_RULES. Not investment advice.")


if __name__ == "__main__":
    main()
