"""Prices from yfinance: NIFTY 500 universe, indicators, setups and filters."""
import io
import warnings
import pandas as pd
import numpy as np
import requests
import yfinance as yf
warnings.filterwarnings("ignore")
from config import HISTORY_YEARS, MACRO, TOP_SECTORS


FALLBACK = {  # used if NSE list download fails
    "RELIANCE": "Oil Gas", "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT",
    "HDFCBANK": "Banks", "ICICIBANK": "Banks", "SBIN": "Banks", "KOTAKBANK": "Banks", "AXISBANK": "Banks",
    "INDUSINDBK": "Banks", "BAJFINANCE": "Finance", "BAJAJFINSV": "Finance", "SHRIRAMFIN": "Finance",
    "LT": "Capital Goods", "SIEMENS": "Capital Goods", "ABB": "Capital Goods", "BEL": "Defence", "HAL": "Defence",
    "BHARTIARTL": "Telecom", "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
    "M&M": "Auto", "MARUTI": "Auto", "BAJAJ-AUTO": "Auto", "EICHERMOT": "Auto", "HEROMOTOCO": "Auto",
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma", "DIVISLAB": "Pharma", "APOLLOHOSP": "Healthcare",
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals", "VEDL": "Metals", "COALINDIA": "Mining",
    "NTPC": "Power", "POWERGRID": "Power", "TATAPOWER": "Power", "ADANIPOWER": "Power",
    "ULTRACEMCO": "Cement", "GRASIM": "Cement", "AMBUJACEM": "Cement",
    "ASIANPAINT": "Consumer", "TITAN": "Consumer", "TRENT": "Retail", "DMART": "Retail",
    "ONGC": "Oil Gas", "BPCL": "Oil Gas", "IOC": "Oil Gas", "DLF": "Realty", "GODREJPROP": "Realty",
}


def load_universe():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        return dict(zip(df["Symbol"], df["Industry"]))
    except Exception as e:
        print(f"[warn] NIFTY 500 list unavailable ({e}); using built-in list")
        return FALLBACK


