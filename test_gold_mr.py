import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.indicators import calculate_ema, calculate_atr, calculate_rsi, calculate_bollinger_bands

df = load_or_fetch_data("GC=F", interval="1h", period="730d")
close = df['close']
high = df['high']
low = df['low']
n = len(df)

rsi7 = calculate_rsi(close, 7)
atr = calculate_atr(df, 14)
basis, upper, lower, bb_width = calculate_bollinger_bands(close, 20, 2.0)
ema50 = calculate_ema(close, 50)
ema200 = calculate_ema(close, 200)

def test_gold_mean_reversion(rsi_buy=25, rsi_sell=75, stop_atr=2.0, target_ema=True):
    pos = 0 # 1 or -1
    entry_p = 0.0
    sl = 0.0
    trades = []
    
    for i in range(200, n):
        c = close.iloc[i]
        h = high.iloc[i]
        l = low.iloc[i]
        c_atr = atr.iloc[i]
        
        # Position Management
        if pos == 1:
            if l <= sl:
                exit_p = sl * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'SL', pnl))
                pos = 0
            elif (target_ema and c >= basis.iloc[i]) or (not target_ema and rsi7.iloc[i] >= 50):
                exit_p = c * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'TP', pnl))
                pos = 0
        elif pos == -1:
            if h >= sl:
                exit_p = sl * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'SL', pnl))
                pos = 0
            elif (target_ema and c <= basis.iloc[i]) or (not target_ema and rsi7.iloc[i] <= 50):
                exit_p = c * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'TP', pnl))
                pos = 0
                
        # Entries
        if pos == 0:
            # Long: RSI extreme oversold + price below lower Bollinger Band
            # Filter: must not be in a raging downtrend (or only buy if close > ema200)
            if (rsi7.iloc[i] < rsi_buy) and (l <= lower.iloc[i]) and (c > ema200.iloc[i]):
                pos = 1
                entry_p = c * 1.0001
                sl = entry_p - c_atr * stop_atr
            elif (rsi7.iloc[i] > rsi_sell) and (h >= upper.iloc[i]) and (c < ema200.iloc[i]):
                pos = -1
                entry_p = c * 0.9999
                sl = entry_p + c_atr * stop_atr

    pnls = [t[2] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if len(trades) > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 and sum(losses) != 0 else 99.0
    return {
        "rsi_buy": rsi_buy,
        "stop_atr": stop_atr,
        "target_ema": target_ema,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 2),
        "net_profit": round(sum(pnls), 2)
    }

print("Testing Trend-Filtered Mean Reversion on Gold 1H...")
for rb in [20, 25, 30]:
    for sa in [1.5, 2.0, 2.5, 3.0]:
        for tema in [True, False]:
            r = test_gold_mean_reversion(rb, 100-rb, sa, tema)
            if r['win_rate'] >= 60 and r['profit_factor'] >= 1.2:
                print(f"RSI={r['rsi_buy']}/{100-r['rsi_buy']} | SL={r['stop_atr']}x ATR | TargetBasis={r['target_ema']} -> Trades: {r['trades']} | Win Rate: {r['win_rate']}% | PF: {r['profit_factor']} | Net Profit: ${r['net_profit']}")
