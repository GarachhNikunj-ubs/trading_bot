import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.indicators import calculate_ema, calculate_atr

df = load_or_fetch_data("GC=F", interval="1h", period="730d")
close = df['close']
high = df['high']
low = df['low']
ema200 = calculate_ema(close, 200)
ema50 = calculate_ema(close, 50)
atr = calculate_atr(df, 14)

def backtest_donchian_filtered(entry_len=20, exit_len=10, use_ema200=True, atr_filter=0.0):
    entry_high = high.shift(1).rolling(entry_len).max()
    entry_low = low.shift(1).rolling(entry_len).min()
    exit_high = high.shift(1).rolling(exit_len).max()
    exit_low = low.shift(1).rolling(exit_len).min()

    long_cond = close > (entry_high + atr * atr_filter)
    short_cond = close < (entry_low - atr * atr_filter)

    if use_ema200:
        long_cond = long_cond & (close > ema200) & (ema50 > ema200)
        short_cond = short_cond & (close < ema200) & (ema50 < ema200)

    # Let's run simulation with 10% equity sizing, 0.03% comm, 1 tick slippage
    pos = 0 # 1 or -1
    entry_p = 0.0
    trades = []

    for i in range(max(entry_len, 200), len(df)):
        c = close.iloc[i]
        o = df['open'].iloc[i]

        # Check exits
        if pos == 1:
            if c < exit_low.iloc[i]:
                # Exit long
                exit_p = c * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', pnl))
                pos = 0
        elif pos == -1:
            if c > exit_high.iloc[i]:
                exit_p = c * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', pnl))
                pos = 0

        # Check entries
        if pos == 0:
            if long_cond.iloc[i]:
                pos = 1
                entry_p = c * 1.0001
            elif short_cond.iloc[i]:
                pos = -1
                entry_p = c * 0.9999

    pnls = [t[1] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if len(trades) > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 and sum(losses) != 0 else 0
    return {
        "entry_len": entry_len,
        "exit_len": exit_len,
        "use_ema200": use_ema200,
        "atr_filter": atr_filter,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 2),
        "net_profit": round(sum(pnls), 2)
    }

print("Running parameter sweep on filtered trend breakouts...")
for e_len in [20, 30, 40, 50]:
    for x_len in [10, 15, 20]:
        for use_ema in [True, False]:
            for af in [0.0, 0.2]:
                r = backtest_donchian_filtered(e_len, x_len, use_ema, af)
                if r['profit_factor'] >= 1.5 or r['win_rate'] >= 45:
                    print(r)
