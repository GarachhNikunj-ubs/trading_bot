import numpy as np
import pandas as pd
from tabulate import tabulate
from engine.data import load_or_fetch_data
from engine.backtester import BacktestEngine
from strategies.combo_strategies import strategy_dual_engine_fusion
from strategies.indicator_strategies import strategy_03_supertrend_ema
from strategies.smc_strategies import strategy_11_sweep_choch

def run_fusion_comparison(symbol: str = "GC=F"):
    print("\n" + "="*80)
    print(f" DUAL-ENGINE FUSION VS INDIVIDUAL STRATEGIES BENCHMARK ({symbol})")
    print("="*80)
    
    df_raw = load_or_fetch_data(symbol, interval="1h", period="730d")
    df_raw.index = pd.to_datetime(df_raw.index, utc=True)
    
    # Also create 4H resampled data
    df_4h = df_raw.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    engine = BacktestEngine(
        initial_capital=100000.0,
        qty_pct=0.10,          # 10% equity sizing
        commission_pct=0.0003, # 0.03% broker commission
        slippage_pct=0.0001    # 1 tick slippage
    )

    tests = [
        # Individual Strategies
        ("Strategy 03: Supertrend + 200 EMA (1H)", df_raw, strategy_03_supertrend_ema(df_raw)),
        ("Strategy 11: Liquidity Sweep + CHOCH (1H)", df_raw, strategy_11_sweep_choch(df_raw)),
        
        # New Dual-Engine Fusion on 1H
        ("✨ Dual-Engine Fusion (1H, RR 1.5)", df_raw, strategy_dual_engine_fusion(df_raw, swing_len=7, rr=1.5, sl_atr_mult=1.5, cooldown_bars=8)),
        ("✨ Dual-Engine Fusion (1H, RR 2.0)", df_raw, strategy_dual_engine_fusion(df_raw, swing_len=7, rr=2.0, sl_atr_mult=1.5, cooldown_bars=8)),
        ("✨ Dual-Engine Fusion (1H, Swing=10, RR 2.0)", df_raw, strategy_dual_engine_fusion(df_raw, swing_len=10, rr=2.0, sl_atr_mult=1.5, cooldown_bars=10)),

        # New Dual-Engine Fusion on 4H
        ("Strategy 03: Supertrend + 200 EMA (4H)", df_4h, strategy_03_supertrend_ema(df_4h)),
        ("✨ Dual-Engine Fusion (4H, Swing=5, RR 1.8)", df_4h, strategy_dual_engine_fusion(df_4h, swing_len=5, rr=1.8, sl_atr_mult=1.5, cooldown_bars=4)),
        ("✨ Dual-Engine Fusion (4H, Swing=7, RR 2.0)", df_4h, strategy_dual_engine_fusion(df_4h, swing_len=7, rr=2.0, sl_atr_mult=1.5, cooldown_bars=4)),
    ]

    results = []
    for name, data, sigs in tests:
        metrics = engine.execute_backtest(data, name, sigs)
        results.append(metrics)

    res_df = pd.DataFrame(results)
    
    print("\n" + tabulate(
        res_df[["Strategy", "Total Trades", "Win Rate (%)", "Net Profit ($)", "Return (%)", "Profit Factor", "Sharpe Ratio", "Max Drawdown (%)", "OOS Win Rate (%)"]],
        headers="keys",
        tablefmt="github",
        showindex=False
    ))
    return res_df

if __name__ == "__main__":
    run_fusion_comparison("GC=F")
