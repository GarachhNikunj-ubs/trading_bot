import yfinance as yf
import pandas as pd
import numpy as np
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr

def audit_5m():
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    htf_ema = calculate_ema(df_1h['close'], 50)
    htf_st_val, htf_st_dir = calculate_supertrend(df_1h, 10, 3.0)

    htf_bull = ((df_1h['close'] > htf_ema) & (htf_st_dir < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    htf_bear = ((df_1h['close'] < htf_ema) & (htf_st_dir > 0)).reindex(df_5m.index, method='ffill').fillna(False)

    atr_5m = calculate_atr(df_5m, 14)
    ph_5m, pl_5m = calculate_pivots(df_5m, 6, 6)

    n = len(df_5m)
    long_entry = [False]*n
    short_entry = [False]*n
    sl = [np.nan]*n
    tp = [np.nan]*n

    s_low = np.nan
    s_high = np.nan
    last_idx = -999

    max_sl = 8.0
    rr = 1.8
    cooldown = 6

    for i in range(100, n):
        if not np.isnan(pl_5m.iloc[i]): s_low = pl_5m.iloc[i]
        if not np.isnan(ph_5m.iloc[i]): s_high = ph_5m.iloc[i]
        
        if (i - last_idx) < cooldown: continue
        
        # Session filter: 07:00 to 20:00 UTC
        hour = df_5m.index[i].hour
        in_session = (7 <= hour < 20)
        if not in_session: continue
        
        c = df_5m['close'].iloc[i]
        o = df_5m['open'].iloc[i]
        h = df_5m['high'].iloc[i]
        l = df_5m['low'].iloc[i]
        a = atr_5m.iloc[i]
        
        if bool(htf_bull.iloc[i]) and not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o):
            raw_risk = max(c - l, a * 1.2)
            risk = min(raw_risk, max_sl)
            long_entry[i] = True
            sl[i] = c - risk
            tp[i] = c + risk * rr
            last_idx = i
        elif bool(htf_bear.iloc[i]) and not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o):
            raw_risk = max(h - c, a * 1.2)
            risk = min(raw_risk, max_sl)
            short_entry[i] = True
            sl[i] = c + risk
            tp[i] = c - risk * rr
            last_idx = i

    sigs = pd.DataFrame({'long_entry': long_entry, 'short_entry': short_entry, 'stop_loss': sl, 'take_profit': tp}, index=df_5m.index)
    sigs['long_exit'] = False
    sigs['short_exit'] = False

    eng = BacktestEngine(100000.0, qty_pct=0.10, commission_pct=0.0003, slippage_pct=0.0001)
    metrics = eng.execute_backtest(df_5m, 'Gold 5M Scalp Fusion', sigs)

    wins = [t for t in eng.trades if t.pnl_net > 0]
    losses = [t for t in eng.trades if t.pnl_net < 0]
    sl_hits = [t for t in eng.trades if t.exit_reason == 'Stop Loss']
    tp_hits = [t for t in eng.trades if t.exit_reason == 'Take Profit']

    avg_win = np.mean([t.pnl_net for t in wins]) if wins else 0
    avg_loss = np.mean([abs(t.pnl_net) for t in losses]) if losses else 0
    avg_sl_pts = np.mean([abs(t.entry_price - t.exit_price) for t in sl_hits]) if sl_hits else 0
    avg_tp_pts = np.mean([abs(t.entry_price - t.exit_price) for t in tp_hits]) if tp_hits else 0
    avg_bars = np.mean([t.holding_bars for t in eng.trades]) if eng.trades else 0

    print("=== EXACT 5M GOLD SCALP BACKTEST RESULTS ===")
    print(f"Candles Tested: {len(df_5m):,} bars (60 days)")
    print(f"Total Closed Trades: {metrics['Total Trades']}")
    print(f"Winning Trades: {len(wins)} ({metrics['Win Rate (%)']:.1f}%)")
    print(f"Losing Trades: {len(losses)} ({100.0 - metrics['Win Rate (%)']:.1f}%)")
    print(f"Net Profit ($): ${metrics['Net Profit ($)']:,.2f}")
    print(f"Total Return (%): +{metrics['Return (%)']:.2f}%")
    print(f"Profit Factor: {metrics['Profit Factor']:.2f}")
    print(f"Max Drawdown (%): {metrics['Max Drawdown (%)']:.2f}%")
    print(f"Sharpe Ratio: {metrics['Sharpe Ratio']:.2f}")
    print(f"Average Win ($): +${avg_win:.2f}")
    print(f"Average Loss ($): -${avg_loss:.2f}")
    print(f"Average Stop Loss (Points): ${avg_sl_pts:.2f} / oz (Capped at $8.00)")
    print(f"Average Take Profit (Points): ${avg_tp_pts:.2f} / oz")
    print(f"Average Trade Duration: {avg_bars * 5:.0f} minutes (~{avg_bars:.1f} candles)")

if __name__ == "__main__":
    audit_5m()
