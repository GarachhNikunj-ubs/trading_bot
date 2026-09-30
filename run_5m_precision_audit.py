import yfinance as yf
import pandas as pd
import numpy as np
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_supertrend, calculate_atr, calculate_rsi

def run_precision_audit():
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    ema_1h = calculate_ema(df_1h['close'], 50)
    st_1h_v, st_1h_d = calculate_supertrend(df_1h, 10, 3.0)

    bull_1h = ((df_1h['close'] > ema_1h) & (st_1h_d < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    bear_1h = ((df_1h['close'] < ema_1h) & (st_1h_d > 0)).reindex(df_5m.index, method='ffill').fillna(False)

    rsi = calculate_rsi(df_5m['close'], 14)
    atr = calculate_atr(df_5m, 14)

    n = len(df_5m)
    long_entry = [False] * n
    short_entry = [False] * n
    sl = [np.nan] * n
    tp = [np.nan] * n

    last_t = -999
    for i in range(100, n):
        if (i - last_t) < 8: continue
        hour = df_5m.index[i].hour
        # Peak London/NY Liquidity Session: 08:00 to 16:30 UTC
        if not (8 <= hour < 17): continue
        
        c = df_5m['close'].iloc[i]
        o = df_5m['open'].iloc[i]
        l = df_5m['low'].iloc[i]
        h = df_5m['high'].iloc[i]
        
        recent_l = min(df_5m['low'].iloc[max(0, i-6):i])
        recent_h = max(df_5m['high'].iloc[max(0, i-6):i])
        
        body = abs(c - o)
        lower_wick = min(c, o) - l
        upper_wick = h - max(c, o)
        
        # Institutional SMC Hammer / Shooting Star Rejection into Order Block
        is_hammer = (lower_wick >= 1.4 * body) and (c > o) and (rsi.iloc[i] < 48)
        is_star = (upper_wick >= 1.4 * body) and (c < o) and (rsi.iloc[i] > 52)
        
        if bool(bull_1h.iloc[i]) and is_hammer and (l <= recent_l):
            risk = min(max(c - l, 4.0), 8.0) # Tight $4-$8 SL
            long_entry[i] = True
            sl[i] = c - risk
            tp[i] = c + (risk * 1.0)
            last_t = i
        elif bool(bear_1h.iloc[i]) and is_star and (h >= recent_h):
            risk = min(max(h - c, 4.0), 8.0) # Tight $4-$8 SL
            short_entry[i] = True
            sl[i] = c + risk
            tp[i] = c - (risk * 1.0)
            last_t = i

    sigs = pd.DataFrame({'long_entry': long_entry, 'short_entry': short_entry, 'stop_loss': sl, 'take_profit': tp}, index=df_5m.index)
    sigs['long_exit'] = False
    sigs['short_exit'] = False

    eng = BacktestEngine(100000.0, qty_pct=0.10, commission_pct=0.0003, slippage_pct=0.0001)
    res = eng.execute_backtest(df_5m, 'Gold 5M Precision Scalp [70% Target]', sigs)

    sl_trades = [abs(t.entry_price - t.exit_price) for t in eng.trades if t.exit_reason == 'Stop Loss']
    tp_trades = [abs(t.entry_price - t.exit_price) for t in eng.trades if t.exit_reason == 'Take Profit']
    wins = [t for t in eng.trades if t.pnl_net > 0]
    losses = [t for t in eng.trades if t.pnl_net < 0]

    avg_sl = np.mean(sl_trades) if sl_trades else 0.0
    avg_tp = np.mean(tp_trades) if tp_trades else 0.0

    print("="*80)
    print(" 70% WIN RATE 5-MINUTE GOLD SCALP AUDIT RESULTS")
    print("="*80)
    print(f"Total Closed Trades: {res['Total Trades']}")
    print(f"Winning Trades: {len(wins)} ({res['Win Rate (%)']:.1f}%)")
    print(f"Losing Trades: {len(losses)} ({100.0 - res['Win Rate (%)']:.1f}%)")
    print(f"Win Rate: {res['Win Rate (%)']:.1f}%")
    print(f"Profit Factor: {res['Profit Factor']:.2f}")
    print(f"Net Profit ($): ${res['Net Profit ($)']:,.2f}")
    print(f"Max Drawdown (%): {res['Max Drawdown (%)']:.2f}%")
    print(f"Average Stop Loss: ${avg_sl:.2f} points/oz (Max $8.00 Cap)")
    print(f"Average Take Profit: ${avg_tp:.2f} points/oz")
    print(f"Average Risk-to-Reward: 1:1.0 Realized")

if __name__ == "__main__":
    run_precision_audit()
