"""
反向地理編碼工具（Nominatim / OpenStreetMap）。

- 台灣地址中文化：state → 縣市、city_district/suburb → 行政區
- LRU 快取：相同座標（精度 0.001°，≈100m）只打一次 API
- 離線 / 逾時 → 靜默回傳空值，不中斷主流程
"""
import functools
import math
import requests

# Nominatim 使用政策：需填寫 User-Agent，並限 1 req/sec
_USER_AGENT  = "CrisisLens-DisasterAI/1.0 (ntut.org.tw)"
_API_URL     = "https://nominatim.openstreetmap.org/reverse"
_TIMEOUT_SEC = 4


def _grid_key(lat: float, lng: float, precision: int = 3) -> tuple[float, float]:
    """
    將座標量化到指定精度（0.001° ≈ 100m），避免重複 API 請求。
    """
    factor = 10 ** precision
    return (math.floor(lat * factor) / factor,
            math.floor(lng * factor) / factor)


@functools.lru_cache(maxsize=256)
def _cached_geocode(lat_key: float, lng_key: float) -> dict:
    """實際發送 Nominatim 請求（快取版）。"""
    try:
        resp = requests.get(
            _API_URL,
            params={
                "lat":             lat_key,
                "lon":             lng_key,
                "format":          "json",
                "accept-language": "zh-TW",
                "zoom":            14,       # 行政區精度
                "addressdetails":  1,
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        data = resp.json()
        addr = data.get("address", {})

        # 台灣行政區層級：state=縣市、city_district / suburb / town=行政區
        city = (
            addr.get("state")   or
            addr.get("city")    or
            addr.get("county")  or
            ""
        ).strip()

        district = (
            addr.get("city_district") or
            addr.get("suburb")        or
            addr.get("town")          or
            addr.get("village")       or
            addr.get("municipality")  or
            ""
        ).strip()

        # 正規化：Nominatim 用「臺」，系統選單用「台」，統一為「台」
        city     = city.replace("臺", "台")
        district = district.replace("臺", "台")

        display = data.get("display_name", "").split(",")[0].strip()

        return {
            "city":         city,
            "district":     district,
            "display_name": display,
            "raw":          addr,
        }
    except Exception:
        return {"city": "", "district": "", "display_name": "", "raw": {}}


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    反向地理編碼。

    Parameters
    ----------
    lat, lng : float  WGS84 座標

    Returns
    -------
    {
        "city":         "台北市",
        "district":     "信義區",
        "display_name": "信義路五段",   ← 第一個地名片段
        "raw":          {...},           ← Nominatim address dict
    }
    失敗時所有欄位為空字串，不拋出例外。
    """
    if not lat or not lng:
        return {"city": "", "district": "", "display_name": "", "raw": {}}
    key_lat, key_lng = _grid_key(lat, lng)
    return _cached_geocode(key_lat, key_lng)
