from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class AlpacaSettings:
    api_key: str
    secret_key: str
    paper: bool
    data_feed: str  # "iex" | "sip"


def _strtobool(s: str) -> bool:
    return s.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def maybe_load_dotenv(dotenv_path: str | None, enabled: bool) -> None:
    if not enabled or not dotenv_path:
        return
    p = Path(dotenv_path)
    if not p.exists():
        return
    # python-dotenvは任意（依存には入れているが、壊れても動けるようにしておく）
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    load_dotenv(dotenv_path=p.as_posix(), override=False)


def load_settings(data_feed_override: str | None = None) -> AlpacaSettings:
    api_key = os.getenv("ALPACA_API_KEY", "").strip()
    secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip()
    if not api_key or not secret_key:
        raise SystemExit(
            "環境変数 ALPACA_API_KEY / ALPACA_SECRET_KEY が未設定です。"
            " env.example を参考に .env を用意してください。"
        )

    paper = _strtobool(os.getenv("ALPACA_PAPER", "true"))
    data_feed = (data_feed_override or os.getenv("ALPACA_DATA_FEED", "iex")).strip().lower()
    if data_feed not in {"iex", "sip"}:
        raise SystemExit("ALPACA_DATA_FEED は iex または sip を指定してください。")

    return AlpacaSettings(api_key=api_key, secret_key=secret_key, paper=paper, data_feed=data_feed)


def parse_iso_datetime(s: str, *, as_end: bool = False) -> datetime:
    s = s.strip()
    if len(s) == 10:
        # YYYY-MM-DD
        dt = datetime.fromisoformat(s)
        if as_end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999_999)
    else:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def fetch_daily_bars(
    settings: AlpacaSettings,
    symbol: str,
    start: datetime,
    end: datetime,
    adjustment: str = "all",
):
    # Alpaca market data
    from alpaca.data.historical import StockHistoricalDataClient  # type: ignore
    from alpaca.data.requests import StockBarsRequest  # type: ignore
    from alpaca.data.timeframe import TimeFrame  # type: ignore
    from alpaca.data.enums import DataFeed  # type: ignore

    feed = DataFeed.IEX if settings.data_feed == "iex" else DataFeed.SIP

    client = StockHistoricalDataClient(settings.api_key, settings.secret_key)
    req = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        adjustment=adjustment,
        feed=feed,
    )
    resp = client.get_stock_bars(req)
    df = resp.df

    # resp.df は MultiIndex (symbol, timestamp) になりがちなので単一銘柄に整形
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"pandas の import に失敗しました: {e}")

    if df is None or len(df) == 0:
        raise SystemExit("バーが取得できませんでした（銘柄/期間/フィードを確認してください）。")

    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level=0)
    df = df.sort_index()

    # indexをUTCに寄せておく（後続のベクトル化・保存で安定）
    if getattr(df.index, "tz", None) is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    return df


def ma_cross_signals(close, fast: int, slow: int):
    if fast <= 0 or slow <= 0:
        raise SystemExit("--fast/--slow は正の整数にしてください。")
    if fast >= slow:
        raise SystemExit("--fast は --slow より小さくしてください（例: 10 と 30）。")

    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    entries = (fast_ma > slow_ma).fillna(False)
    exits = (fast_ma < slow_ma).fillna(False)
    return entries, exits


def run_vectorbt_backtest(close, entries, exits, init_cash: float, fees: float, slippage: float):
    import vectorbt as vbt  # type: ignore

    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=init_cash,
        fees=fees,
        slippage=slippage,
        freq="1D",
    )
    return pf


def _default_bars_path(symbol: str) -> Path:
    return Path("data") / f"bars_{symbol}.parquet"


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def maybe_save_bars(df, path: Path) -> None:
    _ensure_parent_dir(path)
    # Parquetが無い環境もありうるのでfallbackを用意
    try:
        df.to_parquet(path)
    except Exception:
        csv_path = path.with_suffix(".csv")
        df.to_csv(csv_path)
        print(f"[save] parquet保存に失敗したためCSVに保存しました: {csv_path}")
        return
    print(f"[save] bars saved: {path}")


