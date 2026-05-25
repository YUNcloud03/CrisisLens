"""Haversine 距離計算。"""
import math


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    計算兩個 GPS 座標之間的直線距離（公尺）。
    使用 Haversine 公式，適合短距離計算。
    """
    R = 6_371_000  # 地球半徑（公尺）

    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)

    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
