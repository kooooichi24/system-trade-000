from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SampleDataConfig:
    n: int = 800
    start: str = "2020-01-01"
    freq: str = "D"
    seed: int = 7
    start_price: float = 100.0
    drift: float = 0.0002
    vol: float = 0.01


def make_ohlcv(cfg: SampleDataConfig = SampleDataConfig()) -> pd.DataFrame:
    """
    Create synthetic OHLCV data.

    - close: geometric random walk
    - open: previous close + small noise
    - high/low: intraday range around open/close
    - volume: lognormal
    """
    rng = np.random.default_rng(cfg.seed)

    idx = pd.date_range(cfg.start, periods=cfg.n, freq=cfg.freq)
    rets = rng.normal(loc=cfg.drift, scale=cfg.vol, size=cfg.n)
    close = cfg.start_price * np.exp(np.cumsum(rets))

    open_ = np.empty_like(close)
    open_[0] = close[0] * (1.0 + rng.normal(0, cfg.vol / 5))
    open_[1:] = close[:-1] * (1.0 + rng.normal(0, cfg.vol / 5, size=cfg.n - 1))

    base = np.maximum(open_, close)
    spread = np.abs(rng.normal(0, cfg.vol / 2, size=cfg.n))
    high = base * (1.0 + spread)

    base2 = np.minimum(open_, close)
    low = base2 * (1.0 - spread)

    volume = rng.lognormal(mean=12.0, sigma=0.3, size=cfg.n).astype(np.int64)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )
    df.index.name = "date"
    return df

