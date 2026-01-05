# system-trading-learning（`uv`採用）

Pythonで「システムトレードの検証」を学ぶための最小スターターです。
まずは **CSVがなくても動く** 合成OHLCVデータで、バックテスト→指標出力まで通します。

## セットアップ

このリポジトリは `uv` 前提です。

```bash
# uv が無い場合（例）
python3 -m pip install --user -U uv

# 依存関係インストール & 仮想環境作成
uv sync
```

## まず動かす（合成データ）

```bash
uv run stl --sample
```

## 自分のCSVで動かす

CSVは以下の列を想定します（列名は小文字化して扱います）:

- `date`（または先頭列が日付）
- `open`, `high`, `low`, `close`, `volume`

```bash
uv run stl --csv path/to/ohlcv.csv --fast 20 --slow 60
```

## テスト

```bash
uv run pytest -q
```
