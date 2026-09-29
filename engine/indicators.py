import numpy as np
import pandas as pd

def calculate_ema(series: pd.Series, length: int) -> pd.Series:
    """Pine Script ta.ema equivalent."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_sma(series: pd.Series, length: int) -> pd.Series:
    """Pine Script ta.sma equivalent."""
    return series.rolling(window=length).mean()

def calculate_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Pine Script ta.rsi equivalent (Wilder's RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Pine Script ta.atr equivalent (Wilder's smoothing of True Range)."""
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/length, adjust=False).mean()
    return atr

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    Pine Script ta.supertrend(multiplier, period) equivalent.
    Returns:
        stVal (pd.Series): The Supertrend line value.
        stDir (pd.Series): Direction flag (-1 for Bullish, +1 for Bearish, matching Pine Script logic:
                           ta.crossunder(stDir, 0) = Bullish flip, ta.crossover(stDir, 0) = Bearish flip).
    """
    atr = calculate_atr(df, period)
    hl2 = (df['high'] + df['low']) / 2.0
    
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    
    final_upper = pd.Series(index=df.index, dtype='float64')
    final_lower = pd.Series(index=df.index, dtype='float64')
    supertrend = pd.Series(index=df.index, dtype='float64')
    direction = pd.Series(index=df.index, dtype='int64') # -1: Bullish, 1: Bearish
    
    close = df['close']
    
    curr_upper = basic_upper.iloc[0] if len(basic_upper) > 0 else 0
    curr_lower = basic_lower.iloc[0] if len(basic_lower) > 0 else 0
    curr_dir = 1
    
    for i in range(len(df)):
        if i == 0:
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            supertrend.iloc[i] = basic_upper.iloc[i]
            direction.iloc[i] = 1
            continue
            
        c_prev = close.iloc[i-1]
        c = close.iloc[i]
        
        # Upper band
        if basic_upper.iloc[i] < curr_upper or c_prev > curr_upper:
            curr_upper = basic_upper.iloc[i]
        final_upper.iloc[i] = curr_upper
        
        # Lower band
        if basic_lower.iloc[i] > curr_lower or c_prev < curr_lower:
            curr_lower = basic_lower.iloc[i]
        final_lower.iloc[i] = curr_lower
        
        # Direction
        if curr_dir == 1 and c > curr_upper:
            curr_dir = -1 # Switched to Bullish
        elif curr_dir == -1 and c < curr_lower:
            curr_dir = 1  # Switched to Bearish
            
        direction.iloc[i] = curr_dir
        supertrend.iloc[i] = curr_lower if curr_dir == -1 else curr_upper
        
    return supertrend, direction

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Pine Script ta.vwap(hlc3) equivalent.
    Computes daily/session cumulative VWAP if date column exists, or cumulative across series.
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    vol = df['volume'] if 'volume' in df.columns and (df['volume'] > 0).any() else pd.Series(1.0, index=df.index)
    
    # Check if index has date
    if isinstance(df.index, pd.DatetimeIndex):
        cum_vol_price = (typical_price * vol).groupby(df.index.date).cumsum()
        cum_vol = vol.groupby(df.index.date).cumsum()
        vwap = cum_vol_price / cum_vol.replace(0, np.nan)
        return vwap.ffill()
    else:
        cum_vol_price = (typical_price * vol).cumsum()
        cum_vol = vol.cumsum()
        vwap = cum_vol_price / cum_vol.replace(0, np.nan)
        return vwap.ffill()

def calculate_bollinger_bands(series: pd.Series, length: int = 20, mult: float = 2.0):
    """Pine Script ta.bb(close, 20, 2.0). Returns basis, upper, lower, bbWidth."""
    basis = series.rolling(window=length).mean()
    dev = series.rolling(window=length).std(ddof=0) * mult
    upper = basis + dev
    lower = basis - dev
    bb_width = (upper - lower) / basis.replace(0, np.nan)
    return basis, upper, lower, bb_width

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Pine Script ta.macd(close, 12, 26, 9). Returns macdLine, signalLine, hist."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calculate_pivots(df: pd.DataFrame, left: int = 5, right: int = 5):
    """
    Pine Script ta.pivothigh(high, left, right) and ta.pivotlow(low, left, right).
    Returns series of pivot levels (placed at index of bar where pivot is confirmed, i.e., index i with value high[i-right]).
    """
    high = df['high'].values
    low = df['low'].values
    n = len(df)
    
    ph = [np.nan] * n
    pl = [np.nan] * n
    
    for i in range(left + right, n):
        idx = i - right
        # check high
        val_h = high[idx]
        is_ph = True
        for l in range(idx - left, idx):
            if high[l] >= val_h:
                is_ph = False
                break
        if is_ph:
            for r in range(idx + 1, i + 1):
                if high[r] >= val_h:
                    is_ph = False
                    break
        if is_ph:
            ph[i] = val_h
            
        # check low
        val_l = low[idx]
        is_pl = True
        for l in range(idx - left, idx):
            if low[l] <= val_l:
                is_pl = False
                break
        if is_pl:
            for r in range(idx + 1, i + 1):
                if low[r] <= val_l:
                    is_pl = False
                    break
        if is_pl:
            pl[i] = val_l
            
    return pd.Series(ph, index=df.index), pd.Series(pl, index=df.index)
