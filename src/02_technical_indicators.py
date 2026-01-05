"""
02_technical_indicators.py - テクニカル指標の計算

このスクリプトでは、株価データから
様々なテクニカル指標を計算する方法を学びます。
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """
    単純移動平均線 (Simple Moving Average) を計算する

    Parameters:
    -----------
    data : pd.Series
        価格データ（通常は終値）
    window : int
        移動平均の期間

    Returns:
    --------
    pd.Series
        SMA値
    """
    return data.rolling(window=window).mean()


def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """
    指数移動平均線 (Exponential Moving Average) を計算する

    EMAは直近のデータにより大きな重みを付けます。

    Parameters:
    -----------
    data : pd.Series
        価格データ
    window : int
        移動平均の期間

    Returns:
    --------
    pd.Series
        EMA値
    """
    return data.ewm(span=window, adjust=False).mean()


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index) を計算する

    RSIは0〜100の範囲で、一般的に：
    - 70以上：買われすぎ
    - 30以下：売られすぎ

    Parameters:
    -----------
    data : pd.Series
        価格データ
    window : int
        計算期間（デフォルト: 14）

    Returns:
    --------
    pd.Series
        RSI値 (0-100)
    """
    # 価格変動を計算
    delta = data.diff()

    # 上昇分と下落分を分離
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    # RSを計算
    rs = gain / loss

    # RSIを計算
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple:
    """
    MACD (Moving Average Convergence Divergence) を計算する

    Parameters:
    -----------
    data : pd.Series
        価格データ
    fast : int
        短期EMAの期間（デフォルト: 12）
    slow : int
        長期EMAの期間（デフォルト: 26）
    signal : int
        シグナル線の期間（デフォルト: 9）

    Returns:
    --------
    tuple
        (MACD線, シグナル線, ヒストグラム)
    """
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    data: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple:
    """
    ボリンジャーバンドを計算する

    Parameters:
    -----------
    data : pd.Series
        価格データ
    window : int
        移動平均の期間（デフォルト: 20）
    num_std : float
        標準偏差の倍数（デフォルト: 2.0）

    Returns:
    --------
    tuple
        (中央線, 上限バンド, 下限バンド)
    """
    middle = calculate_sma(data, window)
    std = data.rolling(window=window).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    return middle, upper, lower


