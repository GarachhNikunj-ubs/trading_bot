import yfinance as yf
import pandas as pd
import numpy as np
from tabulate import tabulate
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr

def search_5m_high_winrate():
    print("Loading 5m Gold data...")
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    # 1H HTF Trend Filter
    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    htf_ema50 = calculate_ema(df_1h['close'], 50)
    htf_ema200 = calculate_ema(df_1h['close'], 200)
    st_val_1h, st_dir_1h = calculate_supertrend(df_1h, 10, 3.0)

    # HTF Alignment
    htf_bull_strong = ((df_1h['close'] > htf_ema50) & (df_1h['close'] > htf_ema200) & (st_dir_1h < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    htf_bear_strong = ((df_1h['close'] < htf_ema50) & (df_1h['close'] < htf_ema200) & (st_dir_1h > 0)).reindex(df_5m.index, method='ffill').fillna(False)

    atr_5m = calculate_atr(df_5m, 14)
    n = len(df_5m)

    # Parameter grid search
    experiments = []

    for swing_len in [5, 7, 10]:
        ph, pl = calculate_pivots(df_5m, swing_len, swing_len)
        
        for max_sl in [6.0, 8.0, 10.0]:
            for rr in [1.0, 1.1, 1.2, 1.3, 1.5]:
                for cd in [6, 12, 18]:
                    long_entry = [False] * n
                    short_entry = [False] * n
                    sl = [np.nan] * n
                    tp = [np.nan] * n
                    
                    s_low = np.nan
                    s_high = np.nan
                    last_idx = -999
                    
                    for i in range(100, n):
                        if not np.isnan(pl.iloc[i]): s_low = pl.iloc[i]
                        if not np.isnan(ph.iloc[i]): s_high = ph.iloc[i]
                        
                        if (i - last_idx) < cd: continue
                        
                        # Session Filter: London + NY (07:00 to 18:00 UTC)
                        hour = df_5m.index[i].hour
                        if not (7 <= hour < 18): continue
                        
                        c = df_5m['close'].iloc[i]
                        o = df_5m['open'].iloc[i]
                        h = df_5m['high'].iloc[i]
                        l = df_5m['low'].iloc[i]
                        a = atr_5m.iloc[i]
                        
                        # Strong SMC Liquidity Sweep with Confirmation Body
                        sweep_bull = not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o) and ((c - l) > (h - c))
                        sweep_bear = not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o) and ((h - c) > (c - l))
                        
                        if bool(htf_bull_strong.iloc[i]) and sweep_bull:
                            risk = min(max(c - l, a * 1.0), max_sl)
                            long_entry[i] = True
                            sl[i] = c - risk
                            tp[i] = c + (risk * rr)
                            last_idx = i
                        elif bool(htf_bear_strong.iloc[i]) and sweep_bear:
                            risk = min(max(h - c, a * 1.0), max_sl)
                            short_entry[i] = True
                            sl[i] = c + risk
                            tp[i] = c - (risk * rr)
                            last_idx = i
                            
                    sigs = pd.DataFrame({'long_entry': long_entry, 'short_entry': short_entry, 'stop_loss': sl, 'take_profit': tp}, index=df_5m.index)
                    sigs['long_exit'] = False
                    sigs['short_exit'] = False
                    
                    eng = BacktestEngine(100000.0, qty_pct=0.10, commission_pct=0.0003, slippage_pct=0.0001)
                    res = eng.execute_backtest(df_5m, f"Swing={swing_len}_SL={max_sl}_RR={rr}_CD={cd}", sigs)
                    
                    if res["Total Trades"] >= 15:
                        experiments.append({
                            "swing_len": swing_len,
                            "max_sl": max_sl,
                            "rr": rr,
                            "cooldown": cd,
                            "trades": res["Total Trades"],
                            "win_rate": res["Win Rate (%)"],
                            "profit_factor": res["Profit Factor"],
                            "net_profit": res["Net Profit ($)"],
                            "max_dd": res["Max Drawdown (%)"]
                        })

    df_exp = pd.DataFrame(experiments)
    if not df_exp.empty:
        # Sort by Win Rate descending
        df_sorted = df_exp.sort_values(by="win_rate", ascending=False)
        print("\n" + "="*90)
        print(" TOP 10 HIGHEST WIN RATE CONFIGURATIONS ON 5M GOLD")
        print("="*90)
        print(tabulate(df_sorted.head(15), headers="keys", tablefmt="github", showindex=False))
        return df_sorted
    else:
        print("No configurations met minimum trade threshold.")
        return None

if __name__ == "__main__":
    search_5m_high_winrate()
