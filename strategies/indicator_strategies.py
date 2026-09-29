import numpy as np
import pandas as pd
from engine.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_supertrend,
    calculate_vwap,
    calculate_bollinger_bands,
    calculate_macd
)

def strategy_01_ema_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 01: EMA 9/21 + RSI Momentum Trend System"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    ema_fast = calculate_ema(close, 9)
    ema_slow = calculate_ema(close, 21)
    rsi_val = calculate_rsi(close, 14)
    atr_val = calculate_atr(df, 14)

    ema_cross_up = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
    ema_cross_dn = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

    signals['long_entry'] = ema_cross_up & (rsi_val > 50) & (close > ema_fast)
    signals['short_entry'] = ema_cross_dn & (rsi_val < 50) & (close < ema_fast)
    signals['long_exit'] = False
    signals['short_exit'] = False

    signals['stop_loss'] = np.where(
        signals['long_entry'], close - 1.5 * atr_val,
        np.where(signals['short_entry'], close + 1.5 * atr_val, np.nan)
    )
    signals['take_profit'] = np.where(
        signals['long_entry'], close + 3.0 * atr_val,
        np.where(signals['short_entry'], close - 3.0 * atr_val, np.nan)
    )
    return signals

def strategy_02_ema_trend_following(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 02: EMA 20/50 Trend Following System"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']

    e20 = calculate_ema(close, 20)
    e50 = calculate_ema(close, 50)
    trend_up = e20 > e50
    trend_dn = e20 < e50

    lowest_5 = low.rolling(5).min()
    highest_5 = high.rolling(5).max()

    pullback_long = trend_up & (low <= e20) & (close > e20)
    pullback_short = trend_dn & (high >= e20) & (close < e20)

    signals['long_entry'] = pullback_long
    signals['short_entry'] = pullback_short
    signals['long_exit'] = False
    signals['short_exit'] = False

    signals['stop_loss'] = np.where(
        pullback_long, lowest_5,
        np.where(pullback_short, highest_5, np.nan)
    )
    signals['take_profit'] = np.where(
        pullback_long, close + (close - lowest_5) * 2.0,
        np.where(pullback_short, close - (highest_5 - close) * 2.0, np.nan)
    )
    return signals

def strategy_03_supertrend_ema(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 03: Supertrend + 200 EMA Regime Filter"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    st_val, st_dir = calculate_supertrend(df, period=10, multiplier=3.0)
    ema200 = calculate_ema(close, 200)

    # st_dir flips from 1 (bear) to -1 (bull)
    bull_flip = (st_dir == -1) & (st_dir.shift(1) == 1)
    bear_flip = (st_dir == 1) & (st_dir.shift(1) == -1)

    signals['long_entry'] = bull_flip & (close > ema200)
    signals['short_entry'] = bear_flip & (close < ema200)

    signals['long_exit'] = (st_dir > 0)
    signals['short_exit'] = (st_dir < 0)

    signals['stop_loss'] = np.nan
    signals['take_profit'] = np.nan
    return signals

def strategy_04_vwap_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 04: VWAP + RSI Intraday Reversion/Continuation"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']
    vwap = calculate_vwap(df)
    rsi = calculate_rsi(close, 14)

    bullish_bounce = (close > vwap) & (low <= vwap) & (rsi > 50)
    bearish_bounce = (close < vwap) & (high >= vwap) & (rsi < 50)

    signals['long_entry'] = bullish_bounce
    signals['short_entry'] = bearish_bounce
    signals['long_exit'] = False
    signals['short_exit'] = False

    sl_long = vwap * 0.997
    tp_long = close + (close - sl_long) * 2.0
    sl_short = vwap * 1.003
    tp_short = close - (sl_short - close) * 2.0

    signals['stop_loss'] = np.where(bullish_bounce, sl_long, np.where(bearish_bounce, sl_short, np.nan))
    signals['take_profit'] = np.where(bullish_bounce, tp_long, np.where(bearish_bounce, tp_short, np.nan))
    return signals

def strategy_05_bollinger_squeeze(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 05: Bollinger Band Breakout (Volatility Squeeze)"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    basis, upper, lower, bb_width = calculate_bollinger_bands(close, 20, 2.0)

    lowest_bb_width = bb_width.rolling(20).min().shift(1)
    is_squeezed = bb_width < (lowest_bb_width * 1.15)

    signals['long_entry'] = is_squeezed & (close > upper)
    signals['short_entry'] = is_squeezed & (close < lower)
    signals['long_exit'] = False
    signals['short_exit'] = False

    signals['stop_loss'] = np.where(
        signals['long_entry'] | signals['short_entry'], basis, np.nan
    )
    signals['take_profit'] = np.where(
        signals['long_entry'], close + (close - basis) * 2.5,
        np.where(signals['short_entry'], close - (basis - close) * 2.5, np.nan)
    )
    return signals

def strategy_06_donchian_breakout(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 06: Donchian Channel Breakout (Turtle Model)"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']

    entry_high = high.shift(1).rolling(20).max()
    entry_low = low.shift(1).rolling(20).min()
    exit_high = high.shift(1).rolling(10).max()
    exit_low = low.shift(1).rolling(10).min()

    signals['long_entry'] = close > entry_high
    signals['short_entry'] = close < entry_low
    signals['long_exit'] = close < exit_low
    signals['short_exit'] = close > exit_high

    signals['stop_loss'] = np.nan
    signals['take_profit'] = np.nan
    return signals

def strategy_07_orb(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 07: Opening Range Breakout (ORB 15-Minute)"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    long_entry = [False] * n
    short_entry = [False] * n
    long_exit = [False] * n
    short_exit = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    if isinstance(df.index, pd.DatetimeIndex):
        grouped = df.groupby(df.index.date)
        for date, group in grouped:
            if len(group) < 3:
                continue
            # Session range defined by first bar(s) e.g. 9:15-9:30 (first 1-2 bars depending on interval)
            orb_bar = group.iloc[0]
            orb_high = orb_bar['high']
            orb_low = orb_bar['low']

            for idx in group.index[1:]:
                i = df.index.get_loc(idx)
                c_close = df.at[idx, 'close']
                c_time = idx.time()

                if c_time.hour >= 15 or (c_time.hour == 14 and c_time.minute >= 45):
                    long_exit[i] = True
                    short_exit[i] = True
                    continue

                if c_close > orb_high:
                    long_entry[i] = True
                    sl[i] = orb_low
                    tp[i] = c_close + (c_close - orb_low) * 1.5
                elif c_close < orb_low:
                    short_entry[i] = True
                    sl[i] = orb_high
                    tp[i] = c_close - (orb_high - c_close) * 1.5
    else:
        # Fallback for non-datetime
        lookback = 12
        r_high = df['high'].rolling(lookback).max().shift(1)
        r_low = df['low'].rolling(lookback).min().shift(1)
        long_entry = (df['close'] > r_high).tolist()
        short_entry = (df['close'] < r_low).tolist()
        sl = r_low.tolist()
        tp = (df['close'] + (df['close'] - r_low) * 1.5).tolist()

    signals['long_entry'] = long_entry
    signals['short_entry'] = short_entry
    signals['long_exit'] = long_exit
    signals['short_exit'] = short_exit
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_08_macd_ema(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 08: MACD Histogram Velocity + EMA 50 Filter"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    macd_line, signal_line, hist = calculate_macd(close, 12, 26, 9)
    ema50 = calculate_ema(close, 50)
    atr = calculate_atr(df, 14)

    macd_cross_up = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    macd_cross_dn = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))

    long_valid = macd_cross_up & (hist > hist.shift(1)) & (close > ema50)
    short_valid = macd_cross_dn & (hist < hist.shift(1)) & (close < ema50)

    signals['long_entry'] = long_valid
    signals['short_entry'] = short_valid
    signals['long_exit'] = False
    signals['short_exit'] = False

    signals['stop_loss'] = np.where(
        long_valid, close - 2.0 * atr,
        np.where(short_valid, close + 2.0 * atr, np.nan)
    )
    signals['take_profit'] = np.where(
        long_valid, close + 3.0 * atr,
        np.where(short_valid, close - 3.0 * atr, np.nan)
    )
    return signals

def strategy_09_rsi_mean_reversion(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 09: RSI Statistical Mean Reversion (7-period RSI < 25 / > 75)"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    rsi = calculate_rsi(close, 7)

    signals['long_entry'] = (rsi < 25)
    signals['short_entry'] = (rsi > 75)
    signals['long_exit'] = (rsi >= 50)
    signals['short_exit'] = (rsi <= 50)

    signals['stop_loss'] = np.nan
    signals['take_profit'] = np.nan
    return signals

def strategy_10_multi_confluence(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 10: Multi-Indicator Confluence (EMA, RSI, VWAP, Supertrend)"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    e20 = calculate_ema(close, 20)
    st_val, st_dir = calculate_supertrend(df, period=10, multiplier=2.0)
    vwap = calculate_vwap(df)
    rsi = calculate_rsi(close, 14)
    atr = calculate_atr(df, 14)

    bull_confluence = (close > e20) & (st_dir < 0) & (close > vwap) & (rsi > 55)
    bear_confluence = (close < e20) & (st_dir > 0) & (close < vwap) & (rsi < 45)

    signals['long_entry'] = bull_confluence
    signals['short_entry'] = bear_confluence
    signals['long_exit'] = False
    signals['short_exit'] = False

    signals['stop_loss'] = np.where(
        bull_confluence, close - 1.5 * atr,
        np.where(bear_confluence, close + 1.5 * atr, np.nan)
    )
    signals['take_profit'] = np.where(
        bull_confluence, close + 3.0 * atr,
        np.where(bear_confluence, close - 3.0 * atr, np.nan)
    )
    return signals
