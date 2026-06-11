"""台灣鄉鎮區脆弱度資料載入與查詢。

從 data/township_features_merged.csv 讀取，提供兩層查詢：
  1. 鄉鎮精度  (county + township)
  2. 縣市精度  (county 平均值，fallback)
"""
import os
import csv
from typing import Optional

_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "township_features_merged.csv")

# ── 資料載入 ──────────────────────────────────────────────────

def _norm(s: str) -> str:
    """臺 → 台，統一縣市名稱寫法。"""
    return s.replace("臺", "台") if s else s


_TOWNSHIP: dict[tuple[str, str], dict] = {}
_county_acc: dict[str, dict] = {}
_county_cnt: dict[str, int] = {}

try:
    with open(_CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            county   = _norm(row["county"])
            township = row["township"]
            data = {
                "population_density": float(row["population_density"]),
                "old_age_ratio":      float(row["old_age_ratio"]) / 100.0,  # % → 小數
                "aging_index":        float(row["aging_index"]),
                "beds_per_1000":      float(row["beds_per_1000"]),
                "mountain_area":      bool(int(row["is_mountain"])),
                "coastal_area":       bool(int(row["coastal_area"])),
            }
            _TOWNSHIP[(county, township)] = data

            if county not in _county_acc:
                _county_acc[county] = {
                    "population_density": 0.0, "old_age_ratio": 0.0,
                    "aging_index": 0.0, "beds_per_1000": 0.0,
                    "_mtn": 0, "_coast": 0,
                }
                _county_cnt[county] = 0

            acc = _county_acc[county]
            acc["population_density"] += data["population_density"]
            acc["old_age_ratio"]      += data["old_age_ratio"]
            acc["aging_index"]        += data["aging_index"]
            acc["beds_per_1000"]      += data["beds_per_1000"]
            acc["_mtn"]   += int(data["mountain_area"])
            acc["_coast"] += int(data["coastal_area"])
            _county_cnt[county] += 1
except FileNotFoundError:
    pass  # CSV 不存在時靜默，使用 DEFAULT_VULNERABILITY

COUNTY_VULNERABILITY: dict[str, dict] = {}
for county, acc in _county_acc.items():
    n = _county_cnt[county]
    COUNTY_VULNERABILITY[county] = {
        "population_density": acc["population_density"] / n,
        "old_age_ratio":      acc["old_age_ratio"]      / n,
        "aging_index":        acc["aging_index"]        / n,
        "beds_per_1000":      acc["beds_per_1000"]      / n,
        "mountain_area":      (acc["_mtn"]   / n) >= 0.25,
        "coastal_area":       (acc["_coast"] / n) >= 0.25,
    }

DEFAULT_VULNERABILITY: dict = {
    "population_density": 1000.0,
    "old_age_ratio":      0.20,
    "aging_index":        200.0,
    "beds_per_1000":      5.0,
    "mountain_area":      False,
    "coastal_area":       False,
}


# ── 查詢函式 ──────────────────────────────────────────────────

def lookup_vulnerability(city: str, district: Optional[str] = None) -> dict:
    """回傳脆弱度資料。優先鄉鎮精度，無則縣市平均，最後 fallback 預設值。"""
    city_n = _norm(city) if city else ""
    if district:
        data = _TOWNSHIP.get((city_n, district))
        if data:
            return data
    if city_n:
        data = COUNTY_VULNERABILITY.get(city_n)
        if data:
            return data
    return DEFAULT_VULNERABILITY
