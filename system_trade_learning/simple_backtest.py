import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def get_data(ticker, start_date, end_date):
    """
    Yahoo Financeから株価データを取得する関数
    """
    print(f"{ticker} のデータを取得中...")
    data = yf.download(ticker, start=start_date, end=end_date)
    
    # マルチインデックスカラムの場合に対応（yfinanceのバージョンによって挙動が異なる場合があるため）
    if isinstance(data.columns, pd.MultiIndex):
        data = data.xs(ticker, axis=1, level=1)
        
    return data

def backtest_strategy(data, short_window, long_window):
    """
    単純移動平均線(SMA)を用いたゴールデンクロス・デッドクロス戦略のバックテスト
    """
    # データをコピーして使用
    df = data.copy()
    
    # 移動平均線の計算
    df['Short_MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window=long_window).mean()
    
    # シグナルの生成 (0: ポジションなし, 1: 買い持ち)
    # 短期MA > 長期MA の時に 1 とする
    df['Signal'] = 0.0
    # Long_MAが計算できる期間以降で判定
    df.loc[df.index[long_window:], 'Signal'] = np.where(
        df.loc[df.index[long_window:], 'Short_MA'] > df.loc[df.index[long_window:], 'Long_MA'], 1.0, 0.0
    )
    
    # ポジションの変化（売買タイミング）を取得
    # diff()で差分を取り、1なら買い(0->1), -1なら売り(1->0)
    df['Position'] = df['Signal'].diff()
    
    return df

def calculate_returns(df):
    """
    戦略のリターン計算
    """
    # 前日比のリターンを計算（対数収益率を使う場合もあるが、今回は単純収益率）
    df['Market_Returns'] = df['Close'].pct_change()
    
    # 戦略のリターン = 前日のシグナル * 当日の市場リターン
    # shift(1)することで、シグナルが出た「翌日」の始値〜終値のリターンを取るイメージ（簡易的）
    df['Strategy_Returns'] = df['Signal'].shift(1) * df['Market_Returns']
    
    # 累積リターンの計算
    df['Cumulative_Market_Returns'] = (1 + df['Market_Returns']).cumprod()
    df['Cumulative_Strategy_Returns'] = (1 + df['Strategy_Returns']).cumprod()
    
    return df

def plot_results(df, ticker):
    """
    結果の可視化
    """
    plt.figure(figsize=(14, 7))
    
    # 累積リターンのグラフ
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['Cumulative_Market_Returns'], label='Market (Buy & Hold)', color='gray')
    plt.plot(df.index, df['Cumulative_Strategy_Returns'], label='Strategy (SMA Cross)', color='blue')
    plt.title(f'{ticker} Backtest Results')
    plt.ylabel('Cumulative Returns')
    plt.legend()
    plt.grid(True)
    
    # 移動平均線と売買ポイントのグラフ
    plt.subplot(2, 1, 2)
    plt.plot(df.index, df['Close'], label='Close Price', alpha=0.5, color='black')
    plt.plot(df.index, df['Short_MA'], label='Short MA', alpha=0.7, color='orange')
    plt.plot(df.index, df['Long_MA'], label='Long MA', alpha=0.7, color='purple')
    
    # 買いシグナル（▲）
    plt.plot(df[df['Position'] == 1].index, 
             df['Short_MA'][df['Position'] == 1], 
             '^', markersize=10, color='g', lw=0, label='Buy Signal')
             
    # 売りシグナル（▼）
    plt.plot(df[df['Position'] == -1].index, 
             df['Short_MA'][df['Position'] == -1], 
             'v', markersize=10, color='r', lw=0, label='Sell Signal')
             
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    
    # グラフを保存
    plt.tight_layout()
    plt.savefig('backtest_result.png')
    print("結果のグラフを backtest_result.png に保存しました。")

def main():
    # パラメータ設定
    TICKER = 'SPY' # S&P 500 ETF
    START_DATE = '2020-01-01'
    END_DATE = '2023-12-31'
    SHORT_WINDOW = 50
    LONG_WINDOW = 200
    
    # 1. データ取得
    data = get_data(TICKER, START_DATE, END_DATE)
    
    if data.empty:
        print("データが取得できませんでした。")
        return

    # 2. バックテスト実行
    df = backtest_strategy(data, SHORT_WINDOW, LONG_WINDOW)
    
    # 3. リターン計算
    df = calculate_returns(df)
    
    # 4. 結果表示
    final_return = df['Cumulative_Strategy_Returns'].iloc[-1]
    market_return = df['Cumulative_Market_Returns'].iloc[-1]
    
    print(f"--- 結果サマリー ({TICKER}) ---")
    print(f"期間: {START_DATE} 〜 {END_DATE}")
    print(f"戦略の最終リターン: {final_return:.2f}倍 ({(final_return-1)*100:.1f}%)")
    print(f"市場の最終リターン: {market_return:.2f}倍 ({(market_return-1)*100:.1f}%)")
    
    # 5. グラフ化
    plot_results(df, TICKER)

if __name__ == "__main__":
    main()
