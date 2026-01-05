"""
03_backtest.py - バックテストの基礎

このスクリプトでは、トレード戦略を過去データで
シミュレーションする方法を学びます。
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional


@dataclass
class Trade:
    """個別取引を記録するクラス"""
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    position: str = "long"  # "long" or "short"
    size: float = 1.0

    @property
    def profit(self) -> Optional[float]:
        """取引の損益を計算"""
        if self.exit_price is None:
            return None
        if self.position == "long":
            return (self.exit_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.exit_price) * self.size

    @property
    def return_pct(self) -> Optional[float]:
        """取引のリターン率を計算"""
        if self.exit_price is None:
            return None
        if self.position == "long":
            return (self.exit_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - self.exit_price) / self.entry_price * 100


class Backtester:
    """
    シンプルなバックテストエンジン

    特徴:
    - 日次データでのバックテスト
    - ロング/ショートポジション対応
    - 取引コストの考慮
    - 詳細なパフォーマンス指標
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 0.1% の取引手数料
    ):
        """
        Parameters:
        -----------
        initial_capital : float
            初期資金
        commission : float
            取引手数料率（往復）
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.reset()

    def reset(self):
        """バックテスト状態をリセット"""
        self.capital = self.initial_capital
        self.position = 0  # 保有株数
        self.position_type = None  # "long" or "short"
        self.trades = []  # 取引履歴
        self.current_trade = None
        self.equity_curve = []

    def run(self, df: pd.DataFrame, signals: pd.Series) -> dict:
        """
        バックテストを実行する

        Parameters:
        -----------
        df : pd.DataFrame
            株価データ（少なくとも 'Close' カラムが必要）
        signals : pd.Series
            売買シグナル（1: 買い, -1: 売り, 0: ホールド）

        Returns:
        --------
        dict
            パフォーマンス指標
        """
        self.reset()

        for i in range(len(df)):
            date = df.index[i]
            price = df["Close"].iloc[i]
            signal = signals.iloc[i]

            # 現在の資産価値を記録
            if self.position > 0:
                equity = self.capital + self.position * price
            elif self.position < 0:
                # ショートポジションの場合
                equity = self.capital + (self.current_trade.entry_price - price) * abs(self.position)
            else:
                equity = self.capital

            self.equity_curve.append({"date": date, "equity": equity})

            # シグナルに基づいて売買
            if signal == 1 and self.position <= 0:
                # 買いシグナル
                if self.position < 0:
                    # ショートポジションをクローズ
                    self._close_position(date, price)
                # ロングポジションを開く
                self._open_position(date, price, "long")

            elif signal == -1 and self.position >= 0:
                # 売りシグナル
                if self.position > 0:
                    # ロングポジションをクローズ
                    self._close_position(date, price)
                # （オプション）ショートポジションを開く場合はコメント解除
                # self._open_position(date, price, "short")

        # 最終日にポジションが残っている場合はクローズ
        if self.position != 0:
            self._close_position(df.index[-1], df["Close"].iloc[-1])

        # パフォーマンス指標を計算
        return self._calculate_metrics(df)

    def _open_position(self, date: pd.Timestamp, price: float, position_type: str):
        """ポジションを開く"""
        # 手数料を考慮して購入可能な株数を計算
        available_capital = self.capital * (1 - self.commission)
        shares = available_capital / price

        self.position = shares if position_type == "long" else -shares
        self.position_type = position_type
        self.capital -= self.capital * self.commission  # 手数料

        self.current_trade = Trade(
            entry_date=date,
            entry_price=price,
            position=position_type,
            size=abs(shares),
        )

    def _close_position(self, date: pd.Timestamp, price: float):
        """ポジションをクローズ"""
        if self.current_trade is None:
            return

        self.current_trade.exit_date = date
        self.current_trade.exit_price = price

        # 損益を計算
        if self.position_type == "long":
            proceeds = abs(self.position) * price
        else:
            proceeds = self.current_trade.entry_price * abs(self.position) * 2 - abs(self.position) * price

        # 手数料を引く
        self.capital = proceeds * (1 - self.commission)
        self.trades.append(self.current_trade)

        self.position = 0
        self.position_type = None
        self.current_trade = None

    def _calculate_metrics(self, df: pd.DataFrame) -> dict:
        """パフォーマンス指標を計算"""
        equity_df = pd.DataFrame(self.equity_curve).set_index("date")

        # 基本指標
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        num_trades = len(self.trades)

        if num_trades == 0:
            return {
                "total_return_pct": 0,
                "num_trades": 0,
                "message": "取引が発生しませんでした",
            }

        # 勝敗統計
        winning_trades = [t for t in self.trades if t.profit and t.profit > 0]
        losing_trades = [t for t in self.trades if t.profit and t.profit <= 0]

        win_rate = len(winning_trades) / num_trades * 100 if num_trades > 0 else 0

        # 平均損益
        avg_win = np.mean([t.profit for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.profit for t in losing_trades]) if losing_trades else 0

        # プロフィットファクター
        total_profit = sum(t.profit for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.profit for t in losing_trades)) if losing_trades else 1
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        # 最大ドローダウン
        equity_series = equity_df["equity"]
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # シャープレシオ（年率換算）
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0:
            sharpe_ratio = (
                daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                if daily_returns.std() > 0
                else 0
            )
        else:
            sharpe_ratio = 0

        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.capital,
            "total_return_pct": round(total_return, 2),
            "num_trades": num_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate_pct": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "equity_curve": equity_df,
        }


def plot_backtest_results(
    df: pd.DataFrame, signals: pd.Series, metrics: dict, title: str = ""
):
    """
    バックテスト結果を可視化する

    Parameters:
    -----------
    df : pd.DataFrame
        株価データ
    signals : pd.Series
        売買シグナル
    metrics : dict
        パフォーマンス指標
    title : str
        グラフのタイトル
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # 1. 株価チャートと売買ポイント
    ax1 = axes[0]
    ax1.plot(df.index, df["Close"], label="終値", color="black", linewidth=1)

    # 買いシグナルをマーク
    buy_signals = signals[signals == 1]
    ax1.scatter(
        buy_signals.index,
        df.loc[buy_signals.index, "Close"],
        marker="^",
        color="green",
        s=100,
        label="買い",
        zorder=5,
    )

    # 売りシグナルをマーク
    sell_signals = signals[signals == -1]
    ax1.scatter(
        sell_signals.index,
        df.loc[sell_signals.index, "Close"],
        marker="v",
        color="red",
        s=100,
        label="売り",
        zorder=5,
    )

    ax1.set_ylabel("価格")
    ax1.set_title(f"{title} - バックテスト結果")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # 2. 資産推移
    ax2 = axes[1]
    equity_curve = metrics.get("equity_curve")
    if equity_curve is not None:
        ax2.plot(equity_curve.index, equity_curve["equity"], color="blue", linewidth=1)
        ax2.axhline(
            y=metrics["initial_capital"],
            color="gray",
            linestyle="--",
            alpha=0.5,
            label="初期資金",
        )
    ax2.set_ylabel("資産額")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    # 3. ドローダウン
    ax3 = axes[2]
    if equity_curve is not None:
        equity_series = equity_curve["equity"]
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max * 100
        ax3.fill_between(equity_curve.index, drawdown, 0, alpha=0.5, color="red")
    ax3.set_ylabel("ドローダウン (%)")
    ax3.set_xlabel("日付")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("backtest_results.png", dpi=150, bbox_inches="tight")
    print("グラフを 'backtest_results.png' に保存しました")
    plt.close()


