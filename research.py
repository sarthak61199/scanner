"""Research mode: test every setup x filter x exit x stop, keep what passes -> validated_setups.json."""
import json
import os
import pandas as pd
from config import COST_PCT, FILTERS, MAX_OPEN, MAX_TEST_DD_R, MIN_TEST_N, MIN_TEST_R, MIN_TRAIN_N, MIN_TRAIN_R, RESEARCH_EXITS, SETUPS, STOP_WIDTHS, TEST_MONTHS, VALIDATED
from backtest import backtest, capped_trades, risk_stats
from report import md_table


def _part_stats(t):
    """n/avg/win over all signals; drawdown and avg over the capped portfolio (MAX_OPEN positions)."""
    if not len(t):
        return {"n": 0, "avg_r": None, "win": None, "taken": 0, "taken_avg_r": None, "max_dd_r": None}
    c = capped_trades(t)
    dd, _ = risk_stats(c)
    return {"n": len(t), "avg_r": round(t["R"].mean(), 3), "win": round((t["R"] > 0).mean(), 3),
            "taken": len(c), "taken_avg_r": round(c["R"].mean(), 3), "max_dd_r": dd}


def research(frames, test_start):
    """Every setup x (no filter | one filter) x exit x stop width. Returns one row per combination
    with train/test stats, by-year results and the list of pass rules it failed."""
    rows = []
    for setup in SETUPS:
        for filters in [()] + [(f,) for f in FILTERS]:
            for rule in RESEARCH_EXITS:
                for w in STOP_WIDTHS:
                    _, tr = backtest(frames, setup, filters, stop_atr=w, exit_rule=rule)
                    t = pd.DataFrame(tr)
                    train = t[t["date"] < test_start] if len(t) else t
                    test = t[t["date"] >= test_start] if len(t) else t
                    by_year = {} if not len(t) else {int(y): {"n": len(g), "avg_r": round(g["R"].mean(), 3)}
                               for y, g in t.groupby(pd.to_datetime(t["date"]).dt.year)}
                    # rule 3: train still positive without its best year
                    ex_best = None
                    if len(train):
                        yrs = pd.to_datetime(train["date"]).dt.year
                        best = train.groupby(yrs)["R"].mean().idxmax()
                        rest = train[yrs != best]
                        ex_best = round(rest["R"].mean(), 3) if len(rest) else None
                    rows.append({"setup": setup, "filters": list(filters), "exit": rule, "stop_atr": w,
                                 "train": _part_stats(train), "test": _part_stats(test),
                                 "train_ex_best_year": ex_best, "by_year": by_year})
            print(f"  {setup:12s} {'+'.join(filters) or '(none)':16s} done")
    # rule 5 needs the unfiltered baseline with the same exit and stop
    base = {(r["setup"], r["exit"], r["stop_atr"]): r["test"]["avg_r"] for r in rows if not r["filters"]}
    for r in rows:
        tr, te, fails = r["train"], r["test"], []
        if tr["n"] < MIN_TRAIN_N: fails.append(f"train n {tr['n']} < {MIN_TRAIN_N}")
        elif tr["avg_r"] <= MIN_TRAIN_R: fails.append(f"train avgR {tr['avg_r']} <= {MIN_TRAIN_R}")
        if te["n"] < MIN_TEST_N: fails.append(f"test n {te['n']} < {MIN_TEST_N}")
        elif te["avg_r"] < MIN_TEST_R: fails.append(f"test avgR {te['avg_r']} < {MIN_TEST_R}")
        if te["taken_avg_r"] is not None and te["taken_avg_r"] < MIN_TEST_R:
            fails.append(f"test {MAX_OPEN}-slot account avgR {te['taken_avg_r']} < {MIN_TEST_R}")
        if r["train_ex_best_year"] is None or r["train_ex_best_year"] <= 0:
            fails.append(f"train without best year {r['train_ex_best_year']} <= 0")
        if te["max_dd_r"] is not None and te["max_dd_r"] > MAX_TEST_DD_R:
            fails.append(f"test drawdown {te['max_dd_r']}R > {MAX_TEST_DD_R}R")
        b = base.get((r["setup"], r["exit"], r["stop_atr"]))
        if r["filters"] and te["avg_r"] is not None and b is not None and te["avg_r"] <= b:
            fails.append(f"filter doesn't beat unfiltered test avgR {b}")
        r["fails"] = fails
    return rows


def pick_validated(rows):
    """Best passing combination per setup: highest test avgR, then fewer filters, then fixed exits."""
    simple = {e: i for i, e in enumerate(RESEARCH_EXITS)}
    out = []
    for setup in SETUPS:
        ok = [r for r in rows if r["setup"] == setup and not r["fails"]]
        if ok:
            out.append(sorted(ok, key=lambda r: (-r["test"]["avg_r"], len(r["filters"]), simple[r["exit"]]))[0])
    return out


