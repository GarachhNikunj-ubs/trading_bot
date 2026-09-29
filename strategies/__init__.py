from .indicator_strategies import (
    strategy_01_ema_rsi,
    strategy_02_ema_trend_following,
    strategy_03_supertrend_ema,
    strategy_04_vwap_rsi,
    strategy_05_bollinger_squeeze,
    strategy_06_donchian_breakout,
    strategy_07_orb,
    strategy_08_macd_ema,
    strategy_09_rsi_mean_reversion,
    strategy_10_multi_confluence
)

from .smc_strategies import (
    strategy_11_sweep_choch,
    strategy_12_ob_bos,
    strategy_13_fvg_bos,
    strategy_14_sweep_ob,
    strategy_15_sweep_fvg,
    strategy_16_bos_continuation,
    strategy_17_amd,
    strategy_18_premium_discount,
    strategy_19_asian_sweep,
    strategy_20_flagship_smc
)

ALL_STRATEGIES = {
    "01. EMA 9/21 + RSI Trend": strategy_01_ema_rsi,
    "02. EMA 20/50 Trend Following": strategy_02_ema_trend_following,
    "03. Supertrend + 200 EMA Filter": strategy_03_supertrend_ema,
    "04. VWAP + RSI Intraday": strategy_04_vwap_rsi,
    "05. Bollinger Band Breakout": strategy_05_bollinger_squeeze,
    "06. Donchian Channel Breakout": strategy_06_donchian_breakout,
    "07. Opening Range Breakout (ORB)": strategy_07_orb,
    "08. MACD + EMA Filter": strategy_08_macd_ema,
    "09. RSI Statistical Mean Reversion": strategy_09_rsi_mean_reversion,
    "10. Multi-Indicator Confluence": strategy_10_multi_confluence,
    "11. Liquidity Sweep + CHOCH": strategy_11_sweep_choch,
    "12. Order Block Retest + BOS": strategy_12_ob_bos,
    "13. FVG Retest + BOS": strategy_13_fvg_bos,
    "14. Liquidity Sweep + Order Block": strategy_14_sweep_ob,
    "15. Liquidity Sweep + FVG": strategy_15_sweep_fvg,
    "16. BOS Pullback Continuation": strategy_16_bos_continuation,
    "17. Power of 3 (AMD Model)": strategy_17_amd,
    "18. Premium / Discount Dealing Range": strategy_18_premium_discount,
    "19. Asian Session Range Sweep": strategy_19_asian_sweep,
    "20. Flagship SMC Engine (Sweep+CHOCH+FVG)": strategy_20_flagship_smc,
}
