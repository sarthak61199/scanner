"""Settings: capital, risk, research pass rules, paths. Loads .env."""
import os
import warnings


warnings.filterwarnings("ignore")


try:  # load ANTHROPIC_API_KEY etc. from .env next to this script
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass


CAPITAL = 100000        # trading capital, Rs


RISK_PCT = 1.0          # % of capital risked per trade


MIN_TURNOVER_CR = 5     # min avg daily turnover, Rs crore


TOP = 15                # max trade plans shown


HISTORY_YEARS = 5       # years of daily prices downloaded (first ~1y is indicator warm-up)


TEST_MONTHS = 12        # most recent months held out as the test period


TOP_SECTORS = 5         # 'sector_top' filter: sector ranked in the top N that day


COST_PCT = 0.25         # round-trip costs (brokerage, STT, stamp, slippage), % of entry


SETUPS = ["breakout", "pullback", "earnings_gap"]


FILTERS = ["market_up", "breadth_ok", "sector_top", "rs_strong", "vol_contraction", "oversold",
           "deliv_high", "accumulation", "deliv_not_low", "big_buyer",
           "vix_calm", "crude_calm", "inr_stable", "yields_calm", "dollar_calm"]


# ---------- macro filters: market prices that react to news (geopolitics, policy, global risk) ----------
MACRO = {"lookback": 20,       # trading days over which each change is measured
         "crude_up_pct": 10,   # crude_calm: Brent up less than this %
         "inr_up_pct": 1.5,    # inr_stable: USD/INR up less than this % (rupee weakening)
         "us10y_up_pts": 0.3,  # yields_calm: US 10-year yield up less than this many % points
         "dxy_up_pct": 2}      # dollar_calm: dollar index up less than this %


# ---------- NSE history: delivery %, bulk/block deals, results dates (cached in nse_data/) ----------
NSE_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nse_data")


EARNINGS_GAP_PCT = 4    # earnings_gap setup: min % rise on the results reaction day


BIG_BUYER_CR = 1        # big_buyer filter: min net buying by a single client, Rs crore


BIG_BUYER_DAYS = 10     # ...within this many trading days


EXITS = ["fixed", "breakeven", "ema_trail", "chandelier", "fixed+mkt", "chandelier+mkt"]


STOP_WIDTHS = [1.5, 2.0, 3.0]


VALIDATED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validated_setups.json")


RESEARCH_EXITS = ["fixed", "breakeven", "ema_trail", "chandelier"]   # +mkt exits already shown to hurt


MIN_TRAIN_N, MIN_TRAIN_R = 100, 0.10    # pass rule 1


MIN_TEST_N, MIN_TEST_R = 30, 0.0        # pass rule 2


MAX_TEST_DD_R = 15                      # pass rule 4, on a portfolio holding at most MAX_OPEN trades


MAX_OPEN = 5                            # open positions at once (1% risk each)


# ---------- fundamentals (NSE integrated filings + shareholding) ----------
FUND_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fund_cache")


MAX_PLEDGE = 20      # % of promoter shares pledged


MAX_STAKE_DROP = 2   # promoter stake fall over ~1 year, % points


MAX_DE = 2.0         # debt/equity, ignored for financials


MAX_PDFS = 3        # PDFs read per stock


PDF_CHARS = 4000    # text kept per PDF


# ---------- Mint news (market mood: context only, not a validated signal) ----------
NEWS_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_cache")  # feeds have no history: back this folder up


NEWS_FEEDS = ["markets", "companies", "industry", "news", "politics"]


MOOD_DAYS = 3       # days of headlines in the market-mood summary