def run_research(frames):
    last_day = max(d.index[-1] for d in frames.values())
    test_start = last_day - pd.DateOffset(months=TEST_MONTHS)
    n = len(SETUPS) * (len(FILTERS) + 1) * len(RESEARCH_EXITS) * len(STOP_WIDTHS)
    print(f"Research: {n} combinations (train: before {test_start:%Y-%m-%d}, test: after)...")
    rows = research(frames, test_start)
    chosen = pick_validated(rows)
    with open(VALIDATED, "w") as f:
        json.dump({"generated": f"{pd.Timestamp.today():%Y-%m-%d}", "test_start": f"{test_start:%Y-%m-%d}",
                   "rules": {"min_train_n": MIN_TRAIN_N, "min_train_avg_r": MIN_TRAIN_R, "min_test_n": MIN_TEST_N,
                             "min_test_avg_r": MIN_TEST_R, "max_test_dd_r": MAX_TEST_DD_R},
                   "setups": [{k: r[k] for k in ("setup", "filters", "exit", "stop_atr", "train", "test",
                                                 "train_ex_best_year", "by_year")} for r in chosen]}, f, indent=2)
    write_research_report(rows, chosen, test_start)
    print(f"\n{len([r for r in rows if not r['fails']])} of {len(rows)} combinations passed; "
          f"validated: {[' '.join(['+'.join([r['setup'], *r['filters']]), r['exit'], str(r['stop_atr'])]) for r in chosen] or 'none'}")
    print(f"Saved {os.path.basename(VALIDATED)} and research.md")


def write_research_report(rows, chosen, test_start):
    def flat(r):
        return {"setup": "+".join([r["setup"], *r["filters"]]), "exit": r["exit"], "stop": r["stop_atr"],
                "train_n": r["train"]["n"], "train_avgR": r["train"]["avg_r"],
                "ex_best_yr": r["train_ex_best_year"], "test_n": r["test"]["n"],
                "test_avgR": r["test"]["avg_r"], "test_win": r["test"]["win"],
                "test_taken": r["test"]["taken"], "taken_avgR": r["test"]["taken_avg_r"], "test_DD_R": r["test"]["max_dd_r"]}
    passed = [r for r in rows if not r["fails"]]
    # closest misses: failed only one rule, best test result first
    misses = sorted([r for r in rows if len(r["fails"]) == 1 and r["test"]["avg_r"] is not None],
                    key=lambda r: -r["test"]["avg_r"])[:10]
    lines = [f"# Setup research - {pd.Timestamp.today():%Y-%m-%d}", "",
             f"Train: before {test_start:%Y-%m-%d}. Test: after (held out). Results in R after {COST_PCT}% costs.", "",
             "**Pass rules:** "
             f"train n >= {MIN_TRAIN_N} and avgR > {MIN_TRAIN_R}; test n >= {MIN_TEST_N} and avgR >= {MIN_TEST_R}; "
             f"train still positive without its best year; test drawdown <= {MAX_TEST_DD_R}R "
             f"(portfolio of max {MAX_OPEN} open trades, same-day signals by momentum - test_taken/taken_avgR are those trades, "
             f"and taken_avgR must also be >= {MIN_TEST_R}); "
             "a filter must beat the unfiltered setup (same exit/stop) in test.", "",
             f"{len(rows)} combinations tested. Note: testing many combinations means some pass by luck.", "",
             "## Validated (saved to validated_setups.json)", ""]
    lines += [md_table(pd.DataFrame([flat(r) for r in chosen])), ""] if chosen else \
             ["**None.** No setup has a validated edge right now - the daily scan should sit out.", ""]
    lines += [f"## All passing combinations ({len(passed)})", ""]
    lines += [md_table(pd.DataFrame([flat(r) for r in sorted(passed, key=lambda r: -r['test']['avg_r'])])), ""] if passed else ["None.", ""]
    lines += ["## Closest misses (failed one rule)", ""]
    lines += [md_table(pd.DataFrame([{**flat(r), "failed": r["fails"][0]} for r in misses])), ""] if misses else ["None.", ""]
    with open("research.md", "w") as f:
        f.write("\n".join(lines))


def load_validated(max_age_days=30):
    """Setups that passed research mode. Each gets key 'setup+filter'."""
    if not os.path.exists(VALIDATED):
        raise SystemExit(f"{os.path.basename(VALIDATED)} not found. Run once with RESEARCH=true in .env first.")
    with open(VALIDATED) as f:
        v = json.load(f)
    age = (pd.Timestamp.today() - pd.Timestamp(v["generated"])).days
    if age > max_age_days:
        print(f"[warn] validated setups are {age} days old - rerun with RESEARCH=true")
    for x in v["setups"]:
        x["key"] = "+".join([x["setup"], *x["filters"]])
        x["generated"] = v["generated"]
    print("Validated setups: " + (", ".join(f"{x['key']} ({x['exit']}, {x['stop_atr']}xATR)" for x in v["setups"]) or "none"))
    return v["setups"]
