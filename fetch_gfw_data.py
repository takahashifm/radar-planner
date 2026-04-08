#!/usr/bin/env python3
"""
Global Fishing Watch (GFW) データ取得スクリプト

指定エリア・期間・国のデータを取得し、gfw_data.json として保存する。
GFW API v3 対応（公式ドキュメントに従う）
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
# Step 1: 日本（JPN）の漁船を検索
# ===============================
def search_vessels(headers):
    """指定国の漁船IDを検索"""
    print("🔍 Step 1: 漁船を検索中（国: JPN）...")

    vessel_ids = []
    limit = 100
    offset = 0
    max_pages = 5  # ページング制限（過度な取得を防ぐ）

    for page in range(max_pages):
        print(f"   ページ {page + 1}/{max_pages}...", end=" ")

        params = {
            "query": "*",  # 全漁船検索
            "datasets[0]": "public-global-vessel-identity:latest",
            "limit": limit,
            "offset": offset
        }

        try:
            resp = requests.get(
                f"{API_BASE_URL}/vessels/search",
                params=params,
                headers=headers,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("entries", [])

            if not entries:
                print("終了")
                break

            # flag == "JPN" の漁船をフィルタリング
            for entry in entries:
                registry_info = entry.get("registryInfo", [])
                for reg in registry_info:
                    if reg.get("flag") == FLAG:
                        combined_sources = entry.get("combinedSourcesInfo", [])
                        for source in combined_sources:
                            vessel_id = source.get("vesselId")
                            if vessel_id and vessel_id not in vessel_ids:
                                vessel_ids.append(vessel_id)

            count = len([e for e in entries if any(r.get("flag") == FLAG for r in e.get("registryInfo", []))])
            print(f"{count} 隻")

            offset += limit
        except requests.exceptions.RequestException as e:
            print(f"エラー: {e}")
            break

    print(f"✓ 取得可能なvessel ID: {len(vessel_ids)} 個")
    return vessel_ids[:50]  # 最大50隻まで取得


# ===============================
# Step 2: 各漁船のフィッシングイベントを取得
# ===============================
def fetch_events_for_vessels(vessel_ids, headers):
    """複数の漁船のフィッシングイベントを取得"""
    print(f"\n📥 Step 2: {len(vessel_ids)} 隻のフィッシングイベントを取得中...")

    all_events = []
    event_count = 0

    for idx, vessel_id in enumerate(vessel_ids):
        print(f"   [{idx + 1}/{len(vessel_ids)}] Vessel ID: {vessel_id[:8]}...", end=" ")

        params = {
            f"vessels[0]": vessel_id,
            "datasets[0]": "public-global-fishing-events:latest",
            "start-date": START_DATE,
            "end-date": END_DATE,
            "limit": 100,
            "offset": 0
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
            events = data.get("entries", [])

            # BBOX フィルタリング（クライアント側）
            filtered = [
                e for e in events
                if BBOX["south"] <= e.get("position", {}).get("lat", 0) <= BBOX["north"]
                and BBOX["west"] <= e.get("position", {}).get("lon", 0) <= BBOX["east"]
            ]

            all_events.extend(filtered)
            event_count += len(filtered)
            print(f"{len(filtered)} 件")

        except requests.exceptions.RequestException as e:
            print(f"エラー: {e}")
            continue

    print(f"✓ 合計 {event_count:,} 件のイベントを取得しました")
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
        position = evt.get("position", {})
        vessel = evt.get("vessel", {})

        entry = {
            "position": {
                "lat": position.get("lat"),
                "lon": position.get("lon"),
            },
            "vessel": {
                "name": vessel.get("name", "Unknown"),
                "flag": vessel.get("ssvid", ""),  # SSVID または MMSIを使用
            },
            "gear": evt.get("type", "fishing"),  # type: fishing, porting, loitering など
            "start": evt.get("start", ""),
            "end": evt.get("end", ""),
        }

        # 有効な位置情報があるかチェック
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

    try:
        vessel_ids = search_vessels(headers)
        if vessel_ids:
            events = fetch_events_for_vessels(vessel_ids, headers)
            convert_and_save(events)
        else:
            print("⚠️  該当する漁船が見つかりません")
            output_data = {"entries": []}
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("✅ 完了しました！")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n⚠️  ユーザーが中断しました")
        sys.exit(0)


if __name__ == "__main__":
    main()
