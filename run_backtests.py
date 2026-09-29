import os
import json
import pandas as pd
from tabulate import tabulate
from engine.data import load_or_fetch_data
from engine.backtester import BacktestEngine
from strategies import ALL_STRATEGIES

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

def run_suite(symbol: str = "^NSEI", interval: str = "15m", period: str = "60d"):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"\n=======================================================")
    print(f" LOADING HISTORICAL DATA: {symbol} [{interval}, {period}]")
    print(f"=======================================================")
    df = load_or_fetch_data(symbol, period=period, interval=interval)
    print(f"Total Bars Loaded: {len(df)} | Start: {df.index[0]} | End: {df.index[-1]}\n")

    engine = BacktestEngine(
        initial_capital=100000.0,
        qty_pct=0.10,          # 10% equity allocation per trade
        commission_pct=0.0003, # 0.03% broker commission (PDF Page 10)
        slippage_pct=0.0001    # 1 tick / 0.01% slippage (PDF Page 10)
    )

    results = []
    all_trade_logs = {}

    print("Running Backtest Suite across all 20 Strategies with Friction Calibration...")
    for name, strat_func in ALL_STRATEGIES.items():
        try:
            signals = strat_func(df)
            metrics = engine.execute_backtest(df, name, signals)
            results.append(metrics)

            if len(engine.trades) > 0:
                trade_records = [
                    {
                        "Trade": idx + 1,
                        "Direction": t.direction,
                        "Entry Time": str(t.entry_time),
                        "Entry Price": round(t.entry_price, 2),
                        "Exit Time": str(t.exit_time),
                        "Exit Price": round(t.exit_price, 2),
                        "Exit Reason": t.exit_reason,
                        "Net PnL ($)": round(t.pnl_net, 2),
                        "Return (%)": round(t.return_pct, 2),
                        "R-Multiple": round(t.r_multiple, 2),
                        "Bars": t.holding_bars
                    }
                    for idx, t in enumerate(engine.trades)
                ]
                all_trade_logs[name] = trade_records
            print(f"  ✓ {name}: {metrics['Total Trades']} trades | Return: {metrics['Return (%)']}% | Win Rate: {metrics['Win Rate (%)']}%")
        except Exception as e:
            print(f"  ✗ Error running {name}: {e}")

    results_df = pd.DataFrame(results)

    # Save CSV and JSON
    csv_file = os.path.join(RESULTS_DIR, f"backtest_summary_{symbol.replace('^', '')}_{interval}.csv")
    json_file = os.path.join(RESULTS_DIR, f"backtest_summary_{symbol.replace('^', '')}_{interval}.json")
    trades_file = os.path.join(RESULTS_DIR, f"trade_logs_{symbol.replace('^', '')}_{interval}.json")

    results_df.to_csv(csv_file, index=False)
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    with open(trades_file, 'w') as f:
        json.dump(all_trade_logs, f, indent=2)

    # Rank by Profitability (Net Profit / Return %)
    ranked_profit = results_df.sort_values(by="Return (%)", ascending=False).reset_index(drop=True)
    ranked_sharpe = results_df.sort_values(by="Sharpe Ratio", ascending=False).reset_index(drop=True)

    print("\n" + "="*95)
    print(f" PERFORMANCE LEADERBOARD (Ranked by Return %) - {symbol} [{interval}]")
    print("="*95)
    print(tabulate(
        ranked_profit[["Strategy", "Total Trades", "Win Rate (%)", "Net Profit ($)", "Return (%)", "Profit Factor", "Sharpe Ratio", "Max Drawdown (%)", "OOS Return (%)"]],
        headers="keys",
        tablefmt="github",
        showindex=True
    ))

    print("\n" + "="*95)
    print(f" MOST PROFITABLE STRATEGY HIGHLIGHT")
    print("="*95)
    top_strat = ranked_profit.iloc[0]
    print(f"🏆 Top Winner: {top_strat['Strategy']}")
    print(f"   • Total Return: {top_strat['Return (%)']}% (Net Profit: ${top_strat['Net Profit ($)']})")
    print(f"   • Win Rate: {top_strat['Win Rate (%)']}% ({top_strat['Winning Trades']} wins / {top_strat['Losing Trades']} losses)")
    print(f"   • Profit Factor: {top_strat['Profit Factor']}")
    print(f"   • Sharpe Ratio: {top_strat['Sharpe Ratio']}")
    print(f"   • Max Drawdown: {top_strat['Max Drawdown (%)']}%")
    print(f"   • Out-Of-Sample (30%) Return: {top_strat['OOS Return (%)']}% (OOS Win Rate: {top_strat['OOS Win Rate (%)']}%)")

    top_sharpe = ranked_sharpe.iloc[0]
    print(f"\n🛡️ Best Risk-Adjusted Strategy (Highest Sharpe): {top_sharpe['Strategy']}")
    print(f"   • Sharpe Ratio: {top_sharpe['Sharpe Ratio']} | Return: {top_sharpe['Return (%)']}% | Max DD: {top_sharpe['Max Drawdown (%)']}%")

    return results_df

if __name__ == "__main__":
    # 1. Primary Benchmark: Nifty 50 Index (15-min Intraday)
    run_suite(symbol="^NSEI", interval="15m", period="60d")
