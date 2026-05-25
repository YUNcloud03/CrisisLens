"""Report 嚴重度 & Event 優先級計算。"""

# 高風險災害類型（英文，對應 CLIP 輸出）
_HIGH_RISK = {
    "Fire", "Fire Disaster",
    "Earthquake Damage", "Damaged Infrastructure",
    "Landslide", "Land Disaster",
    "Typhoon or Storm Damage",
}


def calc_report_severity(report: dict) -> tuple[int, str]:
    """
    計算單筆 report 嚴重度。

    Parameters
    ----------
    report : dict，需包含以下 key：
        has_injured_people, has_trapped_people, road_blocked,
        need_help, reported_people_count,
        disaster_type, clip_confidence

    Returns
    -------
    (score: int 0–100, level: str "High" / "Medium" / "Low")
    """
    score = 0

    if report.get("has_injured_people"):  score += 30
    if report.get("has_trapped_people"):  score += 30
    if report.get("road_blocked"):        score += 20
    if report.get("need_help"):           score += 10

    count = report.get("reported_people_count", 0) or 0
    if count >= 6:   score += 20
    elif count >= 1: score += 10

    if report.get("disaster_type") in _HIGH_RISK:
        score += 15

    conf = report.get("clip_confidence") or 0
    if conf >= 0.8:
        score += 5

    score = min(score, 100)
    return score, _severity_level(score)


def _severity_level(score: int) -> str:
    if score >= 70: return "High"
    if score >= 40: return "Medium"
    return "Low"


def calc_event_priority(event: dict, reports: list[dict]) -> tuple[int, str]:
    """
    計算事件整體優先級。

    Parameters
    ----------
    event   : events 資料表的一筆資料（dict）
    reports : 該事件底下所有 reports

    Returns
    -------
    (score: int 0–100, level: str "High" / "Medium" / "Low")
    """
    score = 0

    # 最高 report 嚴重度佔 60%
    if reports:
        max_r = max(r.get("report_severity_score", 0) or 0 for r in reports)
        score += int(max_r * 0.6)

    # 回報數量（多人回報 = 可信度高）
    count = event.get("report_count", 1) or 1
    if count >= 5:   score += 15
    elif count >= 2: score += 8

    # 疑似待協助人數
    people = event.get("estimated_people_need_help", 0) or 0
    if people >= 6:   score += 20
    elif people >= 1: score += 10

    if event.get("has_trapped_people"):  score += 20
    if event.get("has_injured_people"):  score += 20
    if event.get("road_blocked"):        score += 10

    score = min(score, 100)
    return score, _priority_level(score)


def _priority_level(score: int) -> str:
    if score >= 70: return "High"
    if score >= 40: return "Medium"
    return "Low"


def calc_credibility(report_count: int, status: str = "pending_review") -> str:
    if status == "verified":    return "Verified"
    if report_count >= 5:       return "High"
    if report_count >= 2:       return "Medium"
    return "Low"
