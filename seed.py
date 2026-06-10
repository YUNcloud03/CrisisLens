"""
seed.py — 寫入固定測試資料（供所有組員共用相同的開發環境）

使用方式：
    python seed.py           # 新增測試資料（保留現有資料）
    python seed.py --reset   # 先清空 reports/events/grid_summary，再寫入

注意：只清除上面三張表，不影響 model_runs / admin_corrections。
"""
import os, sys, json, argparse
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(__file__))

from db.database import init_db, get_conn
from aggregation.event_matcher import aggregate
from aggregation.h3_utils import latlng_to_h3_cell, DEFAULT_RESOLUTION
from aggregation.scoring import calc_report_severity

# ── 固定測試資料 ──────────────────────────────────────────────────
# 每筆都有 lat/lng → 會轉成 H3 cell → 顯示在熱圖
SEED_REPORTS = [
    # ── 台北市信義區：颱風事件（3 筆，應聚合成 1 個事件）──────────
    {
        "city": "台北市", "district": "信義區",
        "location_name": "信義路五段100號附近",
        "latitude": 25.0330, "longitude": 121.5654,
        "disaster_type": "Typhoon or Storm Damage",
        "description": "強風吹倒路樹，擋住車道，電線桿傾斜",
        "has_trapped_people": 0, "has_injured_people": 0, "road_blocked": 1,
        "reported_people_count": 0, "need_help": 1,
        "event_time_offset_min": -90,    # 90 分鐘前
    },
    {
        "city": "台北市", "district": "信義區",
        "location_name": "松仁路與信義路口",
        "latitude": 25.0340, "longitude": 121.5670,
        "disaster_type": "Typhoon or Storm Damage",
        "description": "招牌掉落，玻璃碎片散落路面",
        "has_trapped_people": 0, "has_injured_people": 1, "road_blocked": 1,
        "reported_people_count": 2, "need_help": 1,
        "event_time_offset_min": -60,
    },
    {
        "city": "台北市", "district": "信義區",
        "location_name": "台北101附近",
        "latitude": 25.0336, "longitude": 121.5647,
        "disaster_type": "Typhoon or Storm Damage",
        "description": "廣場積水嚴重，施工圍籬被吹倒",
        "has_trapped_people": 0, "has_injured_people": 0, "road_blocked": 0,
        "reported_people_count": 0, "need_help": 0,
        "event_time_offset_min": -30,
    },

    # ── 台北市大安區：淹水（High 優先級）─────────────────────────
    {
        "city": "台北市", "district": "大安區",
        "location_name": "忠孝東路四段地下道",
        "latitude": 25.0418, "longitude": 121.5503,
        "disaster_type": "Flood",
        "description": "地下道積水超過50公分，車輛受困無法通行",
        "has_trapped_people": 1, "has_injured_people": 0, "road_blocked": 1,
        "reported_people_count": 5, "need_help": 1,
        "event_time_offset_min": -45,
    },
    {
        "city": "台北市", "district": "大安區",
        "location_name": "新生南路與和平東路口",
        "latitude": 25.0380, "longitude": 121.5340,
        "disaster_type": "Flood",
        "description": "路面大量積水，排水孔溢出",
        "has_trapped_people": 0, "has_injured_people": 0, "road_blocked": 1,
        "reported_people_count": 0, "need_help": 1,
        "event_time_offset_min": -20,
    },

    # ── 花蓮縣吉安鄉：地震（High 優先級）────────────────────────
    {
        "city": "花蓮縣", "district": "吉安鄉",
        "location_name": "吉安鄉南濱路段",
        "latitude": 23.9728, "longitude": 121.6040,
        "disaster_type": "Earthquake Damage",
        "description": "建築物外牆龜裂，一樓柱子明顯受損",
        "has_trapped_people": 1, "has_injured_people": 1, "road_blocked": 0,
        "reported_people_count": 3, "need_help": 1,
        "event_time_offset_min": -120,
    },

    # ── 台北市文山區：火災（Medium 優先級）────────────────────────
    {
        "city": "台北市", "district": "文山區",
        "location_name": "木柵路三段民宅",
        "latitude": 24.9990, "longitude": 121.5720,
        "disaster_type": "Fire",
        "description": "二樓民宅冒出濃煙，火勢已延伸至三樓",
        "has_trapped_people": 0, "has_injured_people": 0, "road_blocked": 0,
        "reported_people_count": 0, "need_help": 1,
        "event_time_offset_min": -15,
    },

    # ── 台中市中區：土石流（無 GPS，用行政區格網）───────────────
    {
        "city": "台中市", "district": "和平區",
        "location_name": None,
        "latitude": None, "longitude": None,   # 無 GPS
        "disaster_type": "Landslide",
        "description": "台 8 線沿線發生土石流，疑似封路",
        "has_trapped_people": 0, "has_injured_people": 0, "road_blocked": 1,
        "reported_people_count": 0, "need_help": 1,
        "event_time_offset_min": -200,
    },
]


