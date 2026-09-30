import yfinance as yf
import pandas as pd
import numpy as np
from engine.indicators import calculate_ema, calculate_supertrend, calculate_atr, calculate_rsi

def test_strategies():
    print("Fetching 5m Gold data...")
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)
    
    # Precompute indicators
    df_1h = df_5m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    ema_1h_50 = calculate_ema(df_1h['close'], 50)
    ema_1h_200 = calculate_ema(df_1h['close'], 200)
    st_1h_v, st_1h_d = calculate_supertrend(df_1h, 10, 3.0)
    
    bull_1h = ((df_1h['close'] > ema_1h_50) & (st_1h_d < 0)).reindex(df_5m.index, method='ffill').fillna(False)
    bear_1h = ((df_1h['close'] < ema_1h_50) & (st_1h_d > 0)).reindex(df_5m.index, method='ffill').fillna(False)
    
    df_5m['ema20'] = calculate_ema(df_5m['close'], 20)
    df_5m['ema50'] = calculate_ema(df_5m['close'], 50)
    df_5m['ema200'] = calculate_ema(df_5m['close'], 200)
    df_5m['rsi'] = calculate_rsi(df_5m['close'], 14)
    df_5m['atr'] = calculate_atr(df_5m, 14)
    
    opens = df_5m['open'].values
    highs = df_5m['high'].values
    lows = df_5m['low'].values
    closes = df_5m['close'].values
    rsi = df_5m['rsi'].values
    atr = df_5m['atr'].values
    ema20 = df_5m['ema20'].values
    ema50 = df_5m['ema50'].values
    ema200 = df_5m['ema200'].values
    times = df_5m.index
    n = len(df_5m)
    
    results = []
    
    # Test Strategy Frameworks:
    # 1. SMC Liquidity Sweep + Rejection + Trend Confluence
    # 2. Institutional Fair Value Gap (FVG) / Order Block retracement
    # 3. Dynamic Scalp with Trailing / Target ratios
    
    for session_filter in ['all', 'london_ny', 'overlap']:
        for rr_target in [0.75, 1.0, 1.25, 1.5, 2.0]:
            for sl_cap in [5.0, 6.0, 7.0, 8.0]:
                for min_wick_ratio in [1.2, 1.5, 1.8]:
                    for rsi_thresh in [35, 40, 45]:
                        trades = []
                        last_bar = -999
                        
                        for i in range(200, n - 50):
                            if (i - last_bar) < 6:
                                continue
                            
                            h_utc = times[i].hour
                            if session_filter == 'london_ny' and not (7 <= h_utc <= 18):
                                continue
                            if session_filter == 'overlap' and not (12 <= h_utc <= 17):
                                continue
                            
                            c = closes[i]
                            o = opens[i]
                            h = highs[i]
                            l = lows[i]
                            cur_atr = atr[i]
                            if np.isnan(cur_atr) or cur_atr <= 0:
                                continue
                            
                            body = abs(c - o)
                            lower_wick = min(c, o) - l
                            upper_wick = h - max(c, o)
                            
                            # Swing lookback for sweep
                            sw_low = np.min(lows[max(0, i-10):i])
                            sw_high = np.max(highs[max(0, i-10):i])
                            
                            # Bullish setup:
                            # 1) HTF Bullish (1H > EMA50 or 5m > EMA200)
                            # 2) Liquidity sweep of recent swing low (l < sw_low)
                            # 3) Strong rejection wick (lower_wick >= min_wick_ratio * body)
                            # 4) Bullish close (c > o)
                            # 5) RSI oversold recovery
                            is_bull_trend = (c > ema200[i]) and bool(bull_1h.iloc[i])
                            is_bear_trend = (c < ema200[i]) and bool(bear_1h.iloc[i])
                            
                            is_bull_sweep = (l <= sw_low) and (lower_wick >= min_wick_ratio * max(body, 0.2)) and (c > o) and (rsi[i] < (100 - rsi_thresh))
                            is_bear_sweep = (h >= sw_high) and (upper_wick >= min_wick_ratio * max(body, 0.2)) and (c < o) and (rsi[i] > rsi_thresh)
                            
                            direction = None
                            entry_p = c
                            sl_p = None
                            tp_p = None
                            risk = 0.0
                            
                            if is_bull_trend and is_bull_sweep:
                                direction = 'LONG'
                                risk = min(max(c - l + 0.5, 3.5), sl_cap)
                                sl_p = entry_p - risk
                                tp_p = entry_p + (risk * rr_target)
                            elif is_bear_trend and is_bear_sweep:
                                direction = 'SHORT'
                                risk = min(max(h - c + 0.5, 3.5), sl_cap)
                                sl_p = entry_p + risk
                                tp_p = entry_p - (risk * rr_target)
                                
                            if direction is not None:
                                # Forward simulate trade
                                outcome = None
                                exit_p = None
                                for k in range(i + 1, min(i + 120, n)): # max 10 hours
                                    kh = highs[k]
                                    kl = lows[k]
                                    ko = opens[k]
                                    
                                    if direction == 'LONG':
                                        if kl <= sl_p:
                                            outcome = 'LOSS'
                                            exit_p = min(ko, sl_p)
                                            break
                                        elif kh >= tp_p:
                                            outcome = 'WIN'
                                            exit_p = max(ko, tp_p)
                                            break
                                    else: # SHORT
                                        if kh >= sl_p:
                                            outcome = 'LOSS'
                                            exit_p = max(ko, sl_p)
                                            break
                                        elif kl <= tp_p:
                                            outcome = 'WIN'
                                            exit_p = min(ko, tp_p)
                                            break
                                            
                                if outcome is not None:
                                    last_bar = i
                                    # Commission & slippage:
                                    # Pos size: $10,000 equity (approx 2.5 oz Gold)
                                    oz = 10000.0 / entry_p
                                    if direction == 'LONG':
                                        gross = (exit_p - entry_p) * oz
                                    else:
                                        gross = (entry_p - exit_p) * oz
                                    comm = (entry_p * oz + exit_p * oz) * 0.0003
                                    net = gross - comm
                                    trades.append({
                                        'direction': direction,
                                        'entry': entry_p,
                                        'exit': exit_p,
                                        'outcome': outcome,
                                        'net': net,
                                        'risk': risk,
                                        'profit_pts': exit_p - entry_p if direction == 'LONG' else entry_p - exit_p
                                    })
                                    
                        if len(trades) >= 20:
                            wins = [t for t in trades if t['outcome'] == 'WIN']
                            wr = len(wins) / len(trades) * 100.0
                            tot_net = sum(t['net'] for t in trades)
                            gross_win = sum(t['net'] for t in wins)
                            gross_loss = abs(sum(t['net'] for t in trades if t['outcome'] == 'LOSS'))
                            pf = (gross_win / gross_loss) if gross_loss > 0 else 99.0
                            avg_sl = np.mean([t['risk'] for t in trades])
                            avg_win_pts = np.mean([abs(t['profit_pts']) for t in wins]) if wins else 0
                            
                            results.append({
                                'session': session_filter,
                                'rr': rr_target,
                                'sl_cap': sl_cap,
                                'wick': min_wick_ratio,
                                'rsi': rsi_thresh,
                                'trades': len(trades),
                                'win_rate': wr,
                                'pf': pf,
                                'net_profit': tot_net,
                                'avg_sl': avg_sl,
                                'avg_win_pts': avg_win_pts
                            })
                            
    res_df = pd.DataFrame(results)
    if len(res_df) > 0:
        print(f"\nTested {len(res_df)} parameter combinations. Filtered for Win Rate >= 65% and Net Profit > 0:")
        high_wr = res_df[(res_df['win_rate'] >= 65.0) & (res_df['net_profit'] > 0)].sort_values('win_rate', ascending=False)
        print(high_wr.head(20).to_string(index=False))
        return high_wr
    else:
        print("No setups found meeting criteria.")
        return None

if __name__ == '__main__':
    test_strategies()
