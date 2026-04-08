#!/usr/bin/env python3
"""
Global Fishing Watch (GFW) データ取得スクリプト

指定エリア・期間・国のデータを取得し、gfw_data.json として保存する。
最新のGFW API v3に対応（フィッシングイベントAPI）
"""

import os
import json
import sys
from datetime import datetime
import requests


# ===============================
# 設定
# ===============================
API_BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"
API_KEY = os.environ.get("GFW_API_KEY")

# 取得パラメータ
BBOX = {
    "west": 140.0,
    "east": 150.0,
    "south": 34.0,
    "north": 44.0,
}
START_DATE = "2022-04-01"
END_DATE = "2026-03-31"
FLAG = "JPN"
OUTPUT_FILE = "gfw_data.json"


# ===============================
# Step 1: 件数確認
# ===============================
def get_event_count(headers):
    """フィッシングイベント件数を確認"""
    print("🔍 Step 1: フィッシングイベント件数を確認中...")

    # queryパラメータ：タイムスタンプ範囲とBBOXでフィルタ
    query = {
        "and": [
            {
                "field": "startTime",
                "value": {"range": [f"{START_DATE}T00:00:00Z", f"{END_DATE}T23:59:59Z"]}
            },
            {
                "field": "latitude",
                "value": {"range": [BBOX["south"], BBOX["north"]]}
            },
            {
                "field": "longitude",
                "value": {"range": [BBOX["west"], BBOX["east"]]}
            }
        ]
    }

    params = {
        "datasets[0]": "public-global-fishing-events:v3.0",
        "limit": 1,
        "offset": 0,
        "query": json.dumps(query)
    }

    try:
        resp = requests.get(
            f"{API_BASE_URL}/events",
            params=params,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        total = data.get("total", 0)
        print(f"✓ 取得対象イベント数: {total:,} 件")

        if total > 50000:
            print(f"⚠️  警告: イベント数が多い ({total:,} 件)")
            response = input("続行しますか？ (y/n): ")
            if response.lower() != "y":
                print("中止しました")
                sys.exit(0)

        return total, data.get("entries", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ API呼び出しエラー: {e}")
        sys.exit(1)


# ===============================
# Step 2: データ取得
# ===============================
def fetch_events(total_count, headers):
    """全イベントをページングで取得"""
    print(f"\n📥 Step 2: {total_count:,} 件のデータを取得中...")

    all_events = []
    page_size = 500  # GFWは1リクエストで最大500件
    offset = 0

    query = {
        "and": [
            {
                "field": "startTime",
                "value": {"range": [f"{START_DATE}T00:00:00Z", f"{END_DATE}T23:59:59Z"]}
            },
            {
                "field": "latitude",
                "value": {"range": [BBOX["south"], BBOX["north"]]}
            },
            {
                "field": "longitude",
                "value": {"range": [BBOX["west"], BBOX["east"]]}
            }
        ]
    }

    while offset < total_count:
        print(f"   取得中... {min(offset + page_size, total_count)} / {total_count}", end="\r")

        params = {
            "datasets[0]": "public-global-fishing-events:v3.0",
            "limit": page_size,
            "offset": offset,
            "query": json.dumps(query)
        }

        try:
            resp = requests.get(
                f"{API_BASE_URL}/events",
                params=params,
                headers=headers,
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            events = data.get("entries", [])

            if not events:
                break

            all_events.extend(events)
            offset += page_size
        except requests.exceptions.RequestException as e:
            print(f"❌ API呼び出しエラー (offset={offset}): {e}")
            sys.exit(1)

    print(f"   ✓ {len(all_events):,} 件を取得しました        ")
    return all_events


# ===============================
# Step 3: JSON形式に変換・保存
# ===============================
def convert_and_save(events):
    """GFW APIデータをHTMLで読み込める形式に変換して保存"""
    print(f"\n💾 Step 3: gfw_data.json を生成中...")

    # renderGFWEvents() が期待するフォーマットに変換
    entries = []
    for evt in events:
        # フィッシングイベント API のレスポンス形式
        # https://github.com/GlobalFishingWatch/gfw-api-docs
        position = evt.get("position", {})
        vessel = evt.get("vessel", {})

        entry = {
            "position": {
                "lat": position.get("latitude", position.get("lat")),
                "lon": position.get("longitude", position.get("lon")),
            },
            "vessel": {
                "name": vessel.get("name", "Unknown"),
                "flag": vessel.get("flag", ""),
            },
            "gear": evt.get("type", ""),  # FISHING / PORTING / LOITERING など
            "start": evt.get("startTime", ""),
            "end": evt.get("endTime", ""),
        }

        # 不要なNoneフィールドをフィルタ
        if entry["position"]["lat"] is not None and entry["position"]["lon"] is not None:
            entries.append(entry)

    output_data = {"entries": entries}

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"✓ {OUTPUT_FILE} を作成しました ({len(entries)} 件のエントリ)")
    except IOError as e:
        print(f"❌ ファイル保存エラー: {e}")
        sys.exit(1)


# ===============================
# Main
# ===============================
def main():
    print("=" * 60)
    print("Global Fishing Watch データ取得スクリプト")
    print("=" * 60)
    print(f"エリア: 東経 {BBOX['west']}°〜{BBOX['east']}°, 北緯 {BBOX['south']}°〜{BBOX['north']}°")
    print(f"期間: {START_DATE} 〜 {END_DATE}")
    print(f"対象国: {FLAG}")
    print()

    if not API_KEY:
        print("❌ エラー: 環境変数 GFW_API_KEY が設定されていません")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {API_KEY}"}

    total, first_page = get_event_count(headers)
    if total > 0:
        events = first_page.copy()  # 最初のページはすでに取得済み
        if total > 1:
            events.extend(fetch_events(total - 1, headers))
        convert_and_save(events)
    else:
        print("⚠️  該当するイベントが見つかりません")
        output_data = {"entries": []}
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ 完了しました！")
    print("=" * 60)


if __name__ == "__main__":
    main()
