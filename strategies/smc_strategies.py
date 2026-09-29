import numpy as np
import pandas as pd
from engine.indicators import calculate_atr, calculate_pivots

def strategy_11_sweep_choch(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 11: Liquidity Sweep + Change of Character (CHOCH)"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    ph, pl = calculate_pivots(df, 5, 5)

    long_entry = [False] * n
    short_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    s_low = np.nan
    s_high = np.nan
    swept_l = False
    swept_h = False

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    for i in range(5, n):
        if not np.isnan(pl.iloc[i]):
            s_low = pl.iloc[i]
        if not np.isnan(ph.iloc[i]):
            s_high = ph.iloc[i]

        if not np.isnan(s_low) and low[i] < s_low and close[i] > s_low:
            swept_l = True
        if not np.isnan(s_high) and high[i] > s_high and close[i] < s_high:
            swept_h = True

        recent_high_5 = max(high[max(0, i-5):i]) if i >= 1 else high[0]
        recent_low_5 = min(low[max(0, i-5):i]) if i >= 1 else low[0]

        choch_l = swept_l and (close[i] > recent_high_5)
        choch_s = swept_h and (close[i] < recent_low_5)

        if choch_l:
            long_entry[i] = True
            sl[i] = s_low if not np.isnan(s_low) else low[i] * 0.99
            tp[i] = close[i] + (close[i] - sl[i]) * 2.0
            swept_l = False

        if choch_s:
            short_entry[i] = True
            sl[i] = s_high if not np.isnan(s_high) else high[i] * 1.01
            tp[i] = close[i] - (sl[i] - close[i]) * 2.0
            swept_h = False

    signals['long_entry'] = long_entry
    signals['short_entry'] = short_entry
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_12_ob_bos(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 12: Order Block Retest + Break of Structure (BOS)"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    long_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_p = df['open'].values

    ob_top = np.nan
    ob_bottom = np.nan

    for i in range(11, n):
        prior_highest_10 = max(high[i-11:i-1])
        bos_bull = close[i] > prior_highest_10

        if bos_bull and close[i-1] < open_p[i-1]:
            ob_top = open_p[i-1]
            ob_bottom = low[i-1]

        if not np.isnan(ob_top) and (low[i] <= ob_top and close[i] >= ob_bottom):
            long_entry[i] = True
            sl[i] = ob_bottom
            tp[i] = close[i] + (close[i] - ob_bottom) * 2.5
            ob_top = np.nan

    signals['long_entry'] = long_entry
    signals['short_entry'] = False
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_13_fvg_bos(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 13: Fair Value Gap (FVG) Retest + Structural BOS"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    long_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n
    atr = calculate_atr(df, 14).values

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    fvg_high = np.nan
    fvg_low = np.nan

    for i in range(9, n):
        bullish_fvg = (low[i] > high[i-2]) and (close[i-1] > high[i-2])
        highest_8 = max(high[i-9:i-1])

        if bullish_fvg and close[i] > highest_8:
            fvg_high = low[i]
            fvg_low = high[i-2]

        if not np.isnan(fvg_high) and (low[i] <= fvg_high and close[i] >= fvg_low):
            long_entry[i] = True
            curr_atr = atr[i] if not np.isnan(atr[i]) else (close[i] * 0.01)
            sl[i] = fvg_low - curr_atr * 0.5
            tp[i] = close[i] + (close[i] - fvg_low) * 2.5
            fvg_high = np.nan

    signals['long_entry'] = long_entry
    signals['short_entry'] = False
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_14_sweep_ob(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 14: Liquidity Sweep + Order Block Execution"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    ph, pl = calculate_pivots(df, 7, 7)

    long_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    swing_ref = np.nan
    ob_level = np.nan

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_p = df['open'].values

    for i in range(14, n):
        if not np.isnan(pl.iloc[i]):
            swing_ref = pl.iloc[i]

        sweep_done = not np.isnan(swing_ref) and (low[i] < swing_ref and close[i] > swing_ref)
        if sweep_done and close[i] > open_p[i]:
            ob_level = low[i]

        if not np.isnan(ob_level) and (low[i] <= ob_level and close[i] > ob_level):
            long_entry[i] = True
            sl[i] = ob_level * 0.998
            tp[i] = close[i] + (close[i] - ob_level) * 3.0
            ob_level = np.nan

    signals['long_entry'] = long_entry
    signals['short_entry'] = False
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_15_sweep_fvg(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 15: Liquidity Sweep + Fair Value Gap (FVG) Retest"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    ph, pl = calculate_pivots(df, 6, 6)

    short_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    prev_high = np.nan
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    for i in range(12, n):
        if not np.isnan(ph.iloc[i]):
            prev_high = ph.iloc[i]

        swept = not np.isnan(prev_high) and (high[i] > prev_high and close[i] < prev_high)
        bear_fvg = (high[i] < low[i-2]) and (close[i-1] < low[i-2])

        if swept and bear_fvg:
            short_entry[i] = True
            sl[i] = high[i-1]
            tp[i] = close[i] - (high[i-1] - close[i]) * 2.5

    signals['long_entry'] = False
    signals['short_entry'] = short_entry
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_16_bos_continuation(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 16: Break of Structure (BOS) Pullback Continuation"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    long_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    leg_low = np.nan
    leg_high = np.nan

    for i in range(16, n):
        h_level = max(high[i-16:i-1])
        bos = (close[i] > h_level) and (close[i-1] <= h_level)

        if bos:
            leg_low = min(low[i-10:i])
            leg_high = high[i]

        if not np.isnan(leg_high):
            fib_50 = leg_high - (leg_high - leg_low) * 0.5
            fib_pullback = (low[i] <= fib_50) and (close[i] > leg_low)
            if fib_pullback:
                long_entry[i] = True
                sl[i] = leg_low
                tp[i] = close[i] + (close[i] - leg_low) * 2.0
                leg_high = np.nan

    signals['long_entry'] = long_entry
    signals['short_entry'] = False
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_17_amd(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 17: Power of 3 (AMD: Accumulation - Manipulation - Distribution)"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    long_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    low = df['low'].values
    close = df['close'].values

    for i in range(13, n):
        acc_range_low = min(low[i-13:i-1])
        manipulation_low = (low[i] < acc_range_low) and (close[i] > acc_range_low)

        if manipulation_low:
            long_entry[i] = True
            sl[i] = low[i-1]
            tp[i] = close[i] + (close[i] - low[i-1]) * 3.0

    signals['long_entry'] = long_entry
    signals['short_entry'] = False
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_18_premium_discount(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 18: Premium / Discount Dealing Range Algorithm"""
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']

    r_high = high.rolling(30).max()
    r_low = low.rolling(30).min()
    eq = (r_high + r_low) / 2.0

    in_discount = close < eq
    in_premium = close > eq

    high_5 = high.shift(1).rolling(5).max()
    low_5 = low.shift(1).rolling(5).min()

    long_trigger = in_discount & (close > high_5) & (close.shift(1) <= high_5)
    short_trigger = in_premium & (close < low_5) & (close.shift(1) >= low_5)

    signals['long_entry'] = long_trigger
    signals['short_entry'] = short_trigger
    signals['long_exit'] = False
    signals['short_exit'] = False

    signals['stop_loss'] = np.where(long_trigger, r_low, np.where(short_trigger, r_high, np.nan))
    signals['take_profit'] = np.where(
        long_trigger, eq + (eq - r_low) * 0.8,
        np.where(short_trigger, eq - (r_high - eq) * 0.8, np.nan)
    )
    return signals

def strategy_19_asian_sweep(df: pd.DataFrame) -> pd.DataFrame:
    """Algo 19: Asian Session Range Liquidity Sweep"""
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    long_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n
    atr = calculate_atr(df, 14).values

    if isinstance(df.index, pd.DatetimeIndex):
        grouped = df.groupby(df.index.date)
        for date, group in grouped:
            if len(group) < 5:
                continue
            asia_bars = group[(group.index.hour >= 0) & (group.index.hour < 6)]
            if asia_bars.empty:
                asia_bars = group.iloc[:max(2, len(group)//4)]
            asia_high = asia_bars['high'].max()
            asia_low = asia_bars['low'].min()

            post_bars = group[group.index > asia_bars.index[-1]]
            for idx in post_bars.index:
                i = df.index.get_loc(idx)
                c_low = df.at[idx, 'low']
                c_close = df.at[idx, 'close']
                if c_low < asia_low and c_close > asia_low:
                    long_entry[i] = True
                    curr_atr = atr[i] if not np.isnan(atr[i]) else (c_close * 0.01)
                    sl[i] = asia_low - curr_atr * 0.5
                    tp[i] = asia_high
    else:
        # Fallback
        lookback = 20
        r_low = df['low'].rolling(lookback).min().shift(1)
        r_high = df['high'].rolling(lookback).max().shift(1)
        sweep_l = (df['low'] < r_low) & (df['close'] > r_low)
        long_entry = sweep_l.tolist()
        sl = (r_low - calculate_atr(df, 14) * 0.5).tolist()
        tp = r_high.tolist()

    signals['long_entry'] = long_entry
    signals['short_entry'] = False
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals

def strategy_20_flagship_smc(df: pd.DataFrame, swing_len: int = 7, rr: float = 2.5) -> pd.DataFrame:
    """
    Algo 20: FLAGSHIP SYSTEM: SMC Liquidity Sweep + CHOCH + FVG Engine
    The Definitive Quant Model combining Pivot Sweeps, CHOCH Structure Breaks, and 3-Bar FVG.
    """
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    ph, pl = calculate_pivots(df, swing_len, swing_len)

    long_entry = [False] * n
    short_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    s_high = np.nan
    s_low = np.nan
    swept_l = False
    swept_h = False
    sweep_low_p = np.nan
    sweep_high_p = np.nan

    for i in range(swing_len * 2, n):
        if not np.isnan(ph.iloc[i]):
            s_high = ph.iloc[i]
        if not np.isnan(pl.iloc[i]):
            s_low = pl.iloc[i]

        if not np.isnan(s_low) and low[i] < s_low and close[i] > s_low:
            swept_l = True
            sweep_low_p = low[i]

        if not np.isnan(s_high) and high[i] > s_high and close[i] < s_high:
            swept_h = True
            sweep_high_p = high[i]

        # 3-candle FVG definitions
        bull_fvg = (low[i] > high[i-2]) and (close[i-1] > high[i-2])
        bear_fvg = (high[i] < low[i-2]) and (close[i-1] < low[i-2])

        # Swing structural breaks
        recent_highest = max(high[i - swing_len - 1 : i])
        recent_lowest = min(low[i - swing_len - 1 : i])

        long_sig = swept_l and (close[i] > recent_highest) and bull_fvg
        short_sig = swept_h and (close[i] < recent_lowest) and bear_fvg

        if long_sig:
            long_entry[i] = True
            curr_sl = sweep_low_p if not np.isnan(sweep_low_p) else low[i] * 0.99
            sl[i] = curr_sl
            tp[i] = close[i] + (close[i] - curr_sl) * rr
            swept_l = False

        if short_sig:
            short_entry[i] = True
            curr_sl = sweep_high_p if not np.isnan(sweep_high_p) else high[i] * 1.01
            sl[i] = curr_sl
            tp[i] = close[i] - (curr_sl - close[i]) * rr
            swept_h = False

    signals['long_entry'] = long_entry
    signals['short_entry'] = short_entry
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals
