import yfinance as yf
import pandas as pd
import numpy as np
from tabulate import tabulate
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr

def search_5m_high_winrate():
    print("Loading 5m Gold data (60 days)...")
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
    
    # HTF Alignment: Supertrend Bullish + Close > EMA50
    htf_bull_strong = ((df_1h['close'] > htf_ema50) & (st_dir_1h < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    htf_bear_strong = ((df_1h['close'] < htf_ema50) & (st_dir_1h > 0)).reindex(df_5m.index, method='ffill').fillna(False)
    
    atr_5m = calculate_atr(df_5m, 14)
    n = len(df_5m)
    
    engine = BacktestEngine(100000.0, qty_pct=0.10, commission_pct=0.0003, slippage_pct=0.0001)
    
    # Parameter grid search
    experiments = []
    print("Testing 5M Gold Elite Parameter Matrix...")
    
    for swing_len in [5, 7]:
        ph, pl = calculate_pivots(df_5m, swing_len, swing_len)
        
        for max_sl in [5.0, 7.0, 8.0, 10.0]:
            for rr in [0.8, 1.0, 1.2, 1.5, 2.0]:
                for cd in [4, 6, 10]:
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
                        a = atr_5m.iloc[i] if not np.isnan(atr_5m.iloc[i]) else 2.5
                        
                        # Bullish Liquidity Sweep into 1H Bullish Trend
                        if bool(htf_bull_strong.iloc[i]) and not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o):
                            raw_risk = max(c - l, a * 1.0)
                            risk = min(raw_risk, max_sl)
                            long_entry[i] = True
                            sl[i] = c - risk
                            tp[i] = c + (risk * rr)
                            last_idx = i
                            
                        # Bearish Liquidity Sweep into 1H Bearish Trend
                        elif bool(htf_bear_strong.iloc[i]) and not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o):
                            raw_risk = max(h - c, a * 1.0)
                            risk = min(raw_risk, max_sl)
                            short_entry[i] = True
                            sl[i] = c + risk
                            tp[i] = c - (risk * rr)
                            last_idx = i
                            
                    sigs = pd.DataFrame({
                        'long_entry': long_entry,
                        'short_entry': short_entry,
                        'long_exit': False,
                        'short_exit': False,
                        'stop_loss': sl,
                        'take_profit': tp
                    }, index=df_5m.index)
                    
                    metrics = engine.execute_backtest(df_5m, f"Gold_5M_SL{max_sl}_RR{rr}_CD{cd}", sigs)
                    
                    if metrics['Total Trades'] >= 15:
                        experiments.append({
                            'Swing': swing_len,
                            'MaxSL': max_sl,
                            'RR': rr,
                            'Cooldown': cd,
                            'Trades': metrics['Total Trades'],
                            'WinRate (%)': metrics['Win Rate (%)'],
                            'ProfitFactor': metrics['Profit Factor'],
                            'NetProfit ($)': metrics['Net Profit ($)'],
                            'Return (%)': metrics['Return (%)'],
                            'MaxDD (%)': metrics['Max Drawdown (%)']
                        })
                        
    if experiments:
        exp_df = pd.DataFrame(experiments)
        # Sort by Win Rate
        sorted_wr = exp_df.sort_values(by=['WinRate (%)', 'NetProfit ($)'], ascending=[False, False]).reset_index(drop=True)
        print("\n" + "="*85)
        print(" TOP 15 GOLD ELITE 5M SETUPS RANKED BY WIN RATE")
        print("="*85)
        print(tabulate(sorted_wr.head(15), headers="keys", tablefmt="github", showindex=True))
        
        # Sort by Net Profit
        sorted_pnl = exp_df.sort_values(by=['NetProfit ($)', 'WinRate (%)'], ascending=[False, False]).reset_index(drop=True)
        print("\n" + "="*85)
        print(" TOP 10 GOLD ELITE 5M SETUPS RANKED BY NET PROFIT")
        print("="*85)
        print(tabulate(sorted_pnl.head(10), headers="keys", tablefmt="github", showindex=True))
        return sorted_wr
    else:
        print("No valid experiments completed.")
        return None

def gold_elite_strategy(df: pd.DataFrame, swing_len: int = 5, max_sl: float = 8.0, rr: float = 1.0, cooldown: int = 6) -> pd.DataFrame:
    """Production Gold Elite 5M Strategy Function"""
    df_1h = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    htf_ema50 = calculate_ema(df_1h['close'], 50)
    st_val_1h, st_dir_1h = calculate_supertrend(df_1h, 10, 3.0)
    htf_bull_strong = ((df_1h['close'] > htf_ema50) & (st_dir_1h < 0)).reindex(df.index, method='ffill').fillna(False)
    htf_bear_strong = ((df_1h['close'] < htf_ema50) & (st_dir_1h > 0)).reindex(df.index, method='ffill').fillna(False)
    
    ph, pl = calculate_pivots(df, swing_len, swing_len)
    atr = calculate_atr(df, 14)
    n = len(df)
    
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
        
        if (i - last_idx) < cooldown: continue
        hour = df.index[i].hour if isinstance(df.index, pd.DatetimeIndex) else 10
        if not (7 <= hour < 18): continue
        
        c = df['close'].iloc[i]
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        a = atr.iloc[i] if not np.isnan(atr.iloc[i]) else 2.5
        
        if bool(htf_bull_strong.iloc[i]) and not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o):
            risk = min(max(c - l, a * 1.0), max_sl)
            long_entry[i] = True
            sl[i] = c - risk
            tp[i] = c + (risk * rr)
            last_idx = i
        elif bool(htf_bear_strong.iloc[i]) and not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o):
            risk = min(max(h - c, a * 1.0), max_sl)
            short_entry[i] = True
            sl[i] = c + risk
            tp[i] = c - (risk * rr)
            last_idx = i
            
    return pd.DataFrame({
        'long_entry': long_entry,
        'short_entry': short_entry,
        'long_exit': False,
        'short_exit': False,
        'stop_loss': sl,
        'take_profit': tp
    }, index=df.index)

if __name__ == '__main__':
    search_5m_high_winrate()