def decide_paper_action(entries, exits) -> str | None:
    if len(entries) == 0 or len(exits) == 0:
        return None
    last_entry = bool(entries.iloc[-1])
    last_exit = bool(exits.iloc[-1])
    if last_entry and not last_exit:
        return "buy"
    if last_exit and not last_entry:
        return "sell"
    return None


def maybe_submit_paper_order(
    settings: AlpacaSettings,
    symbol: str,
    action: str | None,
    qty: int,
    notional: float | None,
    submit: bool,
):
    if action is None:
        print("[order] 最終バーでは売買シグナルが出ていないため、発注なし。")
        return

    from alpaca.common.exceptions import APIError  # type: ignore
    from alpaca.trading.client import TradingClient  # type: ignore
    from alpaca.trading.enums import OrderSide, TimeInForce  # type: ignore
    from alpaca.trading.requests import MarketOrderRequest  # type: ignore

    trading = TradingClient(settings.api_key, settings.secret_key, paper=settings.paper)

    has_position = False
    position_qty: int | None = None
    try:
        pos = trading.get_open_position(symbol)
        # qtyは文字列で返ってくることがある
        position_qty = int(float(getattr(pos, "qty", 0)))
        has_position = position_qty != 0
    except APIError:
        has_position = False

    if action == "buy" and has_position:
        print("[order] buyシグナルだが既にポジション保有中のためスキップ。")
        return
    if action == "sell" and not has_position:
        print("[order] sellシグナルだがポジションが無いためスキップ。")
        return

    if action == "sell":
        order_qty = position_qty if position_qty is not None else qty
        req = MarketOrderRequest(
            symbol=symbol,
            qty=order_qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
    else:
        if notional is not None:
            req = MarketOrderRequest(
                symbol=symbol,
                notional=notional,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
        else:
            req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )

    if not submit:
        print("[order][dry-run] 発注内容:", req)
        print("  実際に送るには --submit-order を付けてください。")
        return

    res = trading.submit_order(req)
    print("[order] submitted:", res)


def run_poc(args) -> None:
    maybe_load_dotenv(args.dotenv, enabled=not args.no_dotenv)
    settings = load_settings(data_feed_override=args.data_feed)

    symbol = args.symbol.strip().upper()
    start_dt = parse_iso_datetime(args.start, as_end=False)
    end_dt = parse_iso_datetime(args.end, as_end=True)
    if start_dt >= end_dt:
        raise SystemExit("--start は --end より前の日時にしてください。")

    df = fetch_daily_bars(
        settings=settings,
        symbol=symbol,
        start=start_dt,
        end=end_dt,
        adjustment=args.adjustment,
    )

    close = df["close"].astype(float)
    entries, exits = ma_cross_signals(close, fast=args.fast, slow=args.slow)

    pf = run_vectorbt_backtest(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=float(args.init_cash),
        fees=float(args.fees),
        slippage=float(args.slippage),
    )

    # 最小の可視化：statsを標準出力に出す
    print("=== backtest stats ===")
    try:
        stats = pf.stats()
        print(stats.to_string())
    except Exception:
        # vectorbtの出力形式差分に備えて最低限の情報を出す
        print("final value:", float(pf.value().iloc[-1]))

    action = decide_paper_action(entries, exits)
    print(f"=== latest signal ({symbol}) ===")
    last_ts = df.index[-1]
    last_date = last_ts.date() if hasattr(last_ts, "date") else last_ts
    print("last_date:", last_date)
    print("action:", action or "none")

    if args.save_bars:
        out = Path(args.bars_path) if args.bars_path else _default_bars_path(symbol)
        maybe_save_bars(df, out)

    maybe_submit_paper_order(
        settings=settings,
        symbol=symbol,
        action=action,
        qty=int(args.qty),
        notional=float(args.notional) if args.notional is not None else None,
        submit=bool(args.submit_order),
    )


