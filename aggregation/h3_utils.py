"""H3 網格轉換工具。"""
import h3

DEFAULT_RESOLUTION = 9   # 街區級，約 174m 邊長

# 各解析度說明（邊長 / 適用視角）
RESOLUTION_META = {
    5: {"label": "縣市層級",   "edge_km": 86.7,  "zoom": 7},
    6: {"label": "區域層級",   "edge_km": 32.7,  "zoom": 9},
    7: {"label": "行政區層級", "edge_km": 12.3,  "zoom": 10},
    8: {"label": "社區層級",   "edge_km": 4.6,   "zoom": 12},
    9: {"label": "街區層級",   "edge_km": 1.7,   "zoom": 13},
}


def latlng_to_h3_cell(lat: float, lng: float, resolution: int = DEFAULT_RESOLUTION) -> str:
    """
    將 GPS 座標轉成 H3 cell id。

    H3 resolution 9：邊長約 174m，面積約 0.1km²，適合街區聚合。
    H3 resolution 8：邊長約 461m，面積約 0.7km²，適合行政區聚合。
    """
    return h3.latlng_to_cell(lat, lng, resolution)


def h3_cell_to_latlng(cell: str) -> tuple[float, float]:
    """H3 cell → 中心點座標 (lat, lng)。"""
    return h3.cell_to_latlng(cell)


def are_neighbors(cell_a: str, cell_b: str) -> bool:
    """判斷兩個 H3 cell 是否相鄰（含自身）。"""
    if cell_a == cell_b:
        return True
    return cell_b in h3.grid_disk(cell_a, 1)


def get_neighbor_cells(cell: str, k: int = 1) -> set[str]:
    """取得距離 k 以內的所有鄰近 H3 cells（含自身）。"""
    return set(h3.grid_disk(cell, k))


def cell_boundary(cell: str) -> list[tuple[float, float]]:
    """取得 H3 cell 的六邊形邊界座標（用於地圖繪製）。"""
    return h3.cell_to_boundary(cell)


def cell_to_parent(cell: str, target_resolution: int) -> str:
    """將高解析度 cell 縮放到低解析度父格網。"""
    return h3.cell_to_parent(cell, target_resolution)


def get_resolution(cell: str) -> int:
    """取得 H3 cell 的解析度。"""
    return h3.get_resolution(cell)