def yf_download(*args, **kwargs):
    """yf.download with warnings off: yfinance re-adds its own warning filter during downloads,
    which lets pandas' inplace deprecation warnings from yfinance's code through."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return yf.download(*args, **kwargs)


def download(symbols):
    tickers = [s + ".NS" for s in symbols]
    data = yf_download(tickers, period=f"{HISTORY_YEARS}y", interval="1d", group_by="ticker",
                      auto_adjust=True, progress=False, threads=True)
    out = {}
    for s, t in zip(symbols, tickers):
        try:
            d = data[t].dropna()
            if len(d) > 260:
                out[s] = d
        except KeyError:
            pass
    return out


# ---------- indicators & setups ----------
def enrich(d):
    d = d.copy()
    c = d["Close"]
    d["ema20"] = c.ewm(span=20).mean()
    d["sma50"] = c.rolling(50).mean()
    d["sma200"] = c.rolling(200).mean()
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - c.shift()).abs(), (d["Low"] - c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    d["hi252"] = d["High"].rolling(252).max().shift(1)
    d["vol50"] = d["Volume"].rolling(50).mean()
    d["ret63"] = c.pct_change(63)
    d["ret126"] = c.pct_change(126)
    d["turnover_cr"] = (c * d["Volume"]).rolling(20).mean() / 1e7
    uptrend = (c > d["sma50"]) & (d["sma50"] > d["sma200"])
    # Setup A: 52-week-high breakout on 1.5x volume
    d["breakout"] = (c > d["hi252"]) & (d["Volume"] > 1.5 * d["vol50"]) & uptrend
    # Setup B: pullback to 20 EMA inside an uptrend, closing back up
    d["pullback"] = uptrend & (d["Low"] <= d["ema20"] * 1.01) & (c > d["ema20"]) & (c > d["Open"]) \
        & (c.pct_change(10) < 0)
    return d


def load_nifty():
    n = yf_download("^NSEI", period=f"{HISTORY_YEARS}y", auto_adjust=True, progress=False)
    if isinstance(n.columns, pd.MultiIndex):
        n.columns = n.columns.get_level_values(0)
    n = n.dropna()
    n["sma200"] = n["Close"].rolling(200).mean()
    n["sma50"] = n["Close"].rolling(50).mean()
    n["ret63"] = n["Close"].pct_change(63)
    return n


def load_macro():
    """Daily closes of the market prices news moves (VIX, crude, rupee, US yield, dollar). Empty on failure."""
    tickers = {"vix": "^INDIAVIX", "crude": "BZ=F", "usdinr": "INR=X", "us10y": "^TNX", "dxy": "DX-Y.NYB"}
    try:
        m = yf_download(list(tickers.values()), period=f"{HISTORY_YEARS}y", auto_adjust=True, progress=False)["Close"]
        m = m.rename(columns={v: k for k, v in tickers.items()})
    except Exception as e:
        print(f"[warn] macro data unavailable ({e}); macro filters off")
        return pd.DataFrame()
    m.index = pd.to_datetime(m.index).tz_localize(None).normalize()
    m = m.ffill()
    # global markets close after NSE, so use the previous day's value for everything but India VIX
    glob = [c for c in m.columns if c != "vix"]
    m[glob] = m[glob].shift(1)
    return m


def macro_filters(m, idx):
    """Market-wide boolean filters on the NSE calendar `idx`. True = calm; False also when data is missing."""
    if m.empty:
        return pd.DataFrame(False, index=idx, columns=["vix_calm", "crude_calm", "inr_stable", "yields_calm", "dollar_calm"])
    m = m.reindex(m.index.union(idx)).ffill().reindex(idx)
    n = MACRO["lookback"]
    return pd.DataFrame({
        # India VIX at or below its 1-year median: no fear spike
        "vix_calm": m["vix"] <= m["vix"].rolling(252, min_periods=126).median(),
        # Brent not up sharply: oil shocks (Middle East, supply) hurt India, a big importer
        "crude_calm": m["crude"].pct_change(n) * 100 < MACRO["crude_up_pct"],
        # rupee not weakening fast: a proxy for foreign money leaving
        "inr_stable": m["usdinr"].pct_change(n) * 100 < MACRO["inr_up_pct"],
        # US 10-year yield (in %) not jumping: pulls FII money out of emerging markets
        "yields_calm": m["us10y"].diff(n) < MACRO["us10y_up_pts"],
        # dollar index not surging: global risk-off
        "dollar_calm": m["dxy"].pct_change(n) * 100 < MACRO["dxy_up_pct"],
    }, index=idx).fillna(False)


def add_filters(frames, uni, nifty, macro=None):
    """Add boolean filter columns to every stock frame. Each uses only data available on that day."""
    close = pd.DataFrame({s: d["Close"] for s, d in frames.items()})
    sma200 = pd.DataFrame({s: d["sma200"] for s, d in frames.items()})
    ret63 = pd.DataFrame({s: d["ret63"] for s, d in frames.items()})
    # market breadth: share of stocks above their 200-day average
    breadth = (close > sma200).sum(axis=1) / sma200.notna().sum(axis=1).replace(0, np.nan)
    # sector rank per day by median 3-month return of its members
    sec_ret = ret63.T.groupby(pd.Series(uni)).median().T
    sec_rank = sec_ret.rank(axis=1, ascending=False)
    market_up = (nifty["Close"] > nifty["sma200"]).reindex(close.index).ffill().fillna(False)
    mkt_weak = (nifty["Close"] < nifty["sma50"]).reindex(close.index).ffill().fillna(False)
    n_ret63 = nifty["ret63"].reindex(close.index).ffill()
    mf = macro_filters(pd.DataFrame() if macro is None else macro, close.index)
    for s, d in frames.items():
        idx = d.index
        d["market_up"] = market_up.reindex(idx).astype(bool).values
        d["mkt_weak"] = mkt_weak.reindex(idx).fillna(False).astype(bool).values
        d["breadth_ok"] = (breadth.reindex(idx) > 0.5).values
        d["sector_top"] = (sec_rank[uni[s]].reindex(idx) <= TOP_SECTORS).values if uni[s] in sec_rank else False
        d["rs_strong"] = (d["ret63"] > n_ret63.reindex(idx)).values
        natr = d["atr"] / d["Close"]  # volatility contraction: range tighter than its 6-month norm, before today
        d["vol_contraction"] = (natr.shift(1) < natr.rolling(126).median().shift(1)).values
        delta = d["Close"].diff()  # oversold: 2-day RSI dipped below 15 in the last 3 days
        up, dn = delta.clip(lower=0).ewm(alpha=0.5).mean(), (-delta.clip(upper=0)).ewm(alpha=0.5).mean()
        rsi2 = 100 - 100 / (1 + up / dn.replace(0, np.nan))
        d["oversold"] = (rsi2.rolling(3).min() < 15).values
        for f in mf.columns:
            d[f] = mf[f].reindex(idx).fillna(False).astype(bool).values
