import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.indicators import calculate_ema, calculate_atr, calculate_rsi, calculate_bollinger_bands, calculate_pivots

df = load_or_fetch_data("GC=F", interval="1h", period="730d")
print("Data loaded:", len(df))

# Test Model A: Daily Trend Filter + 1H RSI Pullback + ATR Trailing Stop
# Test Model B: Liquidity Sweep of Daily/Weekly High-Low + Structural CHOCH
# Test Model C: Bollinger Mean Reversion with Trend Filter
# Test Model D: Supertrend with HTF Filter + Trailing Stop

# Let's inspect Model B: Liquidity Sweep of Pivots (10-bar pivots) with Trend Filter
ph, pl = calculate_pivots(df, 10, 10)
ema200 = calculate_ema(df['close'], 200)
atr = calculate_atr(df, 14)

def evaluate_strategy(long_entries, short_entries, sl_series, tp_series, name="Strategy"):
    initial_capital = 100000.0
    capital = initial_capital
    pos = 0 # 1: Long, -1: Short
    entry_p = 0.0
    sl = 0.0
    tp = 0.0
    trades = []
    
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    n = len(df)
    
    for i in range(1, n):
        # Manage open position
        if pos == 1:
            if lows[i] <= sl:
                # Stop hit
                exit_p = min(opens[i], sl) * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0 # comm + slip
                trades.append(('LONG', 'SL', pnl))
                capital += pnl
                pos = 0
            elif highs[i] >= tp:
                # Target hit
                exit_p = max(opens[i], tp) * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'TP', pnl))
                capital += pnl
                pos = 0
        elif pos == -1:
            if highs[i] >= sl:
                exit_p = max(opens[i], sl) * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'SL', pnl))
                capital += pnl
                pos = 0
            elif lows[i] <= tp:
                exit_p = min(opens[i], tp) * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'TP', pnl))
                capital += pnl
                pos = 0
                
        # New entry
        if pos == 0:
            if long_entries[i]:
                pos = 1
                entry_p = closes[i] * 1.0001
                sl = sl_series[i]
                tp = tp_series[i]
            elif short_entries[i]:
                pos = -1
                entry_p = closes[i] * 0.9999
                sl = sl_series[i]
                tp = tp_series[i]
                
    if len(trades) == 0:
        return {"name": name, "trades": 0, "win_rate": 0, "net_profit": 0}
        
    pnls = [t[2] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(trades) * 100.0
    profit_factor = sum(wins) / abs(sum(losses)) if len(losses) > 0 and sum(losses) != 0 else 99.0
    return {
        "name": name,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "net_profit": round(sum(pnls), 2)
    }

# Let's test a High-Precision Gold Liquidity Sweep System:
# 1. Sweep of 15-bar swing low while close > EMA 200
# 2. Bullish engulfing candle with long lower wick
# 3. Take Profit at recent swing high or 1.5x risk
for lookback in [10, 15, 20]:
    for rr in [1.2, 1.5, 1.8, 2.0]:
        h_swing = df['high'].shift(1).rolling(lookback).max()
        l_swing = df['low'].shift(1).rolling(lookback).min()
        
        # Sweep low then close back above swing low (fakeout)
        sweep_l = (df['low'] < l_swing) & (df['close'] > l_swing) & (df['close'] > ema200) & (df['close'] > df['open'])
        sweep_s = (df['high'] > h_swing) & (df['close'] < h_swing) & (df['close'] < ema200) & (df['close'] < df['open'])
        
        curr_sl_l = (l_swing - atr * 0.5).values
        curr_tp_l = (df['close'] + (df['close'] - (l_swing - atr * 0.5)) * rr).values
        
        curr_sl_s = (h_swing + atr * 0.5).values
        curr_tp_s = (df['close'] - ((h_swing + atr * 0.5) - df['close']) * rr).values
        
        long_e = sweep_l.values
        short_e = sweep_s.values
        
        sl_all = np.where(long_e, curr_sl_l, np.where(short_e, curr_sl_s, np.nan))
        tp_all = np.where(long_e, curr_tp_l, np.where(short_e, curr_tp_s, np.nan))
        
        res = evaluate_strategy(long_e, short_e, sl_all, tp_all, f"Sweep LB={lookback} RR={rr}")
        if res['win_rate'] >= 50 or res['profit_factor'] > 1.3:
            print(res)
