import numpy as np
import pandas as pd
from engine.indicators import (
    calculate_ema,
    calculate_atr,
    calculate_supertrend,
    calculate_rsi,
    calculate_pivots
)

def strategy_dual_engine_fusion(
    df: pd.DataFrame,
    swing_len: int = 7,
    st_period: int = 10,
    st_mult: float = 3.0,
    ema_macro_len: int = 200,
    rr: float = 2.0,
    sl_atr_mult: float = 1.5,
    cooldown_bars: int = 6
) -> pd.DataFrame:
    """
    Dual-Engine Fusion Strategy:
    Combines:
      Engine A (Macro Volatility & Trend): Supertrend(10, 3.0) + 200 EMA Filter
      Engine B (SMC Liquidity Sweep): Pivot Low/High Sweep (Trap Reversal into Trend Direction)
    
    Logic:
      - Long: Supertrend is Bullish (stDir < 0) AND Close > 200 EMA
              AND Low sweeps below recent Pivot Low, then closes back ABOVE the Pivot Low (Stop Run Completed)
              AND Current candle is a strong green rejection candle (Close > Open).
      - Short: Supertrend is Bearish (stDir > 0) AND Close < 200 EMA
               AND High sweeps above recent Pivot High, then closes back BELOW the Pivot High
               AND Current candle is a strong red rejection candle (Close < Open).
    """
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']
    open_p = df['open']
    n = len(df)

    ema200 = calculate_ema(close, ema_macro_len)
    st_val, st_dir = calculate_supertrend(df, period=st_period, multiplier=st_mult)
    ph, pl = calculate_pivots(df, swing_len, swing_len)
    atr = calculate_atr(df, 14)

    long_entry = [False] * n
    short_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    s_low = np.nan
    s_high = np.nan
    last_trade_idx = -999

    for i in range(max(ema_macro_len, swing_len * 2), n):
        # Update latest confirmed swing pivot reference
        if not np.isnan(pl.iloc[i]):
            s_low = pl.iloc[i]
        if not np.isnan(ph.iloc[i]):
            s_high = ph.iloc[i]

        c_close = close.iloc[i]
        c_open = open_p.iloc[i]
        c_high = high.iloc[i]
        c_low = low.iloc[i]
        c_atr = atr.iloc[i]

        # Check cooldown to prevent overtrading
        if (i - last_trade_idx) < cooldown_bars:
            continue

        # Engine A: Macro Trend Conditions
        bull_trend = (c_close > ema200.iloc[i]) and (st_dir.iloc[i] < 0)
        bear_trend = (c_close < ema200.iloc[i]) and (st_dir.iloc[i] > 0)

        # Engine B: Liquidity Sweep Triggers (Stop run + quick rejection)
        sweep_long = not np.isnan(s_low) and (c_low < s_low) and (c_close > s_low) and (c_close > c_open)
        sweep_short = not np.isnan(s_high) and (c_high > s_high) and (c_close < s_high) and (c_close < c_open)

        # Fusion Long Signal
        if bull_trend and sweep_long:
            risk = max(c_close - c_low, c_atr * sl_atr_mult)
            curr_sl = c_close - risk
            curr_tp = c_close + risk * rr
            long_entry[i] = True
            sl[i] = curr_sl
            tp[i] = curr_tp
            last_trade_idx = i

        # Fusion Short Signal
        elif bear_trend and sweep_short:
            risk = max(c_high - c_close, c_atr * sl_atr_mult)
            curr_sl = c_close + risk
            curr_tp = c_close - risk * rr
            short_entry[i] = True
            sl[i] = curr_sl
            tp[i] = curr_tp
            last_trade_idx = i

    signals['long_entry'] = long_entry
    signals['short_entry'] = short_entry
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals
