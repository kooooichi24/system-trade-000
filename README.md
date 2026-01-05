# システムトレード学習ガイド 📈

このリポジトリは、システムトレード（アルゴリズムトレーディング）を基礎から学ぶための学習教材です。

## 📚 目次

1. **基礎知識** (`docs/01_basics.md`)
   - システムトレードとは
   - 必要な知識とスキル
   - リスク管理の基本

2. **データ取得** (`src/01_data_fetching.py`)
   - 株価データの取得方法
   - データの前処理

3. **テクニカル指標** (`src/02_technical_indicators.py`)
   - 移動平均線 (SMA, EMA)
   - RSI（相対力指数）
   - MACD
   - ボリンジャーバンド

4. **バックテスト** (`src/03_backtest.py`)
   - バックテストの基本
   - パフォーマンス評価指標

5. **トレード戦略** (`src/04_strategies.py`)
   - 移動平均クロス戦略
   - RSI戦略
   - 戦略の組み合わせ

## 🚀 セットアップ

```bash
# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
```

## 📁 プロジェクト構成

```
.
├── README.md              # このファイル
├── requirements.txt       # 依存パッケージ
├── docs/                  # ドキュメント
│   └── 01_basics.md      # 基礎知識
├── src/                   # ソースコード
│   ├── 01_data_fetching.py
│   ├── 02_technical_indicators.py
│   ├── 03_backtest.py
│   └── 04_strategies.py
└── notebooks/             # Jupyter Notebook（対話的学習用）
    └── system_trading_tutorial.ipynb
```

## ⚠️ 注意事項

- このリポジトリは**学習目的**で作成されています
- 実際のトレードを行う前に、十分なテストと理解が必要です
- 投資には常にリスクが伴います
- 過去のパフォーマンスは将来の結果を保証するものではありません

## 📖 学習の進め方

1. まず `docs/01_basics.md` を読んで基礎概念を理解する
2. 各Pythonファイルを順番に実行しながら学ぶ
3. コードを改造して、自分なりの戦略を試してみる
4. バックテストで戦略の有効性を検証する

## 🔗 参考リソース

- [Investopedia - Algorithmic Trading](https://www.investopedia.com/terms/a/algorithmictrading.asp)
- [QuantStart](https://www.quantstart.com/)
- [Backtrader Documentation](https://www.backtrader.com/docu/)
