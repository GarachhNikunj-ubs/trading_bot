import numpy as np
import pandas as pd
from engine.data import load_or_fetch_data
from engine.indicators import calculate_ema, calculate_atr

df = load_or_fetch_data("GC=F", interval="1h", period="730d")
close = df['close']
high = df['high']
low = df['low']
opens = df['open']
ema200 = calculate_ema(close, 200)
ema50 = calculate_ema(close, 50)
atr = calculate_atr(df, 14)

def backtest_gold_breakeven_system(
    entry_len=20,
    exit_len=10,
    be_trigger_mult=1.0, # Move stop to breakeven when profit reaches 1.0 * ATR
    use_session_filter=True
):
    entry_high = high.shift(1).rolling(entry_len).max()
    entry_low = low.shift(1).rolling(entry_len).min()
    exit_high = high.shift(1).rolling(exit_len).max()
    exit_low = low.shift(1).rolling(exit_len).min()

    long_cond = (close > entry_high) & (close > ema200) & (ema50 > ema200)
    short_cond = (close < entry_low) & (close < ema200) & (ema50 < ema200)

    pos = 0 # 1 or -1
    entry_p = 0.0
    sl = 0.0
    initial_risk = 0.0
    be_active = False
    trades = []

    for i in range(max(entry_len, 200), len(df)):
        c = close.iloc[i]
        h = high.iloc[i]
        l = low.iloc[i]
        c_atr = atr.iloc[i]
        
        # Session filter: London & NY (07:00 - 17:00 UTC)
        if use_session_filter and isinstance(df.index, pd.DatetimeIndex):
            hour = df.index[i].hour
            in_session = (7 <= hour <= 17)
        else:
            in_session = True

        # Check Active Position
        if pos == 1:
            # Check if breakeven threshold reached
            if not be_active and (h >= entry_p + be_trigger_mult * c_atr):
                be_active = True
                sl = entry_p * 1.0005 # Breakeven plus tiny buffer for fees
                
            # Check Stop Loss
            if l <= sl:
                exit_p = sl * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'SL/BE', pnl))
                pos = 0
            # Check Trailing Channel Exit
            elif c < exit_low.iloc[i]:
                exit_p = c * 0.9999
                pnl = (exit_p - entry_p) / entry_p * 10000.0 - 6.0
                trades.append(('LONG', 'CHANNEL', pnl))
                pos = 0

        elif pos == -1:
            if not be_active and (l <= entry_p - be_trigger_mult * c_atr):
                be_active = True
                sl = entry_p * 0.9995

            if h >= sl:
                exit_p = sl * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'SL/BE', pnl))
                pos = 0
            elif c > exit_high.iloc[i]:
                exit_p = c * 1.0001
                pnl = (entry_p - exit_p) / entry_p * 10000.0 - 6.0
                trades.append(('SHORT', 'CHANNEL', pnl))
                pos = 0

        # New Entries
        if pos == 0 and in_session:
            if long_cond.iloc[i]:
                pos = 1
                entry_p = c * 1.0001
                initial_risk = c_atr * 1.5
                sl = entry_p - initial_risk
                be_active = False
            elif short_cond.iloc[i]:
                pos = -1
                entry_p = c * 0.9999
                initial_risk = c_atr * 1.5
                sl = entry_p + initial_risk
                be_active = False

    pnls = [t[2] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(trades) * 100.0) if len(trades) > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 and sum(losses) != 0 else 99.0
    return {
        "entry_len": entry_len,
        "exit_len": exit_len,
        "be_trigger": be_trigger_mult,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 2),
        "net_profit": round(sum(pnls), 2)
    }

print("\nTesting Gold Breakeven Protection & Session Filtering...")
for be in [0.8, 1.0, 1.2, 1.5]:
    for e_len in [20, 30]:
        for x_len in [8, 10]:
            r = backtest_gold_breakeven_system(e_len, x_len, be, True)
            print(f"BE={be}x ATR | Entry={e_len} | Exit={x_len} -> Trades: {r['trades']} | Win Rate: {r['win_rate']}% | Profit Factor: {r['profit_factor']} | Net Profit: ${r['net_profit']}")
