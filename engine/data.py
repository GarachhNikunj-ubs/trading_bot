import os
import pandas as pd
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def load_or_fetch_data(symbol: str = "^NSEI", period: str = "60d", interval: str = "15m") -> pd.DataFrame:
    """
    Fetches historical OHLCV data via yfinance and caches it locally as CSV.
    Ensures standard column names: open, high, low, close, volume.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    clean_sym = symbol.replace("^", "").replace(".", "_")
    cache_path = os.path.join(DATA_DIR, f"{clean_sym}_{interval}_{period}.csv")

    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df

    print(f"Fetching {symbol} ({interval}, {period}) from yfinance...")
    raw = yf.download(symbol, period=period, interval=interval, progress=False)

    if raw.empty:
        raise ValueError(f"No data returned for symbol {symbol}")

    # Handle MultiIndex columns if returned by yfinance
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0].lower() for col in raw.columns]
    else:
        raw.columns = [col.lower() for col in raw.columns]

    df = raw[['open', 'high', 'low', 'close', 'volume']].copy()
    df = df.dropna()

    df.to_csv(cache_path)
    print(f"Saved {len(df)} bars to {cache_path}")
    return df
