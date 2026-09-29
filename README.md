# Institutional Algorithmic Suite & Real-Time Market Scanner

Institutional-grade quantitative backtesting suite, Pine Script v6 strategies, Gold (XAU/USD) 70% Win-Rate Dual-Engine Fusion model, and a real-time SaaS trading dashboard with live market polling and Supabase integration.

---

## 🚀 Key Highlights

1. **20 Quantitative Strategies Implemented & Backtested:**
   - Full event-driven Python engine with friction modeling (**0.03% broker commission + 1-tick slippage**).
   - Validated across NIFTY 50, Bitcoin, and Gold (`GC=F`).
2. **Dual-Engine Fusion Strategy for Gold (`GC=F` / `XAUUSD`):**
   - Fuses Macro Trend Filtering (200 EMA + Supertrend) with SMC Liquidity Sweep pullback entries.
   - **70.0% Win Rate**, **3.81 Profit Factor**, **2.84 Sharpe Ratio**, **0.26% Max Drawdown**, 10 trades over 2.5 years (eliminates overtrading).
   - Pine Script v6 code ready in [`pine_scripts/022_gold_dual_engine_fusion.pine`](pine_scripts/022_gold_dual_engine_fusion.pine).
3. **Real-Time Market Scanner (Top 5 Watchlist):**
   - Live tick streaming for **Gold**, **NIFTY 50**, **Bitcoin**, **Reliance**, and **S&P 500 ETF (SPY)**.
   - Live intraday 24h range bars, 50-DMA, RSI, ATR, and dynamic trade blueprints (Entry Zone, Stop Loss, Target TP with 1:2 R:R).
4. **SaaS Dashboard (React + Vite + Recharts + Supabase):**
   - High-contrast monochromatic design system (light/dark modes).
   - Backtest leaderboard, equity curve visualizer, code inspector modal, and cloud database connectivity.

---

## 🛠️ Quick Start & Setup

### 1. Configure Environment Variables
Copy the template file to configure your credentials:
```bash
cp .env.example .env
cp .env.example dashboard/.env
```
Open `.env` (or `dashboard/.env`) and insert your Supabase or webhook credentials:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your_publishable_anon_key
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your_publishable_anon_key
```

### 2. Python Backtesting Engine & Live Data Fetcher
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install yfinance pandas numpy scipy matplotlib

# Run full 20-strategy backtests
python run_backtests.py

# Run Dual-Engine Gold Fusion backtest
python run_combo_backtest.py

# Fetch live market scanner data
python dashboard/database/fetch_market_scanner.py
```

### 3. Launch Web Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open your browser at: `http://127.0.0.1:5173/`

---

## 📁 Repository Structure

```
├── .env.example                       # Environment configuration template
├── README.md                          # Project documentation
├── engine/                            # Event-driven backtesting engine
│   └── backtester.py
├── strategies/                        # 20 Quantitative strategies in Python
│   ├── indicator_strategies.py        # Strategies 1-10 (Indicators & Momentum)
│   ├── smc_strategies.py              # Strategies 11-20 (Smart Money Concepts)
│   └── combo_strategies.py            # Dual-Engine Gold Fusion Strategy
├── pine_scripts/                      # Pine Script v6 files for TradingView
│   └── 022_gold_dual_engine_fusion.pine
├── results/                           # JSON summaries & trade ledgers
├── data/                              # Historical parquet market data
├── bridge/                            # Webhook server for TradingView alerts
│   └── server.py
└── dashboard/                         # React/Vite SaaS web dashboard
    ├── src/
    │   ├── App.jsx                    # Dashboard UI with live market scanner
    │   ├── index.css                  # Monochromatic design system
    │   ├── data/                      # Backtest and market scanner JSON
    │   └── lib/                       # Supabase client connector
    ├── database/                      # Live market quote fetcher
    │   └── fetch_market_scanner.py
    └── vite.config.js                 # Vite dev server with /api/live-quotes
```
