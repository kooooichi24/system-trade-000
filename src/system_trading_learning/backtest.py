from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 1_000_000.0
    fee_rate: float = 0.0005  # 0.05%
    slippage_rate: float = 0.0002  # 0.02%
    allow_fractional: bool = False  # stocks: False, crypto/CFD: True


def sma_cross_signal(close: pd.Series, fast: int, slow: int) -> pd.Series:
    """
    Long-only SMA crossover.

    Returns:
        pd.Series of desired position (0.0 or 1.0), indexed like close.
    """
    if fast <= 0 or slow <= 0 or fast >= slow:
        raise ValueError("Require 0 < fast < slow")

    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    desired = (fast_ma > slow_ma).astype(float)
    return desired


@dataclass(frozen=True)
class BacktestResult:
    equity: pd.Series
    positions: pd.Series
    trade_pnls: list[float]


def run_long_only_next_open(
    ohlcv: pd.DataFrame,
    desired_position: pd.Series,
    cfg: BacktestConfig = BacktestConfig(),
) -> BacktestResult:
    """
    Event-driven backtest (long-only), executes at NEXT bar open.

    Assumptions:
    - We observe signals at bar close (t) and trade at open (t+1).
    - Position is either 0 or fully invested (all-in) in the asset.
    - Fees and slippage are applied on notional at entry and exit.
    """
    df = ohlcv.copy()
    required = {"open", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"ohlcv must contain columns: {sorted(required)}")
    if len(df) < 3:
        raise ValueError("Need at least 3 bars for next-open execution")

    desired_position = desired_position.reindex(df.index).fillna(0.0).astype(float)

    cash = float(cfg.initial_cash)
    qty = 0.0
    entry_value = 0.0
    trade_pnls: list[float] = []

    positions = []
    equity = []

    # We trade at open[t], based on desired_position[t-1] (signal at close[t-1])
    prev_desired = float(desired_position.iloc[0])

    for i in range(1, len(df)):
        px_open = float(df["open"].iloc[i])
        px_close = float(df["close"].iloc[i])
        desired = float(desired_position.iloc[i - 1])

        # Execute at open if desired state changes
        if desired != prev_desired:
            if desired == 1.0 and qty == 0.0:
                # Enter
                exec_px = px_open * (1.0 + cfg.slippage_rate)
                fee = cash * cfg.fee_rate
                spendable = cash - fee
                if spendable <= 0:
                    qty = 0.0
                else:
                    raw_qty = spendable / exec_px
                    if not cfg.allow_fractional:
                        raw_qty = float(np.floor(raw_qty))
                    qty = max(raw_qty, 0.0)
                    cost = qty * exec_px
                    cash = cash - cost - fee
                    entry_value = cost + fee

            elif desired == 0.0 and qty > 0.0:
                # Exit
                exec_px = px_open * (1.0 - cfg.slippage_rate)
                proceeds = qty * exec_px
                fee = proceeds * cfg.fee_rate
                cash = cash + proceeds - fee
                pnl = (proceeds - fee) - entry_value
                trade_pnls.append(float(pnl))
                qty = 0.0
                entry_value = 0.0

        prev_desired = desired

        # Mark-to-market at close
        pos_value = qty * px_close
        positions.append(float(qty))
        equity.append(float(cash + pos_value))

    idx = df.index[1:]
    return BacktestResult(
        equity=pd.Series(equity, index=idx, name="equity"),
        positions=pd.Series(positions, index=idx, name="qty"),
        trade_pnls=trade_pnls,
    )