def _build_report(raw: dict, now: datetime) -> dict:
    """將 seed 資料格式轉成 reports 表需要的完整 dict。"""
    offset  = raw.get("event_time_offset_min", 0)
    evt_ts  = (now + timedelta(minutes=offset)).isoformat(timespec="seconds")
    upload  = now.isoformat(timespec="seconds")

    lat = raw.get("latitude")
    lng = raw.get("longitude")
    h3c = latlng_to_h3_cell(lat, lng) if lat and lng else None

    from aggregation.event_matcher import _derive_grid_id
    tmp = {"h3_cell": h3c, "city": raw.get("city"), "district": raw.get("district")}
    grid_id, grid_type = _derive_grid_id(tmp)

    base = {
        "has_injured_people":    int(raw.get("has_injured_people", 0)),
        "has_trapped_people":    int(raw.get("has_trapped_people", 0)),
        "road_blocked":          int(raw.get("road_blocked", 0)),
        "need_help":             int(raw.get("need_help", 0)),
        "reported_people_count": int(raw.get("reported_people_count", 0)),
        "disaster_type":         raw["disaster_type"],
        "clip_confidence":       0.85,
    }
    sev_score, sev_level = calc_report_severity(base)

    return {
        "event_id":                  None,
        "image_path":                None,
        "description":               raw.get("description"),
        "location_name":             raw.get("location_name"),
        "city":                      raw.get("city"),
        "district":                  raw.get("district"),
        "latitude":                  lat,
        "longitude":                 lng,
        "location_source":           "gps" if lat else "manual",
        "h3_cell":                   h3c,
        "h3_resolution":             DEFAULT_RESOLUTION if h3c else None,
        "grid_id":                   grid_id,
        "grid_type":                 grid_type,
        "event_time":                evt_ts,
        "upload_time":               upload,
        "clip_model_version":        "clip-vitb32-v1",
        "clip_prompt_version":       "B-complete-sentence-v1",
        "clip_disaster_type":        raw["disaster_type"],
        "clip_confidence":           0.85,
        "clip_top3":                 json.dumps([
                                         {"class": raw["disaster_type"], "class_zh": raw["disaster_type"], "score": 0.85}
                                     ], ensure_ascii=False),
        "top3_predictions":          "[]",
        "resnet_model_version":      None,
        "resnet_disaster_type":      None,
        "resnet_confidence":         None,
        "disaster_type":             raw["disaster_type"],
        "model_agreement":           1,
        "need_review":               0,
        "need_help":                 int(raw.get("need_help", 0)),
        "reported_people_count":     int(raw.get("reported_people_count", 0)),
        "has_trapped_people":        int(raw.get("has_trapped_people", 0)),
        "has_injured_people":        int(raw.get("has_injured_people", 0)),
        "road_blocked":              int(raw.get("road_blocked", 0)),
        "report_severity_score":     sev_score,
        "report_severity_level":     sev_level,
        "rag_version":               None,
        "rag_advice":                "[]",
        "rag_sources":               "[]",
        "model_run_id":              None,
        "aggregation_rule_version":  "h3-district-city-fallback-v2",
        "priority_rule_version":     "severity-weighted-v1",
        # Safety Guard 預設值（seed 資料視為已審核安全）
        "input_safety_label":        "safe",
        "output_safety_label":       "safe",
        "safety_reason":             None,
        # 提交者
        "submitted_by":              "seed",
        # 額外狀態欄位
        "power_outage":              int(raw.get("power_outage", 0)),
    }


def reset_data():
    """清空 reports / events / grid_summary（保留 model_runs / admin_corrections）。"""
    with get_conn() as conn:
        conn.execute("DELETE FROM grid_summary")
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM reports")
        conn.execute("DELETE FROM h3_grid_summary")
        # 重置自動遞增序號
        for t in ("reports", "events"):
            conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")
    print("✅ 已清空 reports / events / grid_summary")


def seed():
    from db.queries import insert_report
    now = datetime.now()
    inserted = 0
    for raw in SEED_REPORTS:
        report = _build_report(raw, now)
        report_id = insert_report(report)
        aggregate(report, report_id)
        inserted += 1
        loc = f"{raw.get('city','')}{raw.get('district','')} {raw.get('location_name') or '（無地點名稱）'}"
        print(f"  ✅ #{report_id:02d}  {raw['disaster_type']:30s}  {loc}")
    print(f"\n共寫入 {inserted} 筆測試回報")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="先清空資料再寫入")
    args = parser.parse_args()

    init_db()

    if args.reset:
        reset_data()

    print(f"\n寫入 {len(SEED_REPORTS)} 筆測試資料...\n")
    seed()
    print("\n完成！執行 streamlit run app.py 即可看到測試資料。")