def calculate_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
) -> pd.Series:
    """
    ATR (Average True Range) を計算する

    ATRはボラティリティ（価格変動の大きさ）を測定します。

    Parameters:
    -----------
    high : pd.Series
        高値データ
    low : pd.Series
        安値データ
    close : pd.Series
        終値データ
    window : int
        計算期間（デフォルト: 14）

    Returns:
    --------
    pd.Series
        ATR値
    """
    # True Rangeを計算
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATRを計算（True Rangeの移動平均）
    atr = true_range.rolling(window=window).mean()

    return atr


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    データフレームに全ての主要テクニカル指標を追加する

    Parameters:
    -----------
    df : pd.DataFrame
        OHLCVデータ（Open, High, Low, Close, Volume）

    Returns:
    --------
    pd.DataFrame
        テクニカル指標を追加したデータフレーム
    """
    df = df.copy()

    # 移動平均線
    df["SMA_20"] = calculate_sma(df["Close"], 20)
    df["SMA_50"] = calculate_sma(df["Close"], 50)
    df["EMA_12"] = calculate_ema(df["Close"], 12)
    df["EMA_26"] = calculate_ema(df["Close"], 26)

    # RSI
    df["RSI"] = calculate_rsi(df["Close"])

    # MACD
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = calculate_macd(df["Close"])

    # ボリンジャーバンド
    df["BB_Middle"], df["BB_Upper"], df["BB_Lower"] = calculate_bollinger_bands(
        df["Close"]
    )

    # ATR
    df["ATR"] = calculate_atr(df["High"], df["Low"], df["Close"])

    return df


def plot_with_indicators(df: pd.DataFrame, ticker: str = ""):
    """
    株価とテクニカル指標をグラフで表示する

    Parameters:
    -----------
    df : pd.DataFrame
        テクニカル指標を含むデータフレーム
    ticker : str
        銘柄名（タイトル用）
    """
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

    # 1. 価格チャートとボリンジャーバンド、移動平均線
    ax1 = axes[0]
    ax1.plot(df.index, df["Close"], label="終値", color="black", linewidth=1.5)
    ax1.plot(df.index, df["SMA_20"], label="SMA(20)", color="blue", alpha=0.7)
    ax1.plot(df.index, df["SMA_50"], label="SMA(50)", color="red", alpha=0.7)
    ax1.fill_between(
        df.index, df["BB_Upper"], df["BB_Lower"], alpha=0.2, color="gray", label="BB"
    )
    ax1.set_ylabel("価格")
    ax1.set_title(f"{ticker} 株価チャートとテクニカル指標")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # 2. RSI
    ax2 = axes[1]
    ax2.plot(df.index, df["RSI"], color="purple", linewidth=1)
    ax2.axhline(y=70, color="red", linestyle="--", alpha=0.5, label="買われすぎ(70)")
    ax2.axhline(y=30, color="green", linestyle="--", alpha=0.5, label="売られすぎ(30)")
    ax2.fill_between(df.index, df["RSI"], 70, where=(df["RSI"] >= 70), alpha=0.3, color="red")
    ax2.fill_between(df.index, df["RSI"], 30, where=(df["RSI"] <= 30), alpha=0.3, color="green")
    ax2.set_ylabel("RSI")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)

    # 3. MACD
    ax3 = axes[2]
    ax3.plot(df.index, df["MACD"], label="MACD", color="blue", linewidth=1)
    ax3.plot(df.index, df["MACD_Signal"], label="Signal", color="red", linewidth=1)
    colors = ["green" if val >= 0 else "red" for val in df["MACD_Hist"]]
    ax3.bar(df.index, df["MACD_Hist"], color=colors, alpha=0.5, label="Histogram")
    ax3.axhline(y=0, color="black", linestyle="-", alpha=0.3)
    ax3.set_ylabel("MACD")
    ax3.legend(loc="upper left")
    ax3.grid(True, alpha=0.3)

    # 4. 出来高
    ax4 = axes[3]
    ax4.bar(df.index, df["Volume"], color="steelblue", alpha=0.7)
    ax4.set_ylabel("出来高")
    ax4.set_xlabel("日付")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("technical_indicators.png", dpi=150, bbox_inches="tight")
    print("グラフを 'technical_indicators.png' に保存しました")
    plt.close()


# =============================================================================
# メイン処理（実行例）
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("テクニカル指標の計算サンプル")
    print("=" * 60)

    # データ取得
    print("\nApple (AAPL) の過去1年間のデータを取得...")
    df = yf.Ticker("AAPL").history(period="1y")

    # テクニカル指標を追加
    print("テクニカル指標を計算中...")
    df = add_all_indicators(df)

    # 結果の表示
    print("\n【計算結果】最新10日間のデータ:")
    print("-" * 60)
    display_cols = ["Close", "SMA_20", "RSI", "MACD", "BB_Upper", "BB_Lower"]
    print(df[display_cols].tail(10).round(2))

    # シグナルの解釈例
    print("\n【シグナルの解釈例】")
    print("-" * 60)

    latest = df.iloc[-1]

    # RSIの解釈
    rsi_value = latest["RSI"]
    if rsi_value >= 70:
        rsi_signal = "⚠️ 買われすぎ（売りシグナル）"
    elif rsi_value <= 30:
        rsi_signal = "⚠️ 売られすぎ（買いシグナル）"
    else:
        rsi_signal = "📊 中立"
    print(f"RSI ({rsi_value:.2f}): {rsi_signal}")

    # MACDの解釈
    if latest["MACD"] > latest["MACD_Signal"]:
        macd_signal = "📈 上昇トレンド（買いシグナル）"
    else:
        macd_signal = "📉 下降トレンド（売りシグナル）"
    print(f"MACD: {macd_signal}")

    # ボリンジャーバンドの解釈
    price = latest["Close"]
    if price >= latest["BB_Upper"]:
        bb_signal = "⚠️ 上限バンドに接触（反落の可能性）"
    elif price <= latest["BB_Lower"]:
        bb_signal = "⚠️ 下限バンドに接触（反発の可能性）"
    else:
        bb_signal = "📊 バンド内で推移"
    print(f"ボリンジャーバンド: {bb_signal}")

    # 移動平均線の解釈
    if latest["SMA_20"] > latest["SMA_50"]:
        ma_signal = "📈 短期が長期を上回る（上昇トレンド）"
    else:
        ma_signal = "📉 長期が短期を上回る（下降トレンド）"
    print(f"移動平均線: {ma_signal}")

    # グラフの作成
    print("\nグラフを作成中...")
    plot_with_indicators(df, "AAPL")

    print("\n" + "=" * 60)
    print("テクニカル指標のサンプル完了！")
    print("次は 03_backtest.py でバックテストを学びましょう")
    print("=" * 60)
