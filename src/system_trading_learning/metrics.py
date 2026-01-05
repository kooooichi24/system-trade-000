from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Performance:
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    trades: int
    win_rate: float


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def _cagr(equity: pd.Series, periods_per_year: int) -> float:
    if len(equity) < 2:
        return 0.0
    start = float(equity.iloc[0])
    end = float(equity.iloc[-1])
    if start <= 0:
        return 0.0
    years = (len(equity) - 1) / periods_per_year
    if years <= 0:
        return 0.0
    return (end / start) ** (1.0 / years) - 1.0


def _sharpe(returns: pd.Series, periods_per_year: int) -> float:
    r = returns.dropna()
    if len(r) < 2:
        return 0.0
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    if sd == 0.0:
        return 0.0
    return (mu / sd) * math.sqrt(periods_per_year)


def summarize(
    equity: pd.Series,
    trade_pnls: list[float],
    periods_per_year: int = 252,
) -> Performance:
    equity = equity.dropna()
    if equity.empty:
        return Performance(0.0, 0.0, 0.0, 0.0, 0, 0.0)

    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    rets = equity.pct_change()
    cagr = _cagr(equity, periods_per_year=periods_per_year)
    mdd = _max_drawdown(equity)
    sharpe = _sharpe(rets, periods_per_year=periods_per_year)

    trades = len(trade_pnls)
    if trades == 0:
        win_rate = 0.0
    else:
        win_rate = float(np.mean(np.array(trade_pnls) > 0))

    return Performance(
        total_return=total_return,
        cagr=cagr,
        max_drawdown=mdd,
        sharpe=sharpe,
        trades=trades,
        win_rate=win_rate,
    )

