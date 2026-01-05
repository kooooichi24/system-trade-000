# system-trade-000

OSSを土台に「バックテスト → ペーパートレード」までを最小構成で通すためのリポジトリです。

## 最小PoC（oss-poc）

このPoCは **`alpaca-py` で日足データ取得 → `vectorbt` でMAクロスのバックテスト → （任意で）Alpacaペーパー発注** を1本のCLIで実行します。

### セットアップ

- **前提**: Python 3.11+

#### uvを使う場合（推奨）

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

#### pipを使う場合

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 環境変数（Alpaca）

`env.example` を参考に `.env` を作成して、以下を設定してください。

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_PAPER`（true推奨）
- `ALPACA_DATA_FEED`（`iex` 推奨。`sip`は要契約）

### 実行（データ取得→バックテスト）

```bash
st000-poc --symbol SPY --start 2024-01-01 --end 2025-01-01 --fast 10 --slow 30
```

### 実行（+ ペーパー発注）

最終バーのシグナルに応じて、**buy（未保有時）/ sell（保有時）** を1回だけ送ります。
安全のため、実際の送信は `--submit-order` を付けたときだけ行います。

```bash
st000-poc --symbol SPY --start 2024-01-01 --end 2025-01-01 --fast 10 --slow 30 --submit-order --notional 100
```

### 取得バーの保存

```bash
st000-poc --symbol SPY --save-bars
```