def print_metrics(metrics: dict):
    """パフォーマンス指標を表示"""
    print("\n" + "=" * 50)
    print("📊 バックテスト結果")
    print("=" * 50)

    print(f"\n💰 資金")
    print(f"  初期資金: ¥{metrics['initial_capital']:,.0f}")
    print(f"  最終資金: ¥{metrics['final_capital']:,.0f}")
    print(f"  総リターン: {metrics['total_return_pct']:+.2f}%")

    print(f"\n📈 取引統計")
    print(f"  取引回数: {metrics['num_trades']}")
    print(f"  勝ち: {metrics['winning_trades']} / 負け: {metrics['losing_trades']}")
    print(f"  勝率: {metrics['win_rate_pct']:.1f}%")

    print(f"\n📉 損益分析")
    print(f"  平均利益: ¥{metrics['avg_win']:,.0f}")
    print(f"  平均損失: ¥{metrics['avg_loss']:,.0f}")
    print(f"  プロフィットファクター: {metrics['profit_factor']:.2f}")

    print(f"\n⚠️ リスク指標")
    print(f"  最大ドローダウン: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  シャープレシオ: {metrics['sharpe_ratio']:.2f}")

    print("\n" + "=" * 50)


# =============================================================================
# メイン処理（実行例）
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("バックテストのサンプル")
    print("=" * 60)

    # データ取得
    print("\nApple (AAPL) の過去2年間のデータを取得...")
    df = yf.Ticker("AAPL").history(period="2y")

    # シンプルな移動平均クロス戦略でシグナルを生成
    print("シンプルな移動平均クロス戦略でシグナルを生成...")

    # 移動平均線を計算
    df["SMA_short"] = df["Close"].rolling(window=20).mean()
    df["SMA_long"] = df["Close"].rolling(window=50).mean()

    # シグナルを生成
    # SMA_short > SMA_long でゴールデンクロス → 買い
    # SMA_short < SMA_long でデッドクロス → 売り
    signals = pd.Series(0, index=df.index)

    for i in range(1, len(df)):
        # ゴールデンクロス（短期が長期を上抜け）
        if (
            df["SMA_short"].iloc[i] > df["SMA_long"].iloc[i]
            and df["SMA_short"].iloc[i - 1] <= df["SMA_long"].iloc[i - 1]
        ):
            signals.iloc[i] = 1

        # デッドクロス（短期が長期を下抜け）
        elif (
            df["SMA_short"].iloc[i] < df["SMA_long"].iloc[i]
            and df["SMA_short"].iloc[i - 1] >= df["SMA_long"].iloc[i - 1]
        ):
            signals.iloc[i] = -1

    # バックテスト実行
    print("\nバックテストを実行中...")
    backtester = Backtester(initial_capital=1000000, commission=0.001)
    metrics = backtester.run(df, signals)

    # 結果表示
    print_metrics(metrics)

    # グラフ作成
    print("\nグラフを作成中...")
    plot_backtest_results(df, signals, metrics, "AAPL - 移動平均クロス戦略")

    # Buy & Hold との比較
    print("\n【Buy & Hold戦略との比較】")
    print("-" * 40)
    buy_hold_return = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0] * 100
    print(f"Buy & Hold リターン: {buy_hold_return:+.2f}%")
    print(f"戦略リターン: {metrics['total_return_pct']:+.2f}%")

    if metrics['total_return_pct'] > buy_hold_return:
        print("✅ 戦略がBuy & Holdを上回りました！")
    else:
        print("❌ Buy & Holdの方が良いパフォーマンスでした")

    print("\n" + "=" * 60)
    print("バックテストのサンプル完了！")
    print("次は 04_strategies.py で様々な戦略を学びましょう")
    print("=" * 60)
