"""
04_strategies.py - トレード戦略の実装

このスクリプトでは、実際のトレード戦略を
実装する方法を学びます。
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod
from typing import Tuple

# バックテスターをインポート
from backtest import Backtester, print_metrics, plot_backtest_results


class Strategy(ABC):
    """戦略の基底クラス"""

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        売買シグナルを生成する

        Returns:
        --------
        pd.Series
            1: 買い, -1: 売り, 0: ホールド
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """戦略名を返す"""
        pass


class SMAcrossStrategy(Strategy):
    """
    移動平均クロス戦略

    短期移動平均が長期移動平均を上抜けたら買い、
    下抜けたら売り。
    """

    def __init__(self, short_window: int = 20, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    @property
    def name(self) -> str:
        return f"SMAクロス({self.short_window}/{self.long_window})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()
        df["SMA_short"] = df["Close"].rolling(window=self.short_window).mean()
        df["SMA_long"] = df["Close"].rolling(window=self.long_window).mean()

        signals = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            # ゴールデンクロス
            if (
                df["SMA_short"].iloc[i] > df["SMA_long"].iloc[i]
                and df["SMA_short"].iloc[i - 1] <= df["SMA_long"].iloc[i - 1]
            ):
                signals.iloc[i] = 1
            # デッドクロス
            elif (
                df["SMA_short"].iloc[i] < df["SMA_long"].iloc[i]
                and df["SMA_short"].iloc[i - 1] >= df["SMA_long"].iloc[i - 1]
            ):
                signals.iloc[i] = -1

        return signals


class RSIStrategy(Strategy):
    """
    RSI戦略

    RSIが売られすぎゾーンから回復したら買い、
    買われすぎゾーンから下落したら売り。
    """

    def __init__(
        self, period: int = 14, oversold: float = 30, overbought: float = 70
    ):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return f"RSI({self.period}, {self.oversold}/{self.overbought})"

    def _calculate_rsi(self, data: pd.Series) -> pd.Series:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = self._calculate_rsi(df["Close"])
        signals = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            # RSIが売られすぎから回復
            if rsi.iloc[i] > self.oversold and rsi.iloc[i - 1] <= self.oversold:
                signals.iloc[i] = 1
            # RSIが買われすぎから下落
            elif rsi.iloc[i] < self.overbought and rsi.iloc[i - 1] >= self.overbought:
                signals.iloc[i] = -1

        return signals


class BollingerBandStrategy(Strategy):
    """
    ボリンジャーバンド戦略

    価格が下限バンドに触れたら買い、
    上限バンドに触れたら売り（平均回帰戦略）。
    """

    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        return f"ボリンジャーバンド({self.window}, {self.num_std}σ)"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()
        df["BB_middle"] = df["Close"].rolling(window=self.window).mean()
        df["BB_std"] = df["Close"].rolling(window=self.window).std()
        df["BB_upper"] = df["BB_middle"] + self.num_std * df["BB_std"]
        df["BB_lower"] = df["BB_middle"] - self.num_std * df["BB_std"]

        signals = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            # 下限バンドを下から上に抜け → 買い
            if (
                df["Close"].iloc[i] > df["BB_lower"].iloc[i]
                and df["Close"].iloc[i - 1] <= df["BB_lower"].iloc[i - 1]
            ):
                signals.iloc[i] = 1
            # 上限バンドを上から下に抜け → 売り
            elif (
                df["Close"].iloc[i] < df["BB_upper"].iloc[i]
                and df["Close"].iloc[i - 1] >= df["BB_upper"].iloc[i - 1]
            ):
                signals.iloc[i] = -1

        return signals


class MACDStrategy(Strategy):
    """
    MACD戦略

    MACD線がシグナル線を上抜けたら買い、
    下抜けたら売り。
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def name(self) -> str:
        return f"MACD({self.fast}/{self.slow}/{self.signal})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        # EMAを計算
        ema_fast = df["Close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=self.slow, adjust=False).mean()

        # MACD線とシグナル線
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()

        signals = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            # MACDがシグナルを上抜け
            if macd_line.iloc[i] > signal_line.iloc[i] and macd_line.iloc[i - 1] <= signal_line.iloc[i - 1]:
                signals.iloc[i] = 1
            # MACDがシグナルを下抜け
            elif macd_line.iloc[i] < signal_line.iloc[i] and macd_line.iloc[i - 1] >= signal_line.iloc[i - 1]:
                signals.iloc[i] = -1

        return signals


class CombinedStrategy(Strategy):
    """
    複合戦略

    複数の戦略を組み合わせて、
    多数決でシグナルを決定する。
    """

    def __init__(self, strategies: list, threshold: float = 0.5):
        """
        Parameters:
        -----------
        strategies : list
            組み合わせる戦略のリスト
        threshold : float
            シグナルを出すための閾値（0.5 = 過半数）
        """
        self.strategies = strategies
        self.threshold = threshold

    @property
    def name(self) -> str:
        names = [s.name for s in self.strategies]
        return f"複合戦略({' + '.join(names)})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        all_signals = pd.DataFrame(index=df.index)

        # 各戦略のシグナルを取得
        for i, strategy in enumerate(self.strategies):
            all_signals[f"strategy_{i}"] = strategy.generate_signals(df)

        # シグナルの合計を計算
        signal_sum = all_signals.sum(axis=1)
        n_strategies = len(self.strategies)

        # 多数決でシグナルを決定
        signals = pd.Series(0, index=df.index)
        signals[signal_sum >= n_strategies * self.threshold] = 1
        signals[signal_sum <= -n_strategies * self.threshold] = -1

        return signals


def compare_strategies(
    df: pd.DataFrame, strategies: list, initial_capital: float = 1000000
) -> pd.DataFrame:
    """
    複数の戦略を比較する

    Parameters:
    -----------
    df : pd.DataFrame
        株価データ
    strategies : list
        比較する戦略のリスト
    initial_capital : float
        初期資金

    Returns:
    --------
    pd.DataFrame
        各戦略のパフォーマンス比較
    """
    results = []
    backtester = Backtester(initial_capital=initial_capital)

    for strategy in strategies:
        signals = strategy.generate_signals(df)
        metrics = backtester.run(df, signals)

        results.append(
            {
                "戦略": strategy.name,
                "リターン(%)": metrics["total_return_pct"],
                "取引回数": metrics["num_trades"],
                "勝率(%)": metrics["win_rate_pct"],
                "最大DD(%)": metrics["max_drawdown_pct"],
                "シャープ": metrics["sharpe_ratio"],
                "PF": metrics["profit_factor"],
            }
        )

    return pd.DataFrame(results)


def optimize_sma_parameters(
    df: pd.DataFrame,
    short_range: Tuple[int, int] = (5, 30),
    long_range: Tuple[int, int] = (20, 100),
    step: int = 5,
) -> pd.DataFrame:
    """
    SMAクロス戦略のパラメータを最適化する

    Parameters:
    -----------
    df : pd.DataFrame
        株価データ
    short_range : tuple
        短期MAの範囲 (min, max)
    long_range : tuple
        長期MAの範囲 (min, max)
    step : int
        パラメータのステップ

    Returns:
    --------
    pd.DataFrame
        パラメータごとのパフォーマンス
    """
    results = []
    backtester = Backtester()

    short_values = range(short_range[0], short_range[1] + 1, step)
    long_values = range(long_range[0], long_range[1] + 1, step)

    total = len(list(short_values)) * len(list(long_values))
    count = 0

    for short in range(short_range[0], short_range[1] + 1, step):
        for long in range(long_range[0], long_range[1] + 1, step):
            if short >= long:
                continue

            strategy = SMAcrossStrategy(short_window=short, long_window=long)
            signals = strategy.generate_signals(df)
            metrics = backtester.run(df, signals)

            results.append(
                {
                    "短期MA": short,
                    "長期MA": long,
                    "リターン(%)": metrics["total_return_pct"],
                    "勝率(%)": metrics["win_rate_pct"],
                    "シャープ": metrics["sharpe_ratio"],
                    "最大DD(%)": metrics["max_drawdown_pct"],
                }
            )

            count += 1

    return pd.DataFrame(results).sort_values("リターン(%)", ascending=False)


# =============================================================================
# メイン処理（実行例）
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("トレード戦略のサンプル")
    print("=" * 60)

    # データ取得
    print("\nApple (AAPL) の過去2年間のデータを取得...")
    df = yf.Ticker("AAPL").history(period="2y")

    # ----- 各戦略の定義 -----
    strategies = [
        SMAcrossStrategy(short_window=20, long_window=50),
        RSIStrategy(period=14, oversold=30, overbought=70),
        BollingerBandStrategy(window=20, num_std=2.0),
        MACDStrategy(fast=12, slow=26, signal=9),
    ]

    # ----- 戦略の比較 -----
    print("\n【戦略の比較】")
    print("-" * 60)

    comparison = compare_strategies(df, strategies)
    print(comparison.to_string(index=False))

    # Buy & Hold との比較
    buy_hold_return = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0] * 100
    print(f"\nBuy & Hold リターン: {buy_hold_return:+.2f}%")

    # ----- 複合戦略 -----
    print("\n" + "=" * 60)
    print("【複合戦略のテスト】")
    print("-" * 60)

    combined = CombinedStrategy(
        strategies=[
            SMAcrossStrategy(20, 50),
            RSIStrategy(),
            MACDStrategy(),
        ],
        threshold=0.66,  # 3つ中2つ以上の一致で取引
    )

    backtester = Backtester(initial_capital=1000000)
    signals = combined.generate_signals(df)
    metrics = backtester.run(df, signals)

    print(f"戦略: {combined.name}")
    print_metrics(metrics)

    # ----- パラメータ最適化 -----
    print("\n" + "=" * 60)
    print("【SMAクロス戦略のパラメータ最適化】")
    print("-" * 60)
    print("パラメータを探索中...")

    optimization_results = optimize_sma_parameters(
        df, short_range=(10, 30), long_range=(30, 80), step=10
    )

    print("\nトップ5のパラメータ組み合わせ:")
    print(optimization_results.head(10).to_string(index=False))

    # 最適パラメータでバックテスト
    best = optimization_results.iloc[0]
    print(f"\n最適パラメータ: 短期MA={int(best['短期MA'])}, 長期MA={int(best['長期MA'])}")

    best_strategy = SMAcrossStrategy(
        short_window=int(best["短期MA"]), long_window=int(best["長期MA"])
    )
    signals = best_strategy.generate_signals(df)
    metrics = backtester.run(df, signals)

    plot_backtest_results(df, signals, metrics, f"AAPL - {best_strategy.name}")

    # ----- 注意事項 -----
    print("\n" + "=" * 60)
    print("⚠️ 重要な注意事項")
    print("=" * 60)
    print("""
1. 過剰最適化に注意
   - 過去データに過度にフィットしたパラメータは、
     将来のデータでは機能しない可能性があります

2. ウォークフォワード分析を推奨
   - データを複数期間に分けてテストする
   - 最適化期間と検証期間を分ける

3. 取引コストの考慮
   - スプレッド、手数料、スリッページなど

4. リスク管理
   - ストップロスの設定
   - ポジションサイジング
   - 分散投資

5. 実運用前のテスト
   - ペーパートレードで十分なテストを行う
   - 少額から開始する
""")

    print("=" * 60)
    print("戦略サンプル完了！")
    print("=" * 60)
