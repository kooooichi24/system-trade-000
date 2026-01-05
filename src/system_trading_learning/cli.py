from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from system_trading_learning.backtest import (
    BacktestConfig,
    run_long_only_next_open,
    sma_cross_signal,
)
from system_trading_learning.metrics import summarize
from system_trading_learning.sample_data import SampleDataConfig, make_ohlcv


def _read_ohlcv_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Accept either explicit date column or index-like first column.
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    else:
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
        df = df.set_index(df.columns[0])

    df = df.sort_index()
    df.columns = [c.strip().lower() for c in df.columns]

    needed = {"open", "high", "low", "close", "volume"}
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"CSV missing columns: {sorted(missing)}")
    return df[list(["open", "high", "low", "close", "volume"])]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stl", description="System trading learning (uv) starter")
    src = p.add_mutually_exclusive_group(required=False)
    src.add_argument("--csv", type=Path, help="OHLCV CSV path (date, open, high, low, close, volume)")
    src.add_argument("--sample", action="store_true", help="Use synthetic OHLCV (no CSV needed)")

    p.add_argument("--fast", type=int, default=20, help="SMA fast window")
    p.add_argument("--slow", type=int, default=60, help="SMA slow window")
    p.add_argument("--initial-cash", type=float, default=1_000_000.0, help="Initial cash")
    p.add_argument("--fee-rate", type=float, default=0.0005, help="Fee rate (e.g. 0.0005 = 0.05%)")
    p.add_argument(
        "--slippage-rate",
        type=float,
        default=0.0002,
        help="Slippage rate applied on executions",
    )
    p.add_argument("--periods-per-year", type=int, default=252, help="Trading periods per year")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.csv:
        ohlcv = _read_ohlcv_csv(args.csv)
    else:
        # default to sample so it's runnable immediately
        ohlcv = make_ohlcv(SampleDataConfig())

    desired = sma_cross_signal(ohlcv["close"], fast=args.fast, slow=args.slow)
    bt = run_long_only_next_open(
        ohlcv,
        desired_position=desired,
        cfg=BacktestConfig(
            initial_cash=args.initial_cash,
            fee_rate=args.fee_rate,
            slippage_rate=args.slippage_rate,
        ),
    )
    perf = summarize(bt.equity, bt.trade_pnls, periods_per_year=args.periods_per_year)

    print("== summary ==")
    print(f"total_return : {perf.total_return:.2%}")
    print(f"cagr         : {perf.cagr:.2%}")
    print(f"max_drawdown : {perf.max_drawdown:.2%}")
    print(f"sharpe       : {perf.sharpe:.2f}")
    print(f"trades       : {perf.trades}")
    print(f"win_rate     : {perf.win_rate:.2%}")


if __name__ == "__main__":
    main()

