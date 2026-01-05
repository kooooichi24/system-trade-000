from __future__ import annotations

from system_trading_learning.backtest import BacktestConfig, run_long_only_next_open, sma_cross_signal
from system_trading_learning.sample_data import SampleDataConfig, make_ohlcv


def test_smoke_backtest_runs_and_equity_positive() -> None:
    ohlcv = make_ohlcv(SampleDataConfig(n=300))
    desired = sma_cross_signal(ohlcv["close"], fast=10, slow=30)
    res = run_long_only_next_open(ohlcv, desired, cfg=BacktestConfig(initial_cash=100_000))

    assert len(res.equity) > 0
    assert res.equity.iloc[-1] > 0

