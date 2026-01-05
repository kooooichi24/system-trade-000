from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def _default_start_end_utc() -> tuple[str, str]:
    # 日足PoCなので日付で扱いやすいYYYY-MM-DDをデフォルトにする
    end = datetime.now(tz=ZoneInfo("UTC")).date()
    start = end - timedelta(days=365)
    return start.isoformat(), end.isoformat()


def build_parser() -> argparse.ArgumentParser:
    start_default, end_default = _default_start_end_utc()

    p = argparse.ArgumentParser(
        prog="st000-poc",
        description="Alpacaで日足取得 → vectorbtでMAクロスBT → (任意) Alpacaペーパー発注 の最小PoC",
    )
    p.add_argument("--symbol", default="SPY", help="銘柄 (例: SPY)")
    p.add_argument("--start", default=start_default, help="開始 (YYYY-MM-DD または ISO8601)")
    p.add_argument("--end", default=end_default, help="終了 (YYYY-MM-DD または ISO8601)")
    p.add_argument("--fast", type=int, default=10, help="短期MAウィンドウ")
    p.add_argument("--slow", type=int, default=30, help="長期MAウィンドウ")

    p.add_argument("--init-cash", type=float, default=10_000.0, help="初期資金")
    p.add_argument("--fees", type=float, default=0.0, help="手数料率 (例: 0.001 = 0.1%%)")
    p.add_argument("--slippage", type=float, default=0.0, help="スリッページ率 (例: 0.0005)")

    p.add_argument(
        "--adjustment",
        default="all",
        choices=["raw", "split", "dividend", "all"],
        help="株価調整 (Alpaca historical data)",
    )
    p.add_argument(
        "--data-feed",
        default=None,
        choices=["iex", "sip"],
        help="データフィード。未指定なら環境変数ALPACA_DATA_FEED(なければiex)",
    )

    p.add_argument(
        "--dotenv",
        default=".env",
        help="dotenvファイルパス（存在すれば読み込む）。無効化は --no-dotenv",
    )
    p.add_argument("--no-dotenv", action="store_true", help="dotenvを読まない")

    p.add_argument("--save-bars", action="store_true", help="取得したバーを保存する")
    p.add_argument(
        "--bars-path",
        default=None,
        help="バー保存先（未指定なら data/bars_<symbol>.parquet）",
    )

    p.add_argument(
        "--submit-order",
        action="store_true",
        help="（危険）実際にAlpacaへペーパー注文を送る。未指定ならdry-run",
    )
    p.add_argument("--qty", type=int, default=1, help="発注株数（buy時のデフォルト）")
    p.add_argument("--notional", type=float, default=None, help="buy時のnotional（$）。qtyより優先")

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    # 重い依存（alpaca-py / vectorbt）はここで遅延importして、--helpなどは軽くする
    from system_trade_000.poc import run_poc

    run_poc(args)


