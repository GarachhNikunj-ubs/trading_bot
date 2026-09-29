import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.indicators import calculate_ema, calculate_atr, calculate_rsi

df = load_or_fetch_data("GC=F", interval="1h", period="730d")
close = df['close']
high = df['high']
low = df['low']
opens = df['open']
ema200 = calculate_ema(close, 200)
ema50 = calculate_ema(close, 50)
atr = calculate_atr(df, 14)

def backtest_gold_disciplined(
    entry_len=30,
    cooldown_bars=10,
    rr=2.0,
    sl_atr_mult=1.5,
    use_htf_filter=True,
    min_adx=20.0
):
    entry_high = high.shift(1).rolling(entry_len).max()
    entry_low = low.shift(1).rolling(entry_len).min()
    
    # 1. Crossover trigger only (NO re-entries on same wave!)
    long_cross = (close > entry_high) & (close.shift(1) <= entry_high.shift(1))
    short_cross = (close < entry_low) & (close.shift(1) >= entry_low.shift(1))
    
    if use_htf_filter:
        long_cross = long_cross & (close > ema200) & (ema50 > ema200)
        short_cross = short_cross & (close < ema200) & (ema50 < ema200)

    pos = 0 # 1 or -1
    entry_p = 0.0
    sl = 0.0
    tp = 0.0
    last_exit_idx = -999
    trades = []
    
    for i in range(max(entry_len, 200), len(df)):
        c = close.iloc[i]
        h = high.iloc[i]
        l = low.iloc[i]
        c_atr = atr.iloc[i]

        # Manage Position
        if pos == 1:
            if l <= sl:
                # Stop hit
                exit_p = sl * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'SL', pnl))
                pos = 0
                last_exit_idx = i
            elif h >= tp:
                # Target hit
                exit_p = tp * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'TP', pnl))
                pos = 0
                last_exit_idx = i

        elif pos == -1:
            if h >= sl:
                exit_p = sl * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'SL', pnl))
                pos = 0
                last_exit_idx = i
            elif l <= tp:
                exit_p = tp * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'TP', pnl))
                pos = 0
                last_exit_idx = i

        # New Entry with Cooldown
        if pos == 0 and (i - last_exit_idx > cooldown_bars):
            if long_cross.iloc[i]:
                pos = 1
                entry_p = c * 1.0001
                risk = c_atr * sl_atr_mult
                sl = entry_p - risk
                tp = entry_p + risk * rr
            elif short_cross.iloc[i]:
                pos = -1
                entry_p = c * 0.9999
                risk = c_atr * sl_atr_mult
                sl = entry_p + risk
                tp = entry_p - risk * rr

    pnls = [t[2] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if len(trades) > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 and sum(losses) != 0 else 99.0
    return {
        "entry_len": entry_len,
        "cooldown": cooldown_bars,
        "rr": rr,
        "sl_mult": sl_atr_mult,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 2),
        "net_profit": round(sum(pnls), 2)
    }

print("\n--- Disciplined Gold Crossover + Cooldown Filter ---")
for el in [20, 30, 40, 50]:
    for cd in [10, 15, 20]:
        for sl_m in [1.5, 2.0, 2.5]:
            for rr_target in [1.2, 1.5, 2.0]:
                r = backtest_gold_disciplined(el, cd, rr_target, sl_m, True)
                if r['win_rate'] >= 55 and r['profit_factor'] >= 1.4:
                    print(f"Entry={r['entry_len']} | CD={r['cooldown']} | SL={r['sl_mult']}x | RR={r['rr']} -> Trades: {r['trades']} | Win Rate: {r['win_rate']}% | PF: {r['profit_factor']} | Net Profit: ${r['net_profit']}")
