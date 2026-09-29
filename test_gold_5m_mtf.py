import yfinance as yf
import pandas as pd
import numpy as np
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr

def test_mtf():
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    # Resample to 1H for HTF trend filter
    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    ema50_1h = calculate_ema(df_1h['close'], 50)
    st_val_1h, st_dir_1h = calculate_supertrend(df_1h, 10, 3.0)

    # Reindex HTF to 5m
    htf_bull = ((df_1h['close'] > ema50_1h) & (st_dir_1h < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    htf_bear = ((df_1h['close'] < ema50_1h) & (st_dir_1h > 0)).reindex(df_5m.index, method='ffill').fillna(False)

    atr_5m = calculate_atr(df_5m, 14)
    ph_5m, pl_5m = calculate_pivots(df_5m, 8, 8)

    # Test several SL caps and R:R ratios
    experiments = [
        ("MTF 5m (SL capped at $6, RR 1.5)", 6.0, 1.5, 12),
        ("MTF 5m (SL capped at $8, RR 1.5)", 8.0, 1.5, 12),
        ("MTF 5m (SL capped at $10, RR 2.0)", 10.0, 2.0, 12),
        ("MTF 5m (SL capped at $12, RR 2.0)", 12.0, 2.0, 18),
        ("MTF 5m (SL capped at $15, RR 2.0)", 15.0, 2.0, 18),
    ]

    for label, max_sl, rr, cd in experiments:
        n = len(df_5m)
        long_entry = [False]*n
        short_entry = [False]*n
        sl = [np.nan]*n
        tp = [np.nan]*n

        s_low = np.nan
        s_high = np.nan
        last_idx = -999

        for i in range(100, n):
            if not np.isnan(pl_5m.iloc[i]): s_low = pl_5m.iloc[i]
            if not np.isnan(ph_5m.iloc[i]): s_high = ph_5m.iloc[i]
            
            if (i - last_idx) < cd: continue
            
            c = df_5m['close'].iloc[i]
            o = df_5m['open'].iloc[i]
            h = df_5m['high'].iloc[i]
            l = df_5m['low'].iloc[i]
            a = atr_5m.iloc[i]
            
            if bool(htf_bull.iloc[i]) and not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o):
                risk = min(max(c - l, a * 1.2), max_sl)
                long_entry[i] = True
                sl[i] = c - risk
                tp[i] = c + risk * rr
                last_idx = i
            elif bool(htf_bear.iloc[i]) and not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o):
                risk = min(max(h - c, a * 1.2), max_sl)
                short_entry[i] = True
                sl[i] = c + risk
                tp[i] = c - risk * rr
                last_idx = i

        sigs = pd.DataFrame({'long_entry': long_entry, 'short_entry': short_entry, 'stop_loss': sl, 'take_profit': tp}, index=df_5m.index)
        sigs['long_exit'] = False
        sigs['short_exit'] = False

        eng = BacktestEngine(100000.0, qty_pct=0.10, commission_pct=0.0003, slippage_pct=0.0001)
        res = eng.execute_backtest(df_5m, label, sigs)

        sl_trades = [abs(t.entry_price - t.exit_price) for t in eng.trades if t.exit_reason == 'Stop Loss']
        tp_trades = [abs(t.entry_price - t.exit_price) for t in eng.trades if t.exit_reason == 'Take Profit']
        avg_sl = np.mean(sl_trades) if sl_trades else 0.0
        avg_tp = np.mean(tp_trades) if tp_trades else 0.0

        print(f"--- {label} ---")
        print(f"Trades: {res['Total Trades']} | Win Rate: {res['Win Rate (%)']}% | PF: {res['Profit Factor']} | Max DD: {res['Max Drawdown (%)']}% | Net Profit: ${res['Net Profit ($)']} | Avg SL: ${avg_sl:.2f} pts | Avg TP: ${avg_tp:.2f} pts\n")

if __name__ == "__main__":
    test_mtf()
