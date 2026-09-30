import yfinance as yf
import pandas as pd
import numpy as np
from engine.indicators import calculate_ema, calculate_supertrend, calculate_atr, calculate_rsi

def test_5m_setups():
    print("Downloading 5m Gold data...")
    df = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    df.dropna(inplace=True)

    # 1H HTF Trend Confluence
    df_1h = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    ema50_1h = calculate_ema(df_1h['close'], 50)
    st_v_1h, st_d_1h = calculate_supertrend(df_1h, 10, 3.0)

    bull_1h = ((df_1h['close'] > ema50_1h) & (st_d_1h < 0)).reindex(df.index, method='ffill').fillna(False)
    bear_1h = ((df_1h['close'] < ema50_1h) & (st_d_1h > 0)).reindex(df.index, method='ffill').fillna(False)

    df['ema21'] = calculate_ema(df['close'], 21)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['ema200'] = calculate_ema(df['close'], 200)
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    opens = df['open'].values
    rsi = df['rsi'].values
    ema21 = df['ema21'].values
    ema50 = df['ema50'].values
    ema200 = df['ema200'].values
    times = df.index
    n = len(df)

    matches = []

    # Test parameter combinations
    for tp_pts in [4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0]:
        for sl_pts in [4.0, 5.0, 6.0, 7.0, 8.0]:
            for rsi_buy, rsi_sell in [(42, 58), (38, 62), (35, 65), (45, 55), (30, 70)]:
                for hours_filter in [(7, 18), (8, 16), (12, 17)]:
                    trades = []
                    last_idx = -999
                    for i in range(200, n - 30):
                        if (i - last_idx) < 4:
                            continue
                        h = times[i].hour
                        if not (hours_filter[0] <= h <= hours_filter[1]):
                            continue

                        c = closes[i]
                        o = opens[i]
                        l = lows[i]
                        hp = highs[i]
                        r = rsi[i]

                        # Multi-timeframe trend confluence:
                        # 1H Bullish AND 5m Close > 50 EMA AND 5m Close > 200 EMA
                        is_bull = bool(bull_1h.iloc[i]) and (c > ema200[i]) and (ema50[i] > ema200[i])
                        is_bear = bool(bear_1h.iloc[i]) and (c < ema200[i]) and (ema50[i] < ema200[i])

                        # Pullback into EMA21 value zone with rejection candle
                        long_cond = is_bull and (l <= ema21[i] or l <= ema50[i]) and (r <= rsi_buy) and (c > o) and (c > ema21[i])
                        short_cond = is_bear and (hp >= ema21[i] or hp >= ema50[i]) and (r >= rsi_sell) and (c < o) and (c < ema21[i])

                        direction = 'LONG' if long_cond else ('SHORT' if short_cond else None)
                        if direction is None:
                            continue

                        entry = c
                        sl = entry - sl_pts if direction == 'LONG' else entry + sl_pts
                        tp = entry + tp_pts if direction == 'LONG' else entry - tp_pts

                        outcome = None
                        exit_price = None
                        for k in range(i + 1, min(i + 60, n)):
                            kl = lows[k]
                            kh = highs[k]
                            ko = opens[k]
                            if direction == 'LONG':
                                if kl <= sl:
                                    outcome = 'LOSS'
                                    exit_price = min(ko, sl)
                                    break
                                elif kh >= tp:
                                    outcome = 'WIN'
                                    exit_price = max(ko, tp)
                                    break
                            else:
                                if kh >= sl:
                                    outcome = 'LOSS'
                                    exit_price = max(ko, sl)
                                    break
                                elif kl <= tp:
                                    outcome = 'WIN'
                                    exit_price = min(ko, tp)
                                    break

                        if outcome is not None:
                            last_idx = i
                            oz = 10000.0 / entry
                            pnl_gross = (exit_price - entry)*oz if direction == 'LONG' else (entry - exit_price)*oz
                            comm = (entry*oz + exit_price*oz) * 0.0003
                            pnl_net = pnl_gross - comm
                            trades.append({'outcome': outcome, 'pnl_net': pnl_net})

                    if len(trades) >= 25:
                        wins = [t for t in trades if t['outcome'] == 'WIN']
                        wr = len(wins) / len(trades) * 100
                        net = sum(t['pnl_net'] for t in trades)
                        win_sum = sum(t['pnl_net'] for t in wins)
                        loss_sum = abs(sum(t['pnl_net'] for t in trades if t['outcome'] == 'LOSS'))
                        pf = (win_sum / loss_sum) if loss_sum > 0 else 99
                        if wr >= 65.0 and net > 0:
                            matches.append({
                                'TP': tp_pts,
                                'SL': sl_pts,
                                'RSI': f"{rsi_buy}/{rsi_sell}",
                                'Hours': f"{hours_filter[0]}-{hours_filter[1]}",
                                'Trades': len(trades),
                                'WinRate': round(wr, 1),
                                'NetProfit': round(net, 2),
                                'PF': round(pf, 2)
                            })

    if matches:
        res_df = pd.DataFrame(matches)
        print(f"\nFound {len(res_df)} setups with Win Rate >= 65% and Net Profit > 0:")
        print(res_df.sort_values(by=['WinRate', 'NetProfit'], ascending=[False, False]).head(25).to_string(index=False))
    else:
        print("No matches found above 65% WR.")

if __name__ == '__main__':
    test_5m_setups()
