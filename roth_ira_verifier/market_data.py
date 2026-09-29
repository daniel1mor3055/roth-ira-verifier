"""
Fetches market data from Yahoo Finance for fund return verification.

Retrieves S&P 500 price index (^GSPC), SPY ETF (total return proxy),
and USD/ILS exchange rate for the given period.
"""

import sys
import datetime
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

INDEX_TICKERS = {
    "S&P 500": {"price": "^GSPC", "total_return": "SPY"},
}

FX_TICKER = "USDILS=X"


from typing import Tuple

def _resolve_tickers(track_name: str) -> Tuple[str, str]:
    """Map a track name to Yahoo Finance tickers (price, total_return)."""
    name_upper = track_name.upper()
    for key, tickers in INDEX_TICKERS.items():
        if key.upper().replace(" ", "") in name_upper.replace(" ", ""):
            return tickers["price"], tickers["total_return"]
    if "S&P" in name_upper or "SP500" in name_upper or "S&P500" in name_upper:
        return "^GSPC", "SPY"
    raise ValueError(
        f"Unknown track '{track_name}'. Supported: {list(INDEX_TICKERS.keys())}"
    )


def fetch_market_data(
    track_name: str,
    period_start: datetime.date,
    period_end: datetime.date,
    buffer_days: int = 7,
) -> pd.DataFrame:
    """
    Fetch daily market data for the index and USD/ILS exchange rate.

    Returns a DataFrame indexed by date with columns:
        index_price, total_return_price, usdils,
        index_ils, total_return_ils,
        index_ils_ret, total_return_ils_ret
    """
    price_ticker, tr_ticker = _resolve_tickers(track_name)

    fetch_start = (period_start - datetime.timedelta(days=buffer_days)).isoformat()
    fetch_end = (period_end + datetime.timedelta(days=buffer_days)).isoformat()

    def dl(ticker: str) -> pd.DataFrame:
        df = yf.download(ticker, start=fetch_start, end=fetch_end, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        if df.empty:
            sys.exit(f"ERROR: Could not fetch {ticker} data.")
        df.index = pd.to_datetime(df.index).date
        return df

    print(f"  Fetching {price_ticker} (price index) ...")
    idx = dl(price_ticker)

    print(f"  Fetching {tr_ticker} (total return proxy) ...")
    tr = dl(tr_ticker)

    print(f"  Fetching {FX_TICKER} (USD/ILS) ...")
    fx = dl(FX_TICKER)

    data = (
        idx[["Close"]].rename(columns={"Close": "index_price"})
        .join(tr[["Close"]].rename(columns={"Close": "total_return_price"}), how="outer")
        .join(fx[["Close"]].rename(columns={"Close": "usdils"}), how="outer")
        .sort_index()
        .ffill()
        .dropna()
    )

    data["index_ils"] = data["index_price"] * data["usdils"]
    data["total_return_ils"] = data["total_return_price"] * data["usdils"]
    data["index_ils_ret"] = data["index_ils"].pct_change()
    data["total_return_ils_ret"] = data["total_return_ils"].pct_change()

    print(f"  Data range: {data.index[0]} -> {data.index[-1]}  ({len(data)} trading days)")
    return data


def nearest_trading_day(
    index, target: datetime.date, direction: str = "on_or_before"
) -> datetime.date:
    """Find the nearest trading day in the index to the target date."""
    dates = sorted(index)
    if target in dates:
        return target
    if direction == "on_or_before":
        candidates = [d for d in dates if d <= target]
        return max(candidates) if candidates else min(dates)
    else:
        candidates = [d for d in dates if d >= target]
        return min(candidates) if candidates else max(dates)
