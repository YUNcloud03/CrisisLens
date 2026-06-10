"""事件聚合：H3 優先，fallback 到 city+district。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from collections import Counter

from db.queries import (
    get_candidate_events, insert_event,
    get_reports_by_event, update_event_summary, update_report_event,
    get_reports_by_h3_cell, upsert_h3_summary,
    get_reports_by_grid, upsert_grid_summary, get_all_events,
)
from aggregation.distance import haversine_meters
from aggregation.h3_utils import (
    latlng_to_h3_cell, h3_cell_to_latlng,
    are_neighbors, DEFAULT_RESOLUTION
)
from aggregation.scoring import (
    calc_severity_score, calc_vulnerability_score, calc_credibility_score,
    calc_priority_score, calc_credibility, _severity_level, _priority_level
)
from utils.versions import AGGREGATION_RULE_VERSION, PRIORITY_RULE_VERSION

GEO_THRESHOLD_M = 300

# ── 各災害群組的時間窗口（小時）───────────────────────────────
# 新回報的 event_time 距離既有事件的 latest_report_time 超過窗口 → 不合併
TIME_WINDOWS: dict[str, float] = {
    "weather_water": 48.0,   # 颱風 / 洪水：同一颱風可能持續 2 天
    "earth_land":    12.0,   # 地震 / 土石流：主震 + 餘震期
    "fire":           4.0,   # 火災：同一場火通常在 4 小時內持續回報
    "other":          6.0,   # 其他：保守值
}

DISASTER_GROUPS = {
    "weather_water": {
        "Flood", "Water Disaster", "Typhoon or Storm Damage",
    },
    "earth_land": {
        "Earthquake Damage", "Damaged Infrastructure", "Landslide", "Land Disaster",
    },
    "fire": {
        "Fire", "Fire Disaster",
    },
    "other": {
        "Other or No Disaster", "Non Damage",
    },
}


def disaster_group(disaster_type: str) -> str:
    """Return the aggregation group for a model disaster label."""
    for group, labels in DISASTER_GROUPS.items():
        if disaster_type in labels:
            return group
    return disaster_type or "other"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_dt(s: str | None) -> datetime | None:
    """
    容錯時間字串解析。
    支援格式：
        2026-05-25T14:30:00   (ISO)
        2026-05-25 14:30:00
        2026-05-25 14:30
        2026-5-26 12:30       (月/日缺前置零)
        2026-06-08T00:05
    回傳 None 表示無法解析。
    """
    if not s:
        return None
    # 統一空白/T 分隔，補前置零
    s = s.strip().replace("T", " ")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%-m-%-d %H:%M:%S",   # Linux only
        "%Y-%-m-%-d %H:%M",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    # 最後手段：用 fromisoformat（Python 3.11+ 容錯較佳）
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _within_time_window(report: dict, event: dict) -> bool:
    """
    回傳 True 表示「新回報在時間窗口內，可合併進此事件」。

    比較：report.event_time  vs  event.latest_report_time
    窗口由 disaster_group 決定（見 TIME_WINDOWS）。

    任一時間無法解析 → 保守回傳 True（不因此阻止合併）。
    """
    group  = disaster_group(report.get("disaster_type", ""))
    window = TIME_WINDOWS.get(group, 6.0)

    report_dt = _parse_dt(report.get("event_time") or report.get("upload_time"))
    event_dt  = _parse_dt(event.get("latest_report_time"))

    if report_dt is None or event_dt is None:
        return True   # 時間資料不足，保守允許合併

    diff_hours = abs((report_dt - event_dt).total_seconds()) / 3600
    return diff_hours <= window


# ── Grid Summary 重新計算（h3 / district / city 三種） ────────
def _derive_grid_id(report: dict) -> tuple[str | None, str | None]:
    """
    回傳 (grid_id, grid_type)。
    優先順序：H3 → district → city
    """
    if report.get("h3_cell"):
        return report["h3_cell"], "h3"
    city     = report.get("city")
    district = report.get("district")
    if city and district:
        return f"{city}_{district}", "district"
    if city:
        return city, "city"
    return None, None


def _refresh_grid_summary(grid_id: str, grid_type: str,
                           city: str = None, district: str = None):
    """重算並 upsert grid_summary，支援三種 grid_type。"""
    reports = get_reports_by_grid(grid_id, grid_type)
    if not reports:
        return

    from collections import Counter as _Counter
    types = [r.get("disaster_type") for r in reports if r.get("disaster_type")]
    main_type = _Counter(types).most_common(1)[0][0] if types else None

    max_pri_score = 0
    max_sev_score = 0
    max_ppl       = 0
    need_rev_cnt  = 0
    event_ids     = set()
    latest_time   = ""

    for r in reports:
        max_sev_score = max(max_sev_score, r.get("report_severity_score", 0) or 0)
        max_ppl       = max(max_ppl,       r.get("reported_people_count",  0) or 0)
        need_rev_cnt += int(bool(r.get("need_review")))
        if r.get("event_id"):
            event_ids.add(r["event_id"])
        t = r.get("upload_time") or ""
        if t > latest_time:
            latest_time = t

    from db.queries import get_event
    for eid in event_ids:
        ev = get_event(eid)
        if ev:
            max_pri_score = max(max_pri_score, ev.get("event_priority_score", 0) or 0)

    # 中心座標：H3 用格網中心，district/city 填 None
    center_lat = center_lng = None
    h3_res     = None
    if grid_type == "h3":
        center_lat, center_lng = h3_cell_to_latlng(grid_id)
        h3_res = DEFAULT_RESOLUTION

    upsert_grid_summary({
        "grid_id":                    grid_id,
        "grid_type":                  grid_type,
        "h3_resolution":              h3_res,
        "city":                       city,
        "district":                   district,
        "report_count":               len(reports),
        "event_count":                len(event_ids),
        "image_count":                len(reports),
        "main_disaster_type":         main_type,
        "max_priority_score":         max_pri_score,
        "max_priority_level":         _priority_level(max_pri_score),
        "max_report_severity_score":  max_sev_score,
        "estimated_people_need_help": max_ppl,
        "need_review_count":          need_rev_cnt,
        "latest_report_time":         latest_time,
        "center_lat":                 center_lat,
        "center_lng":                 center_lng,
        "updated_at":                 _now(),
    })


# ── H3 grid summary 重新計算（舊版，向下相容） ────────────────
def _refresh_h3_summary(h3_cell: str):
    """重算並 upsert 某個 H3 cell 的統計。"""
    reports = get_reports_by_h3_cell(h3_cell)
    if not reports:
        return

    # main_disaster_type：最多的那個
    types = [r.get("disaster_type") for r in reports if r.get("disaster_type")]
    main_type = Counter(types).most_common(1)[0][0] if types else None

    max_pri_score = 0
    max_sev_score = 0
    max_ppl       = 0
    event_ids     = set()
    latest_time   = ""

    for r in reports:
        max_sev_score = max(max_sev_score, r.get("report_severity_score", 0) or 0)
        max_ppl       = max(max_ppl,       r.get("reported_people_count",  0) or 0)
        if r.get("event_id"):
            event_ids.add(r["event_id"])
        t = r.get("upload_time") or ""
        if t > latest_time:
            latest_time = t

    # 取各事件最高優先級分數
    from db.queries import get_event
    for eid in event_ids:
        ev = get_event(eid)
        if ev:
            max_pri_score = max(max_pri_score, ev.get("event_priority_score", 0) or 0)

    center = h3_cell_to_latlng(h3_cell)

    upsert_h3_summary({
        "h3_cell":                    h3_cell,
        "h3_resolution":              DEFAULT_RESOLUTION,
        "report_count":               len(reports),
        "event_count":                len(event_ids),
        "image_count":                len(reports),
        "main_disaster_type":         main_type,
        "max_priority_score":         max_pri_score,
        "max_priority_level":         _priority_level(max_pri_score),
        "max_report_severity_score":  max_sev_score,
        "estimated_people_need_help": max_ppl,
        "latest_report_time":         latest_time,
        "center_lat":                 center[0],
        "center_lng":                 center[1],
        "updated_at":                 _now(),
    })


# ── 事件配對 ─────────────────────────────────────────────────
def find_matching_event(report: dict) -> int | None:
    """
    v2 聚合：災害群組 + 地理鄰近 + 時間窗口 三重判斷。

    通過條件（三者同時滿足）：
      1. 同一災害群組（Typhoon+Flood / Earthquake+Landslide / Fire / Other）
      2. 地理鄰近（H3 鄰格 > GPS 300m > 同行政區，三擇一）
      3. 新回報的 event_time 距既有事件的 latest_report_time ≤ 群組時間窗口
    """
    report_group = disaster_group(report.get("disaster_type", ""))

    # 只考慮非終止狀態的事件（resolved / archived 不再接受新回報）
    candidates = [
        ev for ev in get_all_events()
        if disaster_group(ev.get("disaster_type", "")) == report_group
        and ev.get("status") not in ("resolved", "archived", "closed")
    ]

    # ── 1. H3 優先：同 cell 或鄰接 cell ─────────────────────
    if report.get("h3_cell"):
        for ev in candidates:
            if ev.get("h3_cell") and are_neighbors(report["h3_cell"], ev["h3_cell"]):
                if _within_time_window(report, ev):
                    return ev["event_id"]

    # ── 2. GPS 距離（無 H3 但有座標）──────────────────────
    if report.get("latitude") and report.get("longitude"):
        for ev in candidates:
            if ev.get("latitude") and ev.get("longitude"):
                dist = haversine_meters(
                    report["latitude"], report["longitude"],
                    ev["latitude"],    ev["longitude"],
                )
                if dist <= GEO_THRESHOLD_M and _within_time_window(report, ev):
                    return ev["event_id"]

    # ── 3. Fallback：city + district ──────────────────────
    for ev in candidates:
        if (report.get("city")     and report["city"]     == ev.get("city") and
                report.get("district") and report["district"] == ev.get("district")):
            if _within_time_window(report, ev):
                return ev["event_id"]

    return None


# ── 英文災害類型 → 中文簡稱對照 ─────────────────────────────
_TYPE_ZH: dict[str, str] = {
    "Earthquake Damage":       "地震",
    "Damaged Infrastructure":  "建物損壞",
    "Flood":                   "淹水",
    "Water Disaster":          "淹水",
    "Fire":                    "火災",
    "Fire Disaster":           "火災",
    "Typhoon or Storm Damage": "颱風",
    "Landslide":               "土石流",
    "Land Disaster":           "土石流",
    "Other or No Disaster":    "其他災情",
    "Non Damage":              "其他災情",
}


def _disaster_zh(disaster_type: str) -> str:
    """回傳災害類型中文簡稱，未知類型保留原字串。"""
    return _TYPE_ZH.get(disaster_type, disaster_type or "災情")


def _build_event_name(report: dict) -> str:
    """
    格式：{日期} {縣市}{行政區}{災害中文}事件
    範例：
      2026-06-08 台北市信義區颱風事件
      2025-09-21 花蓮縣秀林鄉地震事件
      2026-06-08 地震事件            ← 無 GPS / 地址時
    """
    # 日期（取 event_time 或 upload_time 的前 10 碼）
    raw_time = report.get("event_time") or report.get("upload_time") or ""
    date_str = raw_time[:10].replace("T", " ").strip() if raw_time else ""

    # 地點（city + district，避免重複）
    city     = (report.get("city")     or "").strip()
    district = (report.get("district") or "").strip()
    location = city + district          # e.g. "台北市信義區"

    # 災害類型中文
    dtype_zh = _disaster_zh(report.get("disaster_type", ""))

    parts = []
    if date_str:
        parts.append(date_str)
    if location:
        parts.append(location)
    parts.append(dtype_zh + "事件")

    return " ".join(parts)   # "2026-06-08 台北市信義區颱風事件"


# ── 主入口 ────────────────────────────────────────────────────
def aggregate(report: dict, report_id: int) -> dict:
    now        = _now()
    event_time = report.get("event_time") or report.get("upload_time") or now
    matched_id = find_matching_event(report)

    # 計算 grid_id / grid_type（所有 report 都要有格網）
    grid_id, grid_type = _derive_grid_id(report)

    if matched_id is None:
        # 建立新事件
        sev_score = report.get("report_severity_score", 0) or 0
        sev_level = report.get("report_severity_level", "Low")
        ppl       = report.get("reported_people_count", 0) or 0

        # 三層評分
        vuln_score = calc_vulnerability_score(
            report.get("city") or "", report.get("district")
        )
        temp_event = {"status": "pending_review"}
        cred_score, cred_level = calc_credibility_score(temp_event, [report])
        pri_score, pri_level   = calc_priority_score(sev_score, vuln_score, cred_score)

        event_data = {
            "event_name":                _build_event_name(report),
            "location_name":             report.get("location_name"),
            "city":                      report.get("city"),
            "district":                  report.get("district"),
            "latitude":                  report.get("latitude"),
            "longitude":                 report.get("longitude"),
            "location_source":           report.get("location_source"),
            "h3_cell":                   report.get("h3_cell"),
            "h3_resolution":             report.get("h3_resolution", DEFAULT_RESOLUTION),
            "grid_id":                   grid_id,
            "grid_type":                 grid_type,
            "disaster_type":             report.get("disaster_type"),
            "first_report_time":         event_time,
            "latest_report_time":        event_time,
            "report_count":              1,
            "image_count":               1,
            "max_report_severity_score": sev_score,
            "max_report_severity_level": sev_level,
            "estimated_people_need_help":ppl,
            "has_trapped_people":        int(bool(report.get("has_trapped_people"))),
            "has_injured_people":        int(bool(report.get("has_injured_people"))),
            "road_blocked":              int(bool(report.get("road_blocked"))),
            "power_outage":              int(bool(report.get("power_outage"))),
            "vulnerability_score":       vuln_score,
            "credibility_score":         cred_score,
            "credibility_level":         cred_level,
            "event_priority_score":      pri_score,
            "event_priority_level":      pri_level,
            "aggregation_rule_version":  AGGREGATION_RULE_VERSION,
            "priority_rule_version":     PRIORITY_RULE_VERSION,
            "status":                    "pending_review",
            "created_at":                now,
            "updated_at":                now,
        }
        event_id = insert_event(event_data)
        update_report_event(report_id, event_id)
        is_new = True
    else:
        event_id = matched_id
        update_report_event(report_id, event_id)
        _refresh_event(event_id, event_time)
        is_new = False

    # 更新 grid_summary（所有 grid_type 都更新）
    if grid_id and grid_type:
        _refresh_grid_summary(
            grid_id, grid_type,
            city=report.get("city"),
            district=report.get("district"),
        )
    # 向下相容：也更新舊版 h3_grid_summary
    if report.get("h3_cell"):
        _refresh_h3_summary(report["h3_cell"])

    from db.queries import get_event
    ev = get_event(event_id)
    return {
        "event_id":            event_id,
        "is_new":              is_new,
        "event_priority_score":ev["event_priority_score"],
        "event_priority_level":ev["event_priority_level"],
        "h3_cell":             report.get("h3_cell"),
    }


def _initial_priority(report: dict) -> tuple[int, str]:
    sev   = report.get("report_severity_score", 0)
    score = int(sev * 0.6)
    if report.get("has_trapped_people"): score += 20
    if report.get("has_injured_people"): score += 20
    if report.get("road_blocked"):       score += 10
    ppl = report.get("reported_people_count", 0) or 0
    if ppl >= 6:   score += 20
    elif ppl >= 1: score += 10
    return min(score, 100), _priority_level(min(score, 100))


def _refresh_event(event_id: int, latest_time: str):
    from db.queries import get_event
    reports = get_reports_by_event(event_id)
    event   = get_event(event_id)
    if not event:
        return

    max_sev  = max((r.get("report_severity_score", 0) or 0) for r in reports)
    max_ppl  = max((r.get("reported_people_count",  0) or 0) for r in reports)
    trapped  = int(any(r.get("has_trapped_people") for r in reports))
    injured  = int(any(r.get("has_injured_people") for r in reports))
    blocked  = int(any(r.get("road_blocked")        for r in reports))
    outage   = int(any(r.get("power_outage")        for r in reports))

    # 三層評分
    vuln_score = calc_vulnerability_score(
        event.get("city") or "", event.get("district")
    )
    cred_score, cred_level = calc_credibility_score(event, reports)
    pri_score, pri_level   = calc_priority_score(max_sev, vuln_score, cred_score)

    update_event_summary(event_id, {
        "report_count":               len(reports),
        "image_count":                len(reports),
        "latest_report_time":         latest_time,
        "max_report_severity_score":  max_sev,
        "max_report_severity_level":  _severity_level(max_sev),
        "estimated_people_need_help": max_ppl,
        "has_trapped_people":         trapped,
        "has_injured_people":         injured,
        "road_blocked":               blocked,
        "power_outage":               outage,
        "vulnerability_score":        vuln_score,
        "credibility_score":          cred_score,
        "credibility_level":          cred_level,
        "event_priority_score":       pri_score,
        "event_priority_level":       pri_level,
        "updated_at":                 _now(),
    })
