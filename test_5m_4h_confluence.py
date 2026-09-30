import yfinance as yf
import pandas as pd
import numpy as np
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr

def test_5m_4h_confluence():
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    # 4H Macro Trend
    df_4h = df_5m.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    htf_ema50_4h = calculate_ema(df_4h['close'], 50)
    st_val_4h, st_dir_4h = calculate_supertrend(df_4h, 10, 3.0)

    # 1H Trend
    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    htf_ema50_1h = calculate_ema(df_1h['close'], 50)
    st_val_1h, st_dir_1h = calculate_supertrend(df_1h, 10, 3.0)

    # Master Institutional Confluence: 4H + 1H both Bullish or Bearish
    master_bull = ((df_4h['close'] > htf_ema50_4h) & (st_dir_4h < 0)).reindex(df_5m.index, method='ffill').fillna(False) & \
                  ((df_1h['close'] > htf_ema50_1h) & (st_dir_1h < 0)).reindex(df_5m.index, method='ffill').fillna(False)
                  
    master_bear = ((df_4h['close'] < htf_ema50_4h) & (st_dir_4h > 0)).reindex(df_5m.index, method='ffill').fillna(False) & \
                  ((df_1h['close'] < htf_ema50_1h) & (st_dir_1h > 0)).reindex(df_5m.index, method='ffill').fillna(False)

    atr_5m = calculate_atr(df_5m, 14)
    
    high = df_5m['high'].values
    low = df_5m['low'].values
    close = df_5m['close'].values
    open_p = df_5m['open'].values
    n = len(df_5m)

    for swing in [5, 7, 10, 12]:
        ph, pl = calculate_pivots(df_5m, swing, swing)
        
        for target_r in [1.0, 1.2, 1.5, 2.0]:
            for be_pct in [0.7, 0.8, 1.0]:
                trades = []
                s_low = np.nan
                s_high = np.nan
                last_t = -999

                for i in range(100, n):
                    if not np.isnan(pl.iloc[i]): s_low = pl.iloc[i]
                    if not np.isnan(ph.iloc[i]): s_high = ph.iloc[i]

                    if (i - last_t) < 12: continue

                    hour = df_5m.index[i].hour
                    if not (7 <= hour < 18): continue

                    c, o, h, l = close[i], open_p[i], high[i], low[i]
                    a = atr_5m.iloc[i]

                    # SMC Sweep Rejection
                    sweep_l = not np.isnan(s_low) and (l < s_low) and (c > s_low) and (c > o)
                    sweep_s = not np.isnan(s_high) and (h > s_high) and (c < s_high) and (c < o)

                    if bool(master_bull.iloc[i]) and sweep_l:
                        risk = min(max(c - l, a * 1.0), 8.0) # Tight $8 SL
                        entry = c
                        sl = entry - risk
                        tp = entry + (risk * target_r)
                        be_price = entry + (risk * be_pct)

                        hit_be = False
                        pnl = 0.0
                        for j in range(i+1, min(i+100, n)):
                            if high[j] >= be_price and not hit_be:
                                hit_be = True
                                sl = entry + 0.30 # Breakeven plus fees

                            if high[j] >= tp:
                                pnl = tp - entry
                                break
                            elif low[j] <= sl:
                                pnl = sl - entry
                                break
                        trades.append(pnl)
                        last_t = i

                    elif bool(master_bear.iloc[i]) and sweep_s:
                        risk = min(max(h - c, a * 1.0), 8.0)
                        entry = c
                        sl = entry + risk
                        tp = entry - (risk * target_r)
                        be_price = entry - (risk * be_pct)

                        hit_be = False
                        pnl = 0.0
                        for j in range(i+1, min(i+100, n)):
                            if low[j] <= be_price and not hit_be:
                                hit_be = True
                                sl = entry - 0.30

                            if low[j] <= tp:
                                pnl = entry - tp
                                break
                            elif high[j] >= sl:
                                pnl = entry - sl
                                break
                        trades.append(pnl)
                        last_t = i

                if len(trades) >= 10:
                    wins = [p for p in trades if p > 0]
                    wr = (len(wins) / len(trades)) * 100.0
                    if wr >= 65.0:
                        print(f"★ HIGH WIN RATE FOUND! Swing: {swing} | Target: {target_r}R | BE: {be_pct}R | Trades: {len(trades)} | Win Rate: {wr:.1f}% | Net PnL (pts): {sum(trades):.1f}")

if __name__ == "__main__":
    test_5m_4h_confluence()
