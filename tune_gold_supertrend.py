import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.indicators import calculate_ema, calculate_atr, calculate_supertrend, calculate_rsi

df_1h = load_or_fetch_data("GC=F", interval="1h", period="730d")
df_1h.index = pd.to_datetime(df_1h.index, utc=True)
df = df_1h.resample('4h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

close = df['close']
high = df['high']
low = df['low']
opens = df['open']
n = len(df)

ema200 = calculate_ema(close, 200)
ema50 = calculate_ema(close, 50)
atr = calculate_atr(df, 14)
rsi = calculate_rsi(close, 14)
st_val, st_dir = calculate_supertrend(df, period=10, multiplier=3.0)

# Test improvements to Supertrend + 200 EMA
# Basic signals
bull_flip = (st_dir == -1) & (st_dir.shift(1) == 1)
bear_flip = (st_dir == 1) & (st_dir.shift(1) == -1)

def test_enhanced_supertrend(tp_atr_mult=2.5, sl_atr_mult=1.8, max_rsi=68, min_rsi=32, be_mult=1.2):
    pos = 0 # 1 or -1
    entry_p = 0.0
    sl = 0.0
    tp = 0.0
    be_active = False
    trades = []
    
    for i in range(200, n):
        c = close.iloc[i]
        h = high.iloc[i]
        l = low.iloc[i]
        c_atr = atr.iloc[i]
        
        # Position management
        if pos == 1:
            # Check Breakeven trigger
            if not be_active and (h >= entry_p + be_mult * c_atr):
                be_active = True
                sl = entry_p * 1.0005 # Breakeven
                
            if l <= sl:
                exit_p = min(opens.iloc[i], sl) * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'SL/BE', pnl))
                pos = 0
            elif h >= tp:
                exit_p = max(opens.iloc[i], tp) * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'TP', pnl))
                pos = 0
            elif st_dir.iloc[i] > 0: # Supertrend turned bearish
                exit_p = c * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'ST_EXIT', pnl))
                pos = 0
                
        elif pos == -1:
            if not be_active and (l <= entry_p - be_mult * c_atr):
                be_active = True
                sl = entry_p * 0.9995
                
            if h >= sl:
                exit_p = max(opens.iloc[i], sl) * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'SL/BE', pnl))
                pos = 0
            elif l <= tp:
                exit_p = min(opens.iloc[i], tp) * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'TP', pnl))
                pos = 0
            elif st_dir.iloc[i] < 0: # Supertrend turned bullish
                exit_p = c * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'ST_EXIT', pnl))
                pos = 0
                
        # Entry
        if pos == 0:
            # Long condition: Bull flip + close > ema200 + RSI not overbought
            if bull_flip.iloc[i] and (c > ema200.iloc[i]) and (rsi.iloc[i] <= max_rsi):
                pos = 1
                entry_p = c * 1.0001
                sl = entry_p - c_atr * sl_atr_mult
                tp = entry_p + c_atr * tp_atr_mult
                be_active = False
            elif bear_flip.iloc[i] and (c < ema200.iloc[i]) and (rsi.iloc[i] >= min_rsi):
                pos = -1
                entry_p = c * 0.9999
                sl = entry_p + c_atr * sl_atr_mult
                tp = entry_p - c_atr * tp_atr_mult
                be_active = False
                
    pnls = [t[2] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if len(trades) > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 and sum(losses) != 0 else 99.0
    return {
        "tp_mult": tp_atr_mult,
        "sl_mult": sl_atr_mult,
        "be_mult": be_mult,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 2),
        "net_profit": round(sum(pnls), 2)
    }

print("Testing Enhanced Supertrend + 200 EMA + Breakeven Engine on Gold 4H...")
for tp in [2.0, 2.5, 3.0, 3.5]:
    for sl in [1.5, 2.0]:
        for be in [1.0, 1.2, 1.5]:
            r = test_enhanced_supertrend(tp, sl, 68, 32, be)
            if r['win_rate'] >= 60 and r['profit_factor'] >= 2.0:
                print(f"TP={r['tp_mult']}x ATR | SL={r['sl_mult']}x ATR | BE={r['be_mult']}x ATR -> Trades: {r['trades']} | Win Rate: {r['win_rate']}% | Profit Factor: {r['profit_factor']} | Net Profit: ${r['net_profit']}")
