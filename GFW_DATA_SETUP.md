# GFWデータ取得セットアップ

## 概要
このスクリプトは、Global Fishing Watch (GFW) API から漁船分布データを取得し、`gfw_data.json` として保存します。

## 前提条件
- Python 3.8以上
- `requests` ライブラリ
- GFW API キー

## セットアップ手順

### 1. 必要なライブラリをインストール
```bash
pip install requests
```

### 2. GFW APIキーを環境変数に設定
```bash
export GFW_API_KEY="your-api-key-here"
```

### 3. スクリプトを実行
```bash
python3 fetch_gfw_data.py
```

## スクリプト動作フロー

1. **Step 1: 件数確認**
   - APIに対象データの件数を確認
   - データが膨大な場合は警告を表示
   - ユーザーに続行確認を求める

2. **Step 2: データ取得**
   - ページング（1000件/ページ）で全データを取得
   - 進捗を表示

3. **Step 3: JSON生成**
   - `gfw_data.json` を出力
   - HTMLの `renderGFWEvents()` が期待する形式に変換

## 出力ファイル：`gfw_data.json`

```json
{
  "entries": [
    {
      "position": { "lat": 35.0, "lon": 141.0 },
      "vessel": { "name": "第一漁丸", "flag": "JPN" },
      "gear": "purse_seines",
      "start": "2022-05-01T08:00:00Z",
      "end":   "2022-05-01T12:00:00Z"
    }
  ]
}
```

## パラメータのカスタマイズ

スクリプト内の以下部分を編集して、取得パラメータを変更できます：

```python
# 設定
BBOX = {
    "west": 140.0,
    "east": 150.0,
    "south": 34.0,
    "north": 44.0,
}
START_DATE = "2022-04-01"
END_DATE = "2026-03-31"
FLAG = "JPN"
```

- **BBOX**：取得エリア（西経度、東経度、南緯度、北緯度）
- **START_DATE / END_DATE**：取得期間（YYYY-MM-DD形式）
- **FLAG**：対象国の ISO 3166-1 alpha-3 コード（例：JPN=日本、KOR=韓国）

## トラブルシューティング

### エラー：GFW_API_KEY が設定されていない
```
❌ エラー: 環境変数 GFW_API_KEY が設定されていません
```
→ 環境変数を設定してください：
```bash
export GFW_API_KEY="your-key"
```

### エラー：403 Forbidden / 404 Not Found
→ APIキーが無効、権限不足、またはAPI仕様が変わった可能性があります。
→ GFWの公式ドキュメントで最新の API 仕様を確認してください：
   https://github.com/GlobalFishingWatch/gfw-api-docs

### エラー：422 Unprocessable Entity
→ API リクエスト形式が無効な可能性があります。最新の API 仕様を確認してください。

### 警告：イベント数が多い
→ ユーザーが続行確認を求められます。データ量が大きい場合は、エリア・期間を絞るか、FLAG を変更してください。

## データ検証

生成された `gfw_data.json` は、このツールのHTMLから自動的に読み込まれます：
- アプリケーション起動時に自動的に `gfw_data.json` をロード
- 地図上にマーカーが表示されます
- 同時に複数の漁船データが地図上で可視化されます
