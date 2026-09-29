import numpy as np
import pandas as pd
import yfinance as yf
from tabulate import tabulate
from engine.backtester import BacktestEngine
from strategies.combo_strategies import strategy_dual_engine_fusion
from strategies.indicator_strategies import strategy_03_supertrend_ema
from strategies.smc_strategies import strategy_11_sweep_choch

def run_5m_gold_test():
    print("Fetching 5m Gold (GC=F) data...")
    df = yf.download('GC=F', interval='5m', period='60d', progress=False)
    
    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
        
    df.dropna(inplace=True)
    print(f"Loaded {len(df)} 5-minute candles for Gold (GC=F).")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    # Calculate typical ATR on 5m
    tr = np.maximum(df['high'] - df['low'], 
                    np.maximum(abs(df['high'] - df['close'].shift(1)), 
                               abs(df['low'] - df['close'].shift(1))))
    atr_5m = tr.rolling(14).mean().mean()
    print(f"Average 5m Candle ATR on Gold: ${atr_5m:.2f} per ounce")

    engine = BacktestEngine(
        initial_capital=100000.0,
        qty_pct=0.10,          # 10% equity sizing
        commission_pct=0.0003, # 0.03% broker commission
        slippage_pct=0.0001    # 1 tick slippage
    )

    tests = [
        ("Base Strategy 03: Supertrend + 200 EMA (5m)", strategy_03_supertrend_ema(df)),
        ("Base Strategy 11: Sweep + CHOCH (5m)", strategy_11_sweep_choch(df)),
        ("Dual-Engine Fusion 5m (Swing=5, SL=1.0x ATR, RR=1.5)", strategy_dual_engine_fusion(df, swing_len=5, rr=1.5, sl_atr_mult=1.0, cooldown_bars=6)),
        ("Dual-Engine Fusion 5m (Swing=5, SL=1.2x ATR, RR=1.5)", strategy_dual_engine_fusion(df, swing_len=5, rr=1.5, sl_atr_mult=1.2, cooldown_bars=6)),
        ("Dual-Engine Fusion 5m (Swing=7, SL=1.5x ATR, RR=2.0)", strategy_dual_engine_fusion(df, swing_len=7, rr=2.0, sl_atr_mult=1.5, cooldown_bars=12)),
        ("Dual-Engine Fusion 5m (Swing=10, SL=1.2x ATR, RR=2.0)", strategy_dual_engine_fusion(df, swing_len=10, rr=2.0, sl_atr_mult=1.2, cooldown_bars=12)),
        ("Dual-Engine Fusion 5m (Swing=12, SL=1.0x ATR, RR=2.5)", strategy_dual_engine_fusion(df, swing_len=12, rr=2.5, sl_atr_mult=1.0, cooldown_bars=15)),
    ]

    results = []
    trade_samples = {}
    for name, sigs in tests:
        metrics = engine.execute_backtest(df, name, sigs)
        results.append(metrics)
        # Record sample trade SL point distance
        trades = engine.trades
        if trades:
            sl_distances = [abs(t.entry_price - t.exit_price) for t in trades if t.exit_reason == 'Stop Loss']
            avg_sl = np.mean(sl_distances) if sl_distances else 0.0
            trade_samples[name] = {
                "avg_sl_pts": round(avg_sl, 2),
                "total_sl_trades": len(sl_distances),
                "total_trades": len(trades)
            }

    res_df = pd.DataFrame(results)
    print("\n" + "="*90)
    print(" 5-MINUTE TIMEFRAME BACKTEST RESULTS ON GOLD (GC=F, Last 60 Days)")
    print("="*90)
    print(tabulate(
        res_df[["Strategy", "Total Trades", "Win Rate (%)", "Net Profit ($)", "Return (%)", "Profit Factor", "Sharpe Ratio", "Max Drawdown (%)", "OOS Win Rate (%)"]],
        headers="keys",
        tablefmt="github",
        showindex=False
    ))

    print("\n" + "="*90)
    print(" STOP LOSS POINT DISTANCE COMPARISON ON 5M")
    print("="*90)
    for name, info in trade_samples.items():
        print(f"• {name}: Average Stop Loss Distance = ${info['avg_sl_pts']} points (across {info['total_sl_trades']} stop-out events)")

if __name__ == "__main__":
    run_5m_gold_test()
