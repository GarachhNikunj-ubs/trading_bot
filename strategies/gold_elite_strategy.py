import os
import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_atr, calculate_rsi

def calculate_adx(df: pd.DataFrame, length: int = 14):
    """Calculates Wilder's ADX for trend strength."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/length, adjust=False).mean()
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    pos_di = 100 * pd.Series(pos_dm, index=df.index).ewm(alpha=1/length, adjust=False).mean() / atr
    neg_di = 100 * pd.Series(neg_dm, index=df.index).ewm(alpha=1/length, adjust=False).mean() / atr
    
    dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/length, adjust=False).mean()
    return adx, pos_di, neg_di

def gold_elite_trend_pullback(
    df: pd.DataFrame,
    ema_trend_len: int = 200,
    ema_fast_len: int = 21,
    ema_mid_len: int = 50,
    adx_threshold: float = 22.0,
    tp_mult: float = 2.0,
    sl_mult: float = 1.2
) -> pd.DataFrame:
    """
    Gold Institutional Trend-Pullback & Liquidity Engine:
    1. Macro Regime: Close > EMA 200 and EMA 50 > EMA 200 (Long only in bull market).
    2. Trend Strength: ADX(14) > threshold (avoids consolidation whipsaws).
    3. Retracement Trigger: Price pulls back to tag EMA 21 or EMA 50 with RSI between 40 and 60.
    4. Confirmation: Bullish rejection candle closing back above EMA 21.
    5. Tight Risk / High Asymmetry: SL below recent 3-bar swing low; TP at 2.0x risk.
    """
    signals = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']
    open_p = df['open']
    n = len(df)
    
    ema_fast = calculate_ema(close, ema_fast_len)
    ema_mid = calculate_ema(close, ema_mid_len)
    ema_trend = calculate_ema(close, ema_trend_len)
    atr = calculate_atr(df, 14)
    rsi = calculate_rsi(close, 14)
    adx, pos_di, neg_di = calculate_adx(df, 14)
    
    long_entries = [False] * n
    short_entries = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n
    
    for i in range(max(ema_trend_len, 50), n):
        # Time / Session filter if DatetimeIndex available (focus on London/NY sessions: 07:00 - 20:00 UTC)
        if isinstance(df.index, pd.DatetimeIndex):
            hour = df.index[i].hour
            in_session = (7 <= hour <= 20)
        else:
            in_session = True
            
        if not in_session:
            continue
            
        c_close = close.iloc[i]
        c_low = low.iloc[i]
        c_high = high.iloc[i]
        c_open = open_p.iloc[i]
        
        c_ema21 = ema_fast.iloc[i]
        c_ema50 = ema_mid.iloc[i]
        c_ema200 = ema_trend.iloc[i]
        c_adx = adx.iloc[i]
        c_rsi = rsi.iloc[i]
        c_atr = atr.iloc[i]
        
        # Bullish Setup
        bull_regime = (c_close > c_ema200) and (c_ema50 > c_ema200)
        strong_trend = c_adx > adx_threshold and pos_di.iloc[i] > neg_di.iloc[i]
        
        # Pullback tag into value zone (low penetrates EMA 21 or EMA 50)
        pullback_long = (low.iloc[i-1] <= ema_fast.iloc[i-1] or c_low <= c_ema21) and (42 <= c_rsi <= 65)
        # Rejection candle: strong green close above open and close above EMA 21
        bullish_candle = (c_close > c_open) and (c_close > c_ema21) and (c_close - c_low) > (c_high - c_close)
        
        if bull_regime and strong_trend and pullback_long and bullish_candle:
            recent_low = min(low.iloc[i-3:i+1])
            risk = c_close - recent_low
            if risk > c_atr * 0.4: # Filter micro-stops
                long_entries[i] = True
                curr_sl = c_close - risk * sl_mult
                curr_tp = c_close + risk * tp_mult
                sl[i] = curr_sl
                tp[i] = curr_tp
                continue
                
        # Bearish Setup
        bear_regime = (c_close < c_ema200) and (c_ema50 < c_ema200)
        bear_trend = c_adx > adx_threshold and neg_di.iloc[i] > pos_di.iloc[i]
        
        pullback_short = (high.iloc[i-1] >= ema_fast.iloc[i-1] or c_high >= c_ema21) and (35 <= c_rsi <= 58)
        bearish_candle = (c_close < c_open) and (c_close < c_ema21) and (c_high - c_close) > (c_close - c_low)
        
        if bear_regime and bear_trend and pullback_short and bearish_candle:
            recent_high = max(high.iloc[i-3:i+1])
            risk = recent_high - c_close
            if risk > c_atr * 0.4:
                short_entries[i] = True
                curr_sl = c_close + risk * sl_mult
                curr_tp = c_close - risk * tp_mult
                sl[i] = curr_sl
                tp[i] = curr_tp

    signals['long_entry'] = long_entries
    signals['short_entry'] = short_entries
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals
