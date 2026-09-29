import numpy as np
import pandas as pd
from engine.indicators import calculate_atr, calculate_pivots, calculate_ema

def strategy_institutional_smc(
    df: pd.DataFrame,
    swing_len: int = 5,
    rr: float = 2.5,
    max_sl_pts: float = None,  # Tight SL cap in points (e.g. 8.0 for 5m, 15.0 for 15m)
    cooldown_bars: int = 4
) -> pd.DataFrame:
    """
    Complete Institutional Smart Money Concepts (SMC) Strategy:
    Based on the Institutional Trilogy:
      1. Power of 3 (AMD): Accumulation -> Manipulation (Liquidity Sweep) -> Distribution
      2. Liquidity Sweep: Price takes out retail stop orders above/below key swing highs/lows
      3. CHOCH (Change of Character): Market structure shift following the sweep
      4. Order Block (OB) Retest: Entry on the retest of the last opposing candle before the impulse
    """
    signals = pd.DataFrame(index=df.index)
    n = len(df)
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_p = df['open'].values
    
    ph, pl = calculate_pivots(df, swing_len, swing_len)
    atr = calculate_atr(df, 14).values
    
    long_entry = [False] * n
    short_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n
    
    # State tracking
    bull_setup = False
    bear_setup = False
    sweep_price_low = np.nan
    sweep_price_high = np.nan
    ob_bull_low = np.nan
    ob_bull_high = np.nan
    ob_bear_low = np.nan
    ob_bear_high = np.nan
    setup_bar_idx = -999
    last_trade_bar = -999
    
    recent_pl = np.nan
    recent_ph = np.nan
    
    for i in range(swing_len * 2, n):
        # Update swing pivots
        if not np.isnan(pl.iloc[i]):
            recent_pl = pl.iloc[i]
        if not np.isnan(ph.iloc[i]):
            recent_ph = ph.iloc[i]
            
        c_close = close[i]
        c_open = open_p[i]
        c_high = high[i]
        c_low = low[i]
        c_atr = atr[i] if not np.isnan(atr[i]) else 5.0
        
        # --- 1. LIQUIDITY SWEEP DETECTION (MANIPULATION PHASE) ---
        # Bullish: Low sweeps below recent Pivot Low, but close rejects back above it
        if not np.isnan(recent_pl) and c_low < recent_pl and c_close > recent_pl and not bull_setup:
            bull_setup = True
            sweep_price_low = c_low
            # Identify Order Block: last bearish candle before impulse
            ob_bull_low = min(c_low, low[i-1])
            ob_bull_high = max(c_open, high[i-1])
            setup_bar_idx = i
            
        # Bearish: High sweeps above recent Pivot High, but close rejects back below it
        if not np.isnan(recent_ph) and c_high > recent_ph and c_close < recent_ph and not bear_setup:
            bear_setup = True
            sweep_price_high = c_high
            # Identify Order Block: last bullish candle before impulse
            ob_bear_low = min(c_open, low[i-1])
            ob_bear_high = max(c_high, high[i-1])
            setup_bar_idx = i
            
        # Timeout on setup (invalidate if no CHOCH or mitigation within 20 bars)
        if (i - setup_bar_idx) > 20:
            bull_setup = False
            bear_setup = False
            
        if (i - last_trade_bar) < cooldown_bars:
            continue
            
        # --- 2. CHOCH & ORDER BLOCK MITIGATION ENTRY ---
        # Bullish Entry:
        # Price swept liquidity, confirmed bullish displacement (close > open), 
        # and mitigates / rejects off the Order Block zone
        if bull_setup and (i > setup_bar_idx):
            mitigated = (c_low <= ob_bull_high and c_close >= ob_bull_low)
            bullish_candle = (c_close > c_open)
            
            if (mitigated or c_close > high[setup_bar_idx]) and bullish_candle:
                risk = max(c_close - sweep_price_low, c_atr * 1.0)
                if max_sl_pts:
                    risk = min(risk, max_sl_pts)
                
                curr_sl = c_close - risk
                curr_tp = c_close + (risk * rr)
                
                long_entry[i] = True
                sl[i] = curr_sl
                tp[i] = curr_tp
                last_trade_bar = i
                bull_setup = False
                
        # Bearish Entry:
        # Price swept liquidity, confirmed bearish displacement (close < open),
        # and mitigates / rejects off the Bearish Order Block zone
        elif bear_setup and (i > setup_bar_idx):
            mitigated = (c_high >= ob_bear_low and c_close <= ob_bear_high)
            bearish_candle = (c_close < c_open)
            
            if (mitigated or c_close < low[setup_bar_idx]) and bearish_candle:
                risk = max(sweep_price_high - c_close, c_atr * 1.0)
                if max_sl_pts:
                    risk = min(risk, max_sl_pts)
                    
                curr_sl = c_close + risk
                curr_tp = c_close - (risk * rr)
                
                short_entry[i] = True
                sl[i] = curr_sl
                tp[i] = curr_tp
                last_trade_bar = i
                bear_setup = False

    signals['long_entry'] = long_entry
    signals['short_entry'] = short_entry
    signals['long_exit'] = False
    signals['short_exit'] = False
    signals['stop_loss'] = sl
    signals['take_profit'] = tp
    return signals
