"""三層評分 + Priority 加權合成。v2

Severity Score    (0-100) — 現場災情嚴重度
Vulnerability Score (0-100) — 地區承受能力
Credibility Score  (0-100) — 資料可信度
Priority Score     (0-100) = 0.50×S + 0.30×V + 0.20×C
"""
from typing import Optional
from aggregation.region_data import lookup_vulnerability

_HIGH_RISK = {
    "Fire", "Fire Disaster",
    "Earthquake Damage", "Damaged Infrastructure",
    "Landslide", "Land Disaster",
    "Typhoon or Storm Damage",
}


# ════════════════════════════════════════════════════════════
# 1. Severity Score
# ════════════════════════════════════════════════════════════

def calc_severity_score(report: dict) -> tuple[int, str]:
    """
    災情嚴重度（0-100）。

    來源：CLIP 圖片判斷 + 使用者勾選項目。
    """
    score = 0

    # 圖片災害嚴重度 (max 25)
    disaster_type = report.get("disaster_type", "")
    conf = report.get("clip_confidence", 0) or 0
    if disaster_type in _HIGH_RISK:
        if conf >= 0.80:   score += 25
        elif conf >= 0.60: score += 18
        else:              score += 10
    else:
        score += 5

    # 現場狀況
    if report.get("has_trapped_people"):  score += 25  # 受困
    if report.get("has_injured_people"):  score += 20  # 醫療需求
    if report.get("road_blocked"):        score += 15  # 道路中斷
    if report.get("power_outage"):        score += 10  # 停電
    if report.get("need_help"):           score += 5   # 需要協助

    # 人數（max 15）
    count = report.get("reported_people_count", 0) or 0
    if count >= 10:   score += 15
    elif count >= 6:  score += 10
    elif count >= 1:  score += 5

    score = min(score, 100)
    return score, _severity_level(score)


# ════════════════════════════════════════════════════════════
# 2. Vulnerability Score
# ════════════════════════════════════════════════════════════

def calc_vulnerability_score(city: str, district: Optional[str] = None) -> int:
    """
    地區脆弱度（0-100）。

    資料來源：township_features_merged.csv
      population_density, old_age_ratio, beds_per_1000,
      mountain_area, coastal_area
    優先使用鄉鎮精度，fallback 縣市平均。
    """
    info = lookup_vulnerability(city, district)
    score = 0

    # 人口密度 (max 25) — 密度越高受影響人數越多
    pd = info["population_density"]
    if pd >= 15000:   score += 25
    elif pd >= 5000:  score += 20
    elif pd >= 1000:  score += 15
    elif pd >= 200:   score += 10
    else:             score += 5

    # 高齡比例 (max 25) — 老年人口越多需求越大
    oar = info["old_age_ratio"]  # 已是小數（0~1）
    if oar >= 0.40:   score += 25
    elif oar >= 0.30: score += 18
    elif oar >= 0.20: score += 12
    else:             score += 6

    # 醫療壓力 (max 30) — 床位越少應急能力越弱
    bpk = info["beds_per_1000"]
    if bpk < 1.0:    score += 30
    elif bpk < 3.0:  score += 22
    elif bpk < 7.0:  score += 14
    else:            score += 6

    # 地形風險
    if info["mountain_area"]:  score += 15   # 山區：道路中斷、救援困難
    if info["coastal_area"]:   score += 10   # 沿海：海嘯、風暴潮

    return min(score, 100)


# ════════════════════════════════════════════════════════════
# 3. Credibility Score
# ════════════════════════════════════════════════════════════

