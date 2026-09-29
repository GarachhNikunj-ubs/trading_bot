import os
import json
import sqlite3
import pandas as pd

DB_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "data")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "quant_trading.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        category TEXT,
        timeframe TEXT,
        asset TEXT,
        win_rate REAL,
        profit_factor REAL,
        sharpe_ratio REAL,
        total_trades INTEGER,
        net_profit REAL,
        max_drawdown REAL,
        oos_win_rate REAL,
        pine_script_path TEXT,
        description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_name TEXT,
        asset TEXT,
        timeframe TEXT,
        trade_num INTEGER,
        direction TEXT,
        entry_time TEXT,
        entry_price REAL,
        exit_time TEXT,
        exit_price REAL,
        exit_reason TEXT,
        net_pnl REAL,
        return_pct REAL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        strategy TEXT,
        symbol TEXT,
        action TEXT,
        qty REAL,
        price REAL,
        sl REAL,
        status TEXT
    );
    """)

    # Populate with our empirical backtest benchmark data
    # 1. Gold (XAUUSD) Dataset
    gold_strategies = [
        {
            "name": "AlphaQuant Dual-Engine Fusion",
            "category": "Fusion (Trend + SMC)",
            "timeframe": "4H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 70.0,
            "profit_factor": 3.81,
            "sharpe_ratio": 2.84,
            "total_trades": 10,
            "net_profit": 1388.52,
            "max_drawdown": 0.26,
            "oos_win_rate": 100.0,
            "description": "Combines Supertrend + 200 EMA Macro Baseline with SMC Liquidity Sweep. Zero overtrading.",
            "code": "// Strategy 22: Dual-Engine Fusion (XAUUSD 4H)\n//@version=6\nstrategy('AlphaQuant Dual-Engine Fusion', overlay=true)\n..."
        },
        {
            "name": "Supertrend + 200 EMA Filter",
            "category": "Trend Following",
            "timeframe": "4H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 55.81,
            "profit_factor": 3.57,
            "sharpe_ratio": 3.18,
            "total_trades": 43,
            "net_profit": 5935.90,
            "max_drawdown": 1.30,
            "oos_win_rate": 54.55,
            "description": "Macro trend filtering eliminates consolidation whipsaws on Gold multi-day runs.",
            "code": "// Strategy 03: Supertrend + 200 EMA\n//@version=6\nstrategy('Algo 03: Supertrend', overlay=true)\n..."
        },
        {
            "name": "Donchian Breakout (Turtle Model)",
            "category": "Trend Following",
            "timeframe": "1H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 43.17,
            "profit_factor": 1.49,
            "sharpe_ratio": 1.35,
            "total_trades": 315,
            "net_profit": 7133.92,
            "max_drawdown": 1.90,
            "oos_win_rate": 41.41,
            "description": "Classic Turtle trend following logic with 20-period breakout and 10-period trailing exit.",
            "code": "// Strategy 06: Donchian Breakout\n//@version=6\nstrategy('Algo 06: Donchian Breakout', overlay=true)\n..."
        },
        {
            "name": "Liquidity Sweep + CHOCH",
            "category": "Smart Money Concepts",
            "timeframe": "1H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 37.09,
            "profit_factor": 1.38,
            "sharpe_ratio": 1.00,
            "total_trades": 213,
            "net_profit": 4596.21,
            "max_drawdown": 2.01,
            "oos_win_rate": 40.32,
            "description": "Detects institutional stop hunts at swing extremes followed by Change of Character.",
            "code": "// Strategy 11: Sweep + CHOCH\n//@version=6\nstrategy('Algo 11: Sweep + CHOCH', overlay=true)\n..."
        },
        {
            "name": "FVG Retest + Structural BOS",
            "category": "Smart Money Concepts",
            "timeframe": "1H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 40.54,
            "profit_factor": 1.02,
            "sharpe_ratio": 0.50,
            "total_trades": 333,
            "net_profit": 264.81,
            "max_drawdown": 2.09,
            "oos_win_rate": 38.00,
            "description": "Quantifies 3-bar price imbalances and enters limit orders on retracements.",
            "code": "// Strategy 13: FVG Retest + BOS\n//@version=6\n..."
        },
        {
            "name": "BOS Pullback Continuation",
            "category": "Smart Money Concepts",
            "timeframe": "1H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 37.17,
            "profit_factor": 1.12,
            "sharpe_ratio": 0.31,
            "total_trades": 191,
            "net_profit": 1615.19,
            "max_drawdown": 2.25,
            "oos_win_rate": 35.00,
            "description": "Enters upon 50% Fibonacci retracements of confirmed displacement legs.",
            "code": "// Strategy 16: BOS Continuation\n//@version=6\n..."
        },
        {
            "name": "MACD Histogram Velocity + EMA 50",
            "category": "Momentum",
            "timeframe": "1H",
            "asset": "Gold (XAUUSD)",
            "win_rate": 44.88,
            "profit_factor": 1.07,
            "sharpe_ratio": 0.05,
            "total_trades": 332,
            "net_profit": 1111.53,
            "max_drawdown": 2.76,
            "oos_win_rate": 42.00,
            "description": "Dual-layer momentum confirmation filtering crossovers by histogram slope and 50 EMA.",
            "code": "// Strategy 08: MACD + EMA\n//@version=6\n..."
        }
    ]

    # Insert into SQLite
    cursor.execute("DELETE FROM strategies;")
    cursor.execute("DELETE FROM trades;")
    for s in gold_strategies:
        cursor.execute("""
        INSERT INTO strategies (name, category, timeframe, asset, win_rate, profit_factor, sharpe_ratio, total_trades, net_profit, max_drawdown, oos_win_rate, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (s["name"], s["category"], s["timeframe"], s["asset"], s["win_rate"], s["profit_factor"], s["sharpe_ratio"], s["total_trades"], s["net_profit"], s["max_drawdown"], s["oos_win_rate"], s["description"]))

    # Insert trade logs for Dual-Engine Fusion
    fusion_trades = [
        {"Trade": 1, "Direction": "LONG", "Entry Time": "2024-09-04 08:00", "Entry Price": 2520.45, "Exit Time": "2024-09-12 12:00", "Exit Price": 2565.98, "Exit Reason": "Take Profit", "Net PnL ($)": 173.60, "Return (%)": 1.74},
        {"Trade": 2, "Direction": "SHORT", "Entry Time": "2024-11-25 20:00", "Entry Price": 2610.24, "Exit Time": "2024-11-27 04:00", "Exit Price": 2643.65, "Exit Reason": "Stop Loss", "Net PnL ($)": -135.26, "Return (%)": -1.35},
        {"Trade": 3, "Direction": "SHORT", "Entry Time": "2024-12-26 20:00", "Entry Price": 2652.53, "Exit Time": "2024-12-30 12:00", "Exit Price": 2617.78, "Exit Reason": "Take Profit", "Net PnL ($)": 124.09, "Return (%)": 1.24},
        {"Trade": 4, "Direction": "LONG", "Entry Time": "2025-02-25 16:00", "Entry Price": 2924.59, "Exit Time": "2025-02-27 12:00", "Exit Price": 2883.07, "Exit Reason": "Stop Loss", "Net PnL ($)": -149.18, "Return (%)": -1.49},
        {"Trade": 5, "Direction": "LONG", "Entry Time": "2025-03-11 00:00", "Entry Price": 2900.69, "Exit Time": "2025-03-12 16:00", "Exit Price": 2948.10, "Exit Reason": "Take Profit", "Net PnL ($)": 156.39, "Return (%)": 1.56},
        {"Trade": 6, "Direction": "LONG", "Entry Time": "2025-06-08 20:00", "Entry Price": 3338.73, "Exit Time": "2025-06-13 00:00", "Exit Price": 3459.63, "Exit Reason": "Take Profit", "Net PnL ($)": 355.56, "Return (%)": 3.55},
        {"Trade": 7, "Direction": "LONG", "Entry Time": "2025-07-31 04:00", "Entry Price": 3356.44, "Exit Time": "2025-07-31 16:00", "Exit Price": 3288.57, "Exit Reason": "Stop Loss", "Net PnL ($)": -210.19, "Return (%)": -2.09},
        {"Trade": 8, "Direction": "LONG", "Entry Time": "2025-09-11 12:00", "Entry Price": 3672.37, "Exit Time": "2025-09-16 04:00", "Exit Price": 3731.27, "Exit Reason": "Take Profit", "Net PnL ($)": 153.79, "Return (%)": 1.53},
        {"Trade": 9, "Direction": "LONG", "Entry Time": "2026-01-16 16:00", "Entry Price": 4595.66, "Exit Time": "2026-01-20 04:00", "Exit Price": 4700.43, "Exit Reason": "Take Profit", "Net PnL ($)": 221.89, "Return (%)": 2.21},
        {"Trade": 10, "Direction": "SHORT", "Entry Time": "2026-06-17 16:00", "Entry Price": 4253.87, "Exit Time": "2026-06-30 00:00", "Exit Price": 3956.09, "Exit Reason": "Take Profit", "Net PnL ($)": 697.83, "Return (%)": 6.93}
    ]

    for t in fusion_trades:
        cursor.execute("""
        INSERT INTO trades (strategy_name, asset, timeframe, trade_num, direction, entry_time, entry_price, exit_time, exit_price, exit_reason, net_pnl, return_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ("AlphaQuant Dual-Engine Fusion", "Gold (XAUUSD)", "4H", t["Trade"], t["Direction"], t["Entry Time"], t["Entry Price"], t["Exit Time"], t["Exit Price"], t["Exit Reason"], t["Net PnL ($)"], t["Return (%)"]))

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS smc_timeframes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        timeframe TEXT,
        period TEXT,
        total_trades INTEGER,
        win_rate REAL,
        avg_sl REAL,
        avg_tp REAL,
        profit_factor REAL,
        max_drawdown REAL,
        net_profit REAL,
        max_sl_rule TEXT,
        description TEXT
    );
    """)

    smc_tf_records = [
        {
            "id": "SMC_5M",
            "name": "Institutional SMC (5-Minute Scalp)",
            "timeframe": "5m",
            "period": "60 Days",
            "total_trades": 83,
            "win_rate": 49.4,
            "avg_sl": 6.95,
            "avg_tp": 13.22,
            "profit_factor": 1.03,
            "max_drawdown": 0.53,
            "net_profit": 28.46,
            "max_sl_rule": "$8.00 Hard Cap",
            "description": "5M Liquidity Sweep + Order Block mitigation retest with strict $8.00 SL cap"
        },
        {
            "id": "SMC_15M",
            "name": "Institutional SMC (15-Minute Intraday)",
            "timeframe": "15m",
            "period": "60 Days",
            "total_trades": 34,
            "win_rate": 29.41,
            "avg_sl": 13.74,
            "avg_tp": 48.48,
            "profit_factor": 1.09,
            "max_drawdown": 0.64,
            "net_profit": 80.97,
            "max_sl_rule": "$14.00 Cap",
            "description": "15M structural sweep into institutional OB zone with 1:1.8 Risk-Reward"
        },
        {
            "id": "SMC_1H",
            "name": "Institutional SMC (1-Hour Swing)",
            "timeframe": "1h",
            "period": "2 Years",
            "total_trades": 51,
            "win_rate": 29.41,
            "avg_sl": 31.80,
            "avg_tp": 80.18,
            "profit_factor": 0.84,
            "max_drawdown": 1.26,
            "net_profit": -534.26,
            "max_sl_rule": "$25.00 – $32.00 Cap",
            "description": "1-Hour session liquidity pool sweep with 1:2.0 Risk-Reward"
        },
        {
            "id": "SMC_4H",
            "name": "Dual-Engine SMC Fusion (4-Hour Macro)",
            "timeframe": "4h",
            "period": "2 Years",
            "total_trades": 7,
            "win_rate": 71.43,
            "avg_sl": 25.35,
            "avg_tp": 108.57,
            "profit_factor": 6.42,
            "max_drawdown": 0.26,
            "net_profit": 1138.44,
            "max_sl_rule": "Structural Macro SL",
            "description": "Flagship 71.4% Win Rate model. Macro 200 EMA + SMC Liquidity Sweep & OB retest"
        }
    ]

    for tf in smc_tf_records:
        cursor.execute("""
        INSERT INTO smc_timeframes (name, timeframe, period, total_trades, win_rate, avg_sl, avg_tp, profit_factor, max_drawdown, net_profit, max_sl_rule, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (tf["name"], tf["timeframe"], tf["period"], tf["total_trades"], tf["win_rate"], tf["avg_sl"], tf["avg_tp"], tf["profit_factor"], tf["max_drawdown"], tf["net_profit"], tf["max_sl_rule"], tf["description"]))

    conn.commit()
    conn.close()

    # Also write JSON bundle for instant client-side rendering
    bundle = {
        "database_info": {
            "type": "SQLite 3.0",
            "location": DB_PATH,
            "status": "CONNECTED",
            "last_synced": "2026-09-29 12:20 UTC"
        },
        "strategies": gold_strategies,
        "smc_timeframes": smc_tf_records,
        "fusion_trades": fusion_trades,
        "equity_curve": [
            {"date": "2024-08", "equity": 100000},
            {"date": "2024-09", "equity": 100173.60},
            {"date": "2024-11", "equity": 100038.34},
            {"date": "2024-12", "equity": 100162.43},
            {"date": "2025-02", "equity": 100013.25},
            {"date": "2025-03", "equity": 100169.64},
            {"date": "2025-06", "equity": 100525.20},
            {"date": "2025-07", "equity": 100315.01},
            {"date": "2025-09", "equity": 100468.80},
            {"date": "2026-01", "equity": 100690.69},
            {"date": "2026-06", "equity": 101388.52}
        ]
    }

    json_path = os.path.join(DATA_DIR, "backtest_data.json")
    with open(json_path, "w") as f:
        json.dump(bundle, f, indent=2)

    print(f"Database initialized: {DB_PATH}")
    print(f"JSON bundle saved: {json_path}")

if __name__ == "__main__":
    init_database()
