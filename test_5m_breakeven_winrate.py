import yfinance as yf
import pandas as pd
import numpy as np
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr

def test_5m_advanced_protection():
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    # 1H HTF Trend Filter
    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    htf_ema50 = calculate_ema(df_1h['close'], 50)
    htf_st_val, htf_st_dir = calculate_supertrend(df_1h, 10, 3.0)

    htf_bull = ((df_1h['close'] > htf_ema50) & (htf_st_dir < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    htf_bear = ((df_1h['close'] < htf_ema50) & (htf_st_dir > 0)).reindex(df_5m.index, method='ffill').fillna(False)

    atr_5m = calculate_atr(df_5m, 14)
    ph, pl = calculate_pivots(df_5m, 8, 8)
    
    n = len(df_5m)
    high = df_5m['high'].values
    low = df_5m['low'].values
    close = df_5m['close'].values
    open_p = df_5m['open'].values

    # Test varying target multipliers with Breakeven protection
    for be_trigger in [0.7, 0.8, 1.0]:
        for target_r in [1.0, 1.2, 1.5, 1.8]:
            trades = []
            s_low = np.nan
            s_high = np.nan
            last_trade = -999

            for i in range(100, n):
                if not np.isnan(pl.iloc[i]): s_low = pl.iloc[i]
                if not np.isnan(ph.iloc[i]): s_high = ph.iloc[i]

                if (i - last_trade) < 12: continue

                hour = df_5m.index[i].hour
                if not (7 <= hour < 18): continue

                c = close[i]
                o = open_p[i]
                h = high[i]
                l = low[i]
                a = atr_5m.iloc[i]

                sweep_bull = not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o)
                sweep_bear = not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o)

                if bool(htf_bull.iloc[i]) and sweep_bull:
                    risk = min(max(c - l, a * 1.0), 8.0) # $8 max SL
                    entry = c
                    sl = entry - risk
                    tp = entry + (risk * target_r)
                    be_level = entry + (risk * be_trigger)
                    
                    # Simulate trade execution candle by candle
                    hit_be = False
                    outcome = None
                    pnl = 0.0
                    for j in range(i+1, min(i+100, n)):
                        # Check high/low
                        if high[j] >= be_level and not hit_be:
                            hit_be = True
                            sl = entry + 0.50 # Move stop to Breakeven (+0.50 for commission)

                        if high[j] >= tp:
                            outcome = 'WIN'
                            pnl = tp - entry
                            break
                        elif low[j] <= sl:
                            if hit_be:
                                outcome = 'BE_WIN'
                                pnl = sl - entry
                            else:
                                outcome = 'LOSS'
                                pnl = sl - entry
                            break
                    
                    if outcome:
                        trades.append({'outcome': outcome, 'pnl': pnl})
                        last_trade = i

                elif bool(htf_bear.iloc[i]) and sweep_bear:
                    risk = min(max(h - c, a * 1.0), 8.0)
                    entry = c
                    sl = entry + risk
                    tp = entry - (risk * target_r)
                    be_level = entry - (risk * be_trigger)

                    hit_be = False
                    outcome = None
                    pnl = 0.0
                    for j in range(i+1, min(i+100, n)):
                        if low[j] <= be_level and not hit_be:
                            hit_be = True
                            sl = entry - 0.50 # Move stop to Breakeven

                        if low[j] <= tp:
                            outcome = 'WIN'
                            pnl = entry - tp
                            break
                        elif high[j] >= sl:
                            if hit_be:
                                outcome = 'BE_WIN'
                                pnl = entry - sl
                            else:
                                outcome = 'LOSS'
                                pnl = entry - sl
                            break
                    if outcome:
                        trades.append({'outcome': outcome, 'pnl': pnl})
                        last_trade = i

            total = len(trades)
            if total > 0:
                wins = [t for t in trades if t['pnl'] > 0]
                losses = [t for t in trades if t['pnl'] < 0]
                win_rate = (len(wins) / total) * 100.0
                net_pnl = sum([t['pnl'] for t in trades])
                print(f"BE Trigger: {be_trigger}R | Target: {target_r}R | Trades: {total} | Win Rate: {win_rate:.1f}% | Net PnL (pts): {net_pnl:.1f}")

if __name__ == "__main__":
    test_5m_advanced_protection()