def calc_credibility_score(event: dict, reports: list[dict]) -> tuple[int, str]:
    """
    資料可信度（0-100）。

    加權公式：
      40% — AI 分類信心度（CLIP confidence）
      30% — 使用者輸入與 AI 結果是否一致（model_agreement + need_review）
      20% — 附近相同災情回報數
      10% — 地理合理性（災害類型與地形的匹配度）

    管理員確認 → 直接給 95。
    """
    if event.get("status") in {"active", "verified"}:   # verified = 舊名稱，向下相容
        return 95, "Verified"

    if not reports:
        return 0, "Low"

    # 取信心度最高的回報作為代表
    best = max(reports, key=lambda r: r.get("clip_confidence") or 0)

    # ── 1. AI 分類信心度 (40%) ─────────────────────────────
    ai_conf = best.get("clip_confidence") or 0
    ai_score = ai_conf * 100  # 0–100

    # ── 2. 使用者輸入與 AI 結果一致性 (30%) ────────────────
    # model_agreement: CLIP vs ResNet 是否一致
    # need_review: 信心不足 / 模型矛盾 / gap 太小
    if best.get("model_agreement") == 1 and not best.get("need_review"):
        consistency_score = 100   # 完全一致
    elif best.get("model_agreement") == 1:
        consistency_score = 60    # 模型一致但有其他警示
    elif not best.get("need_review"):
        consistency_score = 40    # 模型不一致但無明顯矛盾
    else:
        consistency_score = 15    # 模型不一致且有矛盾警示

    # ── 3. 附近相同災情回報數 (20%) ────────────────────────
    dtype = event.get("disaster_type") or best.get("disaster_type") or ""
    same_type = sum(1 for r in reports if r.get("disaster_type") == dtype)
    if same_type >= 5:    count_score = 100
    elif same_type >= 3:  count_score = 75
    elif same_type >= 2:  count_score = 50
    else:                 count_score = 20   # 僅單筆

    # ── 4. 地理合理性 (10%) ─────────────────────────────────
    geo_score = _geo_plausibility(dtype, event.get("city") or "", event.get("district"))

    # ── 加權合成 ────────────────────────────────────────────
    score = int(round(
        0.40 * ai_score +
        0.30 * consistency_score +
        0.20 * count_score +
        0.10 * geo_score
    ))
    score = max(0, min(score, 100))
    return score, _credibility_level(score)


# 災害類型 × 地形 合理性對照表
_GEO_RULES: dict[str, dict] = {
    "Landslide":              {"mountain": 100, "coastal": 50,  "other": 30},
    "Land Disaster":          {"mountain": 100, "coastal": 50,  "other": 30},
    "Typhoon or Storm Damage":{"mountain": 60,  "coastal": 95,  "other": 50},
    "Water Disaster":         {"mountain": 50,  "coastal": 85,  "other": 55},
    "Earthquake Damage":      {"mountain": 75,  "coastal": 75,  "other": 70},
    "Fire":                   {"mountain": 70,  "coastal": 65,  "other": 70},
    "Fire Disaster":          {"mountain": 70,  "coastal": 65,  "other": 70},
    "Damaged Infrastructure": {"mountain": 70,  "coastal": 70,  "other": 70},
    "Non Damage":             {"mountain": 65,  "coastal": 65,  "other": 65},
}
_GEO_DEFAULT = {"mountain": 65, "coastal": 65, "other": 60}


def _geo_plausibility(disaster_type: str, city: str, district: Optional[str]) -> int:
    """災害類型與地形特徵的匹配度 (0-100)。"""
    geo = lookup_vulnerability(city, district)
    rule = _GEO_RULES.get(disaster_type, _GEO_DEFAULT)
    if geo.get("mountain_area"):  return rule["mountain"]
    if geo.get("coastal_area"):   return rule["coastal"]
    return rule["other"]


# ════════════════════════════════════════════════════════════
# 4. Priority Score
# ════════════════════════════════════════════════════════════

def calc_priority_score(severity: int, vulnerability: int, credibility: int) -> tuple[int, str]:
    """Priority = 0.50 × S + 0.30 × V + 0.20 × C"""
    score = int(round(0.50 * severity + 0.30 * vulnerability + 0.20 * credibility))
    score = min(score, 100)
    return score, _priority_level(score)


# ════════════════════════════════════════════════════════════
# Level helpers
# ════════════════════════════════════════════════════════════

def _severity_level(score: int) -> str:
    if score >= 70: return "High"
    if score >= 40: return "Medium"
    return "Low"

def _priority_level(score: int) -> str:
    if score >= 70: return "High"
    if score >= 40: return "Medium"
    return "Low"

def _credibility_level(score: int) -> str:
    if score >= 70: return "High"
    if score >= 40: return "Medium"
    return "Low"


# ════════════════════════════════════════════════════════════
# Backward compatibility（舊介面保留，內部呼叫新函式）
# ════════════════════════════════════════════════════════════

def calc_report_severity(report: dict) -> tuple[int, str]:
    return calc_severity_score(report)

def calc_event_priority(event: dict, reports: list[dict]) -> tuple[int, str]:
    sev  = event.get("max_report_severity_score", 0) or 0
    vuln = calc_vulnerability_score(event.get("city") or "", event.get("district"))
    cred, _ = calc_credibility_score(event, reports)
    return calc_priority_score(sev, vuln, cred)

def calc_credibility(report_count: int, status: str = "pending_review") -> str:
    if status in {"active", "verified"}: return "Verified"   # verified = 舊名稱，向下相容
    if report_count >= 5:    return "High"
    if report_count >= 2:    return "Medium"
    return "Low"
