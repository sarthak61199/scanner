"""report.md writer."""
import pandas as pd
from config import COST_PCT, MAX_OPEN, RISK_PCT
from nse import fund_summary
from backtest import EXIT_RULES


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_report(sec, validated, plans, df, notes, top, funds, rejected):
    out = [f"# Market Scan: {pd.Timestamp.now():%Y-%m-%d %H:%M}", ""]

    out += ["## Sector strength", ""]
    s = sec.head(10).reset_index()
    s["ret63"] = (s["ret63"] * 100).round(1).astype(str) + "%"
    s["ret126"] = (s["ret126"] * 100).round(1).astype(str) + "%"
    s["breadth"] = (s["breadth"] * 100).round(0).astype(int).astype(str) + "%"
    s["score"] = s["score"].round(2)
    out += [md_table(s.rename(columns={"ret63": "3m return", "ret126": "6m return", "breadth": "% above 200DMA"})), ""]

    out += ["## Validated setups", "",
            "Only setups that passed research mode (see research.md) are scanned. "
            f"R after {COST_PCT}% costs; '{MAX_OPEN}-slot' = account holding at most {MAX_OPEN} trades, strongest momentum first.", ""]
    if validated:
        out += [md_table(pd.DataFrame([{
            "setup": v["key"], "exit": v["exit"], "stop": f"{v['stop_atr']}xATR",
            "train trades": v["train"]["n"], "train avgR": v["train"]["avg_r"],
            "test trades": v["test"]["n"], "test avgR": v["test"]["avg_r"],
            f"{MAX_OPEN}-slot test avgR": v["test"]["taken_avg_r"], "test DD (R)": v["test"]["max_dd_r"],
            "researched": v["generated"]} for v in validated])), ""]
        out += ["Exit rules:", ""] + [f"- **{e}**: {EXIT_RULES[e]}" for e in sorted({v['exit'] for v in validated})] + [""]
    else:
        out += ["**None passed.** No setup has a validated edge right now: sit out.", ""]

    if plans.empty:
        out += ["## Trade plans", "", "No live setups today. Top-ranked watchlist:", ""]
        w = df.sort_values("score", ascending=False).head(top)[["sym", "sector", "score", "close"]]
        out += [md_table(w.round(2)), ""]
    else:
        out += ["## Trade plans", "", md_table(plans), ""]
        out += ["## Fundamentals", ""]
        for sym in plans["symbol"].unique():
            out += [f"### {sym}", "", fund_summary(funds[sym]), ""]
        if notes:
            out += ["## Claude analysis", ""]
            for i, text in notes.items():
                p = plans.loc[i]
                out += [f"### {p['symbol']} ({p['setup']})", "", text, ""]

    if rejected:
        out += ["## Rejected on fundamentals", "", "| symbol | setup | red flags |", "|---|---|---|"]
        out += [f"| {sym} | {setup} | {why} |" for sym, setup, why in rejected]
        out.append("")

    out += ["---", f"Rules: max {MAX_OPEN} open trades, {RISK_PCT}% risk each; exit per the setup's exit rule above. "
            "Not investment advice."]
    with open("report.md", "w") as f:
        f.write("\n".join(out))
