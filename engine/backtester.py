import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Trade:
    strategy: str
    direction: str # 'LONG' or 'SHORT'
    entry_idx: int
    entry_time: Any
    entry_price: float
    qty: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_idx: Optional[int] = None
    exit_time: Optional[Any] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_gross: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    pnl_net: float = 0.0
    return_pct: float = 0.0
    r_multiple: float = 0.0
    holding_bars: int = 0

class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        qty_pct: float = 0.10,          # 10% of equity per trade (matches PDF default_qty_value=10)
        commission_pct: float = 0.0003, # 0.03% broker commission (mandated on PDF page 10)
        slippage_pct: float = 0.0001,   # 1 tick / 0.01% slippage (mandated on PDF page 10)
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.qty_pct = qty_pct
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_trade: Optional[Trade] = None

    def reset(self):
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.current_trade = None

    def execute_backtest(self, df: pd.DataFrame, strategy_name: str, signals: pd.DataFrame) -> Dict[str, Any]:
        """
        Signals DataFrame expected to have columns:
        - 'long_entry': bool
        - 'short_entry': bool
        - 'long_exit': bool (optional)
        - 'short_exit': bool (optional)
        - 'stop_loss': float
        - 'take_profit': float
        """
        self.reset()
        n = len(df)
        times = df.index if isinstance(df.index, pd.DatetimeIndex) else range(n)
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        long_entries = signals['long_entry'].values
        short_entries = signals['short_entry'].values
        long_exits = signals.get('long_exit', pd.Series(False, index=df.index)).values
        short_exits = signals.get('short_exit', pd.Series(False, index=df.index)).values
        stop_losses = signals['stop_loss'].values
        take_profits = signals['take_profit'].values

        for i in range(n):
            c_open = opens[i]
            c_high = highs[i]
            c_low = lows[i]
            c_close = closes[i]
            c_time = times[i]

            # 1. Manage active position (Intrabar SL/TP execution)
            if self.current_trade is not None:
                tr = self.current_trade
                tr.holding_bars += 1
                sl_hit = False
                tp_hit = False
                exit_price = None
                exit_reason = None

                if tr.direction == 'LONG':
                    # Stop loss check
                    if tr.stop_loss is not None and c_low <= tr.stop_loss:
                        sl_hit = True
                        # Execution price with slippage
                        exit_price = min(c_open, tr.stop_loss) * (1.0 - self.slippage_pct)
                        exit_reason = 'Stop Loss'
                    # Take profit check
                    elif tr.take_profit is not None and c_high >= tr.take_profit:
                        tp_hit = True
                        exit_price = max(c_open, tr.take_profit) * (1.0 - self.slippage_pct)
                        exit_reason = 'Take Profit'
                    # Signal exit check
                    elif long_exits[i]:
                        exit_price = c_close * (1.0 - self.slippage_pct)
                        exit_reason = 'Signal Exit'

                elif tr.direction == 'SHORT':
                    # Stop loss check
                    if tr.stop_loss is not None and c_high >= tr.stop_loss:
                        sl_hit = True
                        exit_price = max(c_open, tr.stop_loss) * (1.0 + self.slippage_pct)
                        exit_reason = 'Stop Loss'
                    # Take profit check
                    elif tr.take_profit is not None and c_low <= tr.take_profit:
                        tp_hit = True
                        exit_price = min(c_open, tr.take_profit) * (1.0 + self.slippage_pct)
                        exit_reason = 'Take Profit'
                    # Signal exit check
                    elif short_exits[i]:
                        exit_price = c_close * (1.0 + self.slippage_pct)
                        exit_reason = 'Signal Exit'

                if exit_price is not None:
                    self._close_position(tr, i, c_time, exit_price, exit_reason)

            # 2. Check for new entries if flat
            if self.current_trade is None and i < n - 1:
                if long_entries[i]:
                    entry_p = c_close * (1.0 + self.slippage_pct)
                    sl = stop_losses[i] if not np.isnan(stop_losses[i]) else None
                    tp = take_profits[i] if not np.isnan(take_profits[i]) else None
                    
                    pos_value = self.capital * self.qty_pct
                    qty = pos_value / entry_p
                    comm = pos_value * self.commission_pct
                    self.capital -= comm

                    self.current_trade = Trade(
                        strategy=strategy_name,
                        direction='LONG',
                        entry_idx=i,
                        entry_time=c_time,
                        entry_price=entry_p,
                        qty=qty,
                        stop_loss=sl,
                        take_profit=tp,
                        commission=comm,
                        slippage=pos_value * self.slippage_pct
                    )

                elif short_entries[i]:
                    entry_p = c_close * (1.0 - self.slippage_pct)
                    sl = stop_losses[i] if not np.isnan(stop_losses[i]) else None
                    tp = take_profits[i] if not np.isnan(take_profits[i]) else None

                    pos_value = self.capital * self.qty_pct
                    qty = pos_value / entry_p
                    comm = pos_value * self.commission_pct
                    self.capital -= comm

                    self.current_trade = Trade(
                        strategy=strategy_name,
                        direction='SHORT',
                        entry_idx=i,
                        entry_time=c_time,
                        entry_price=entry_p,
                        qty=qty,
                        stop_loss=sl,
                        take_profit=tp,
                        commission=comm,
                        slippage=pos_value * self.slippage_pct
                    )

            # Record mark-to-market equity
            unrealized_pnl = 0.0
            if self.current_trade is not None:
                tr = self.current_trade
                if tr.direction == 'LONG':
                    unrealized_pnl = (c_close - tr.entry_price) * tr.qty
                else:
                    unrealized_pnl = (tr.entry_price - c_close) * tr.qty
            self.equity_curve.append(self.capital + unrealized_pnl)

        # Close any open trade at the end of data
        if self.current_trade is not None:
            self._close_position(
                self.current_trade,
                n - 1,
                times[n - 1],
                closes[n - 1],
                'End of Backtest'
            )

        return self.calculate_metrics(strategy_name, df)

    def _close_position(self, tr: Trade, exit_idx: int, exit_time: Any, exit_price: float, reason: str):
        tr.exit_idx = exit_idx
        tr.exit_time = exit_time
        tr.exit_price = exit_price
        tr.exit_reason = reason

        exit_val = exit_price * tr.qty
        exit_comm = exit_val * self.commission_pct
        tr.commission += exit_comm

        if tr.direction == 'LONG':
            tr.pnl_gross = (exit_price - tr.entry_price) * tr.qty
        else:
            tr.pnl_gross = (tr.entry_price - exit_price) * tr.qty

        tr.pnl_net = tr.pnl_gross - tr.commission - tr.slippage
        tr.return_pct = (tr.pnl_net / (tr.entry_price * tr.qty)) * 100.0

        # R-Multiple calculation if SL existed
        if tr.stop_loss is not None:
            initial_risk_per_unit = abs(tr.entry_price - tr.stop_loss)
            if initial_risk_per_unit > 0:
                if tr.direction == 'LONG':
                    tr.r_multiple = (exit_price - tr.entry_price) / initial_risk_per_unit
                else:
                    tr.r_multiple = (tr.entry_price - exit_price) / initial_risk_per_unit

        self.capital += tr.pnl_net
        self.trades.append(tr)
        self.current_trade = None

    def calculate_metrics(self, strategy_name: str, df: pd.DataFrame) -> Dict[str, Any]:
        total_trades = len(self.trades)
        if total_trades == 0:
            return {
                'Strategy': strategy_name,
                'Total Trades': 0,
                'Win Rate (%)': 0.0,
                'Net Profit ($)': 0.0,
                'Return (%)': 0.0,
                'Profit Factor': 0.0,
                'Sharpe Ratio': 0.0,
                'Max Drawdown (%)': 0.0,
                'Avg Trade (%)': 0.0,
                'Avg R-Multiple': 0.0,
                'Winning Trades': 0,
                'Losing Trades': 0,
                'OOS Win Rate (%)': 0.0,
                'OOS Return (%)': 0.0
            }

        pnls = np.array([t.pnl_net for t in self.trades])
        ret_pcts = np.array([t.return_pct for t in self.trades])
        r_multiples = np.array([t.r_multiple for t in self.trades])

        wins = pnls[pnls > 0]
        losses = pnls[pnls <= 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades) * 100.0

        gross_profit = wins.sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses.sum()) if len(losses) > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        net_profit = float(pnls.sum())
        total_return_pct = (net_profit / self.initial_capital) * 100.0

        # Drawdown
        eq = np.array(self.equity_curve)
        peak = np.maximum.accumulate(eq)
        drawdowns = (eq - peak) / peak
        max_drawdown_pct = abs(float(drawdowns.min())) * 100.0 if len(drawdowns) > 0 else 0.0

        # Sharpe ratio (from bar-by-bar returns)
        bar_returns = pd.Series(eq).pct_change().dropna()
        if len(bar_returns) > 1 and bar_returns.std() > 0:
            sharpe = (bar_returns.mean() / bar_returns.std()) * np.sqrt(252 * 26) # Annualized for ~15m bars
        else:
            sharpe = 0.0

        # Walk-forward Split: Reserve last 30% for Out-of-Sample verification (Mandated on Page 11)
        split_idx = int(len(df) * 0.70)
        oos_trades = [t for t in self.trades if t.entry_idx >= split_idx]
        if len(oos_trades) > 0:
            oos_pnls = [t.pnl_net for t in oos_trades]
            oos_wins = [p for p in oos_pnls if p > 0]
            oos_win_rate = (len(oos_wins) / len(oos_trades)) * 100.0
            oos_return = (sum(oos_pnls) / self.initial_capital) * 100.0
        else:
            oos_win_rate = 0.0
            oos_return = 0.0

        return {
            'Strategy': strategy_name,
            'Total Trades': total_trades,
            'Win Rate (%)': round(win_rate, 2),
            'Net Profit ($)': round(net_profit, 2),
            'Return (%)': round(total_return_pct, 2),
            'Profit Factor': round(profit_factor, 2),
            'Sharpe Ratio': round(sharpe, 2),
            'Max Drawdown (%)': round(max_drawdown_pct, 2),
            'Avg Trade (%)': round(float(ret_pcts.mean()), 2),
            'Avg R-Multiple': round(float(r_multiples.mean()), 2),
            'Winning Trades': win_count,
            'Losing Trades': loss_count,
            'OOS Win Rate (%)': round(oos_win_rate, 2),
            'OOS Return (%)': round(oos_return, 2)
        }
