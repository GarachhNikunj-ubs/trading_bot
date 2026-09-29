import numpy as np
import pandas as pd
from tabulate import tabulate
from engine.data import load_or_fetch_data
from engine.backtester import BacktestEngine
from strategies.gold_elite_strategy import gold_elite_trend_pullback

def test_gold_configurations():
    print("\n=================================================================")
    print(" BACKTESTING HIGH-PRECISION GOLD (GC=F / XAUUSD) STRATEGY (2-3 YRS)")
    print("=================================================================")
    df = load_or_fetch_data(symbol="GC=F", interval="1h", period="730d")
    print(f"Total Hourly Bars: {len(df)} | Start: {df.index[0]} | End: {df.index[-1]}")
    
    engine = BacktestEngine(
        initial_capital=100000.0,
        qty_pct=0.10,          # 10% equity sizing
        commission_pct=0.0003, # 0.03% broker commission
        slippage_pct=0.0001    # 1 tick slippage
    )
    
    configs = [
        {"name": "Conservative Elite (TP 1.5R, SL 1.0R, ADX > 25)", "tp": 1.5, "sl": 1.0, "adx": 25.0},
        {"name": "High Precision (TP 1.4R, SL 1.0R, ADX > 22)", "tp": 1.4, "sl": 1.0, "adx": 22.0},
        {"name": "Ultra Win-Rate (TP 1.2R, SL 1.0R, ADX > 22)", "tp": 1.2, "sl": 1.0, "adx": 22.0},
        {"name": "Asymmetric Elite (TP 1.8R, SL 1.0R, ADX > 25)", "tp": 1.8, "sl": 1.0, "adx": 25.0},
        {"name": "Selective Filter (TP 1.5R, SL 1.1R, ADX > 28)", "tp": 1.5, "sl": 1.1, "adx": 28.0},
    ]
    
    results = []
    
    for cfg in configs:
        signals = gold_elite_trend_pullback(
            df,
            adx_threshold=cfg["adx"],
            tp_mult=cfg["tp"],
            sl_mult=cfg["sl"]
        )
        res = engine.execute_backtest(df, cfg["name"], signals)
        results.append(res)
        
    res_df = pd.DataFrame(results)
    ranked = res_df.sort_values(by="Win Rate (%)", ascending=False).reset_index(drop=True)
    
    print("\n" + "="*100)
    print(" GOLD HIGH-PRECISION STRATEGY AUDIT (Ranked by Win Rate %)")
    print("="*100)
    print(tabulate(
        ranked[["Strategy", "Total Trades", "Win Rate (%)", "Net Profit ($)", "Return (%)", "Profit Factor", "Sharpe Ratio", "Max Drawdown (%)", "OOS Win Rate (%)"]],
        headers="keys",
        tablefmt="github",
        showindex=True
    ))
    return ranked

if __name__ == "__main__":
    test_gold_configurations()
