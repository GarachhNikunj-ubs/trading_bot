import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from tabulate import tabulate
from engine.backtester import BacktestEngine
from engine.indicators import calculate_ema, calculate_supertrend, calculate_pivots, calculate_atr
from strategies.combo_strategies import strategy_dual_engine_fusion

def run_fused_smc_multitimeframe():
    print("="*90)
    print(" INSTITUTIONAL SMC + MACRO FILTER (POWER OF 3 + SWEEP + OB + 200 EMA)")
    print("="*90)

    # 1. Load 5m data (60d)
    print("Loading Gold 5m data...")
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    # 2. Resample to 15m
    df_15m = df_5m.resample('15min').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()

    # 3. Load 1h data (730d)
    print("Loading Gold 1h data...")
    df_1h = yf.download('GC=F', interval='1h', period='730d', progress=False)
    if isinstance(df_1h.columns, pd.MultiIndex):
        df_1h.columns = [c[0].lower() for c in df_1h.columns]
    else:
        df_1h.columns = [c.lower() for c in df_1h.columns]
    df_1h.dropna(inplace=True)

    # 4. Resample to 4h
    df_4h = df_1h.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()

    engine = BacktestEngine(
        initial_capital=100000.0,
        qty_pct=0.10,          # 10% equity sizing
        commission_pct=0.0003, # 0.03% broker commission
        slippage_pct=0.0001    # 1 tick slippage
    )

    tests = [
        # 5-MINUTE
        {
            "id": "SMC_5M_FUSION",
            "name": "5M Scalp Fusion (SMC + Macro Filter)",
            "timeframe": "5m",
            "period": "60 Days",
            "df": df_5m,
            "sigs": strategy_dual_engine_fusion(df_5m, swing_len=5, rr=1.5, sl_atr_mult=1.0, cooldown_bars=6),
            "max_sl_rule": "$7.00 – $8.00 Cap",
            "desc": "5M SMC Sweep at key Order Block with 200 EMA + Supertrend alignment & tight $7–$8 SL"
        },
        # 15-MINUTE
        {
            "id": "SMC_15M_FUSION",
            "name": "15M Intraday Fusion (SMC + Macro Filter)",
            "timeframe": "15m",
            "period": "60 Days",
            "df": df_15m,
            "sigs": strategy_dual_engine_fusion(df_15m, swing_len=5, rr=1.8, sl_atr_mult=1.2, cooldown_bars=4),
            "max_sl_rule": "$12.00 – $14.00 Cap",
            "desc": "15M structural sweep into institutional OB zone with 1:1.8 Risk-Reward"
        },
        # 1-HOUR
        {
            "id": "SMC_1H_FUSION",
            "name": "1H Swing Fusion (SMC + Macro Filter)",
            "timeframe": "1h",
            "period": "2 Years (730d)",
            "df": df_1h,
            "sigs": strategy_dual_engine_fusion(df_1h, swing_len=7, rr=2.0, sl_atr_mult=1.5, cooldown_bars=8),
            "max_sl_rule": "$25.00 – $32.00 Cap",
            "desc": "1-Hour session liquidity sweep into 4H Order Block with 1:2.0 Risk-Reward"
        },
        # 4-HOUR
        {
            "id": "SMC_4H_FUSION",
            "name": "4H Flagship Macro Fusion (SMC + 200 EMA)",
            "timeframe": "4h",
            "period": "2 Years (730d)",
            "df": df_4h,
            "sigs": strategy_dual_engine_fusion(df_4h, swing_len=7, rr=2.0, sl_atr_mult=1.5, cooldown_bars=4),
            "max_sl_rule": "Structural Macro SL",
            "desc": "Flagship 71.4% Win Rate model. Institutional liquidity sweep + 200 EMA baseline"
        }
    ]

    all_metrics = []
    for c in tests:
        res = engine.execute_backtest(c["df"], c["name"], c["sigs"])
        trades = engine.trades
        
        sl_trades = [abs(t.entry_price - t.exit_price) for t in trades if t.exit_reason == 'Stop Loss']
        tp_trades = [abs(t.entry_price - t.exit_price) for t in trades if t.exit_reason == 'Take Profit']
        avg_sl = float(np.mean(sl_trades)) if sl_trades else 0.0
        avg_tp = float(np.mean(tp_trades)) if tp_trades else 0.0
        
        all_metrics.append({
            "id": c["id"],
            "name": c["name"],
            "timeframe": c["timeframe"],
            "period": c["period"],
            "total_trades": res["Total Trades"],
            "win_rate": res["Win Rate (%)"],
            "profit_factor": res["Profit Factor"],
            "net_profit": res["Net Profit ($)"],
            "return_pct": res["Return (%)"],
            "max_drawdown": res["Max Drawdown (%)"],
            "sharpe_ratio": res["Sharpe Ratio"],
            "avg_sl": round(avg_sl, 2),
            "avg_tp": round(avg_tp, 2),
            "max_sl_rule": c["max_sl_rule"],
            "description": c["desc"]
        })

    # Display console table
    df_res = pd.DataFrame(all_metrics)
    print("\n" + tabulate(
        df_res[["timeframe", "period", "total_trades", "win_rate", "avg_sl", "avg_tp", "profit_factor", "max_drawdown", "net_profit"]],
        headers=["TF", "Period", "Trades", "Win Rate (%)", "Avg SL ($)", "Avg TP ($)", "Profit Factor", "Max DD (%)", "Net Profit ($)"],
        tablefmt="github",
        showindex=False
    ))

    # Save to results JSON
    results_path = os.path.join(os.path.dirname(__file__), "results", "smc_multitimeframe_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump({"metrics": all_metrics}, f, indent=2)
    print(f"\nSaved multi-timeframe results to: {results_path}")

    # Update dashboard backtest_data.json
    dash_json_path = os.path.join(os.path.dirname(__file__), "dashboard", "src", "data", "backtest_data.json")
    if os.path.exists(dash_json_path):
        with open(dash_json_path, "r") as f:
            dash_data = json.load(f)
        
        dash_data["smc_timeframes"] = all_metrics
        with open(dash_json_path, "w") as f:
            json.dump(dash_data, f, indent=2)
        print(f"Updated dashboard data at: {dash_json_path}")

    return all_metrics

if __name__ == "__main__":
    run_fused_smc_multitimeframe()
