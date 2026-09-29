import yfinance as yf
import pandas as pd
import numpy as np
from tabulate import tabulate
from engine.backtester import BacktestEngine
from strategies.combo_strategies import strategy_dual_engine_fusion

def compare_timeframes():
    # Load 1h data (730d)
    df_1h = yf.download('GC=F', interval='1h', period='730d', progress=False)
    if isinstance(df_1h.columns, pd.MultiIndex):
        df_1h.columns = [c[0].lower() for c in df_1h.columns]
    else:
        df_1h.columns = [c.lower() for c in df_1h.columns]
    df_1h.dropna(inplace=True)

    # 4H data
    df_4h = df_1h.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    
    # 5m data (60d)
    df_5m = yf.download('GC=F', interval='5m', period='60d', progress=False)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = [c[0].lower() for c in df_5m.columns]
    else:
        df_5m.columns = [c.lower() for c in df_5m.columns]
    df_5m.dropna(inplace=True)

    # 15m data (resampled from 5m, 60d)
    df_15m = df_5m.resample('15min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()

    # 30m data (resampled from 5m, 60d)
    df_30m = df_5m.resample('30min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()

    engine = BacktestEngine(100000.0, qty_pct=0.10, commission_pct=0.0003, slippage_pct=0.0001)

    timeframes = [
        ("5-Minute (5m)", df_5m, 5, 1.5, 1.0, 6, "60 Days"),
        ("15-Minute (15m)", df_15m, 5, 1.8, 1.2, 4, "60 Days"),
        ("30-Minute (30m)", df_30m, 5, 2.0, 1.5, 4, "60 Days"),
        ("1-Hour (1H)", df_1h, 7, 2.0, 1.5, 8, "2 Years (730d)"),
        ("4-Hour (4H) - Current", df_4h, 7, 2.0, 1.5, 4, "2 Years (730d)"),
    ]

    table_data = []

    for label, data, sw, rr, sl_m, cd, period in timeframes:
        sigs = strategy_dual_engine_fusion(data, swing_len=sw, rr=rr, sl_atr_mult=sl_m, cooldown_bars=cd)
        metrics = engine.execute_backtest(data, label, sigs)

        sl_trades = [abs(t.entry_price - t.exit_price) for t in engine.trades if t.exit_reason == 'Stop Loss']
        tp_trades = [abs(t.entry_price - t.exit_price) for t in engine.trades if t.exit_reason == 'Take Profit']
        avg_sl = np.mean(sl_trades) if sl_trades else 0.0
        avg_tp = np.mean(tp_trades) if tp_trades else 0.0

        table_data.append({
            "Timeframe": label,
            "Period": period,
            "Trades": metrics["Total Trades"],
            "Win Rate (%)": f"{metrics['Win Rate (%)']:.1f}%",
            "Avg Stop Loss ($)": f"${avg_sl:.2f}",
            "Avg Take Profit ($)": f"${avg_tp:.2f}",
            "Profit Factor": metrics["Profit Factor"],
            "Max Drawdown (%)": f"{metrics['Max Drawdown (%)']:.2f}%",
            "Net Profit ($)": f"${metrics['Net Profit ($)']:,.2f}"
        })

    print(tabulate(table_data, headers="keys", tablefmt="github"))

if __name__ == "__main__":
    compare_timeframes()
