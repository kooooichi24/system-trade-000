"""
01_data_fetching.py - 株価データの取得

このスクリプトでは、Yahoo Finance APIを使用して
株価データを取得する方法を学びます。
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Yahoo Financeから株価データを取得する

    Parameters:
    -----------
    ticker : str
        銘柄のティッカーシンボル（例: "AAPL", "7203.T"）
    period : str
        データ取得期間（"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"）

    Returns:
    --------
    pd.DataFrame
        OHLCVデータ（始値、高値、安値、終値、出来高）
    """
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    return df


def fetch_stock_data_by_date(
    ticker: str, start_date: str, end_date: str
) -> pd.DataFrame:
    """
    指定した期間の株価データを取得する

    Parameters:
    -----------
    ticker : str
        銘柄のティッカーシンボル
    start_date : str
        開始日（YYYY-MM-DD形式）
    end_date : str
        終了日（YYYY-MM-DD形式）

    Returns:
    --------
    pd.DataFrame
        OHLCVデータ
    """
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    return df


def fetch_multiple_stocks(tickers: list, period: str = "1y") -> dict:
    """
    複数銘柄のデータを一括取得する

    Parameters:
    -----------
    tickers : list
        ティッカーシンボルのリスト
    period : str
        データ取得期間

    Returns:
    --------
    dict
        銘柄ごとのDataFrameを格納した辞書
    """
    data = {}
    for ticker in tickers:
        try:
            data[ticker] = fetch_stock_data(ticker, period)
            print(f"✓ {ticker} のデータを取得しました")
        except Exception as e:
            print(f"✗ {ticker} のデータ取得に失敗: {e}")
    return data


def get_stock_info(ticker: str) -> dict:
    """
    銘柄の基本情報を取得する

    Parameters:
    -----------
    ticker : str
        ティッカーシンボル

    Returns:
    --------
    dict
        銘柄情報
    """
    stock = yf.Ticker(ticker)
    return stock.info


# =============================================================================
# メイン処理（実行例）
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("株価データ取得のサンプル")
    print("=" * 60)

    # ----- 例1: 単一銘柄のデータ取得 -----
    print("\n【例1】Appleの過去1年間の株価データを取得")
    print("-" * 40)

    aapl_data = fetch_stock_data("AAPL", period="1y")
    print(f"データ件数: {len(aapl_data)} 日分")
    print(f"期間: {aapl_data.index[0].strftime('%Y-%m-%d')} 〜 {aapl_data.index[-1].strftime('%Y-%m-%d')}")
    print("\n最新5日間のデータ:")
    print(aapl_data.tail())

    # ----- 例2: 日付指定でのデータ取得 -----
    print("\n" + "=" * 60)
    print("【例2】期間を指定してデータを取得")
    print("-" * 40)

    # 過去3ヶ月のデータを取得
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    msft_data = fetch_stock_data_by_date("MSFT", start_date, end_date)
    print(f"Microsoft のデータを取得: {start_date} 〜 {end_date}")
    print(f"データ件数: {len(msft_data)} 日分")
    print(msft_data.head())

    # ----- 例3: 複数銘柄の一括取得 -----
    print("\n" + "=" * 60)
    print("【例3】複数銘柄のデータを一括取得")
    print("-" * 40)

    # 有名なテック株
    tech_stocks = ["AAPL", "GOOGL", "MSFT", "AMZN"]
    all_data = fetch_multiple_stocks(tech_stocks, period="6mo")

    print("\n各銘柄の最新終値:")
    for ticker, df in all_data.items():
        if not df.empty:
            latest_close = df["Close"].iloc[-1]
            print(f"  {ticker}: ${latest_close:.2f}")

    # ----- 例4: 日本株のデータ取得 -----
    print("\n" + "=" * 60)
    print("【例4】日本株のデータを取得（トヨタ自動車）")
    print("-" * 40)

    # 日本株は「銘柄コード.T」の形式
    toyota_data = fetch_stock_data("7203.T", period="1mo")
    print(f"トヨタ自動車 (7203) のデータ: {len(toyota_data)} 日分")
    print(toyota_data.tail())

    # ----- 例5: 銘柄情報の取得 -----
    print("\n" + "=" * 60)
    print("【例5】銘柄の基本情報を取得")
    print("-" * 40)

    info = get_stock_info("AAPL")
    print(f"会社名: {info.get('longName', 'N/A')}")
    print(f"セクター: {info.get('sector', 'N/A')}")
    print(f"時価総額: ${info.get('marketCap', 0):,.0f}")
    print(f"PER: {info.get('trailingPE', 'N/A')}")
    print(f"配当利回り: {info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "配当利回り: N/A")

    print("\n" + "=" * 60)
    print("データ取得のサンプル完了！")
    print("次は 02_technical_indicators.py でテクニカル指標を学びましょう")
    print("=" * 60)
