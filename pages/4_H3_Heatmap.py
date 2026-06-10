"""Page 4 — Multi-scale H3 Disaster Aggregation Map（動態縮放版）"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from collections import Counter, defaultdict
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
try:
    import h3 as h3lib
except ImportError:
    h3lib = None

from db.database import init_db
from db.queries import get_all_h3_summaries, get_grid_summaries
from utils.auth import require_admin
from utils.ui_theme import apply_theme, page_header, stat_card, top_pill

init_db()  # 含一次性資料遷移（h3_grid_summary → grid_summary、backfill grid_id/grid_type）

# ── 頁面設定 ──────────────────────────────────────────────────
st.set_page_config(page_title="H3 地圖｜CrisisLens", page_icon="🗺️", layout="wide", initial_sidebar_state="expanded")
apply_theme()
require_admin()
if h3lib is None:
    top_pill(3, "管理端 - Dashboard 總覽", "H3 Heatmap")
    page_header(
        "Multi-scale H3 災情聚合地圖",
        "目前環境缺少 h3 套件，無法渲染 H3 熱區圖。請安裝 requirements.txt 後重新啟動。",
        "CrisisLens Rescue",
    )
    st.error("缺少 h3 套件：請執行 `pip install -r requirements.txt`。")
    st.stop()
top_pill(3, "管理端 - Dashboard 總覽", "H3 Heatmap")
page_header(
    "Multi-scale H3 災情聚合地圖",
    "整合多尺度 H3 空間聚合與災情通報，協助救援單位快速辨識高風險區域與資源需求。",
    "CrisisLens Rescue",
    f"<strong>{datetime.now().strftime('%H:%M:%S')}</strong>{datetime.now().strftime('%Y / %m / %d')}",
)

TAIWAN_LAT, TAIWAN_LNG = 23.97, 120.97
MAP_HEIGHT = 680

# ═══════════════════════════════════════════════════════════════
# 資料聚合
# ═══════════════════════════════════════════════════════════════
def _priority_level(score: int) -> str:
    if score >= 70: return "High"
    if score >= 40: return "Medium"
    return "Low"

def _get_cell(row) -> str:
    """
    從 DataFrame row 取出 H3 cell ID。
    grid_summary 資料：cell 存在 grid_id 欄位。
    demo / 舊版資料：cell 存在 h3_cell 欄位。
    """
    return str(row.get("h3_cell") or row.get("grid_id") or "")

def _row_to_js(row) -> dict:
    """轉成前端 JS 需要的精簡欄位。"""
    cell = _get_cell(row)
    return {
        "h3_cell":                    cell,
        "report_count":               int(row.get("report_count", 0) or 0),
        "event_count":                int(row.get("event_count",  0) or 0),
        "max_priority_level":         str(row.get("max_priority_level") or "Low"),
        "max_priority_score":         int(row.get("max_priority_score", 0) or 0),
        "main_disaster_type":         str(row.get("main_disaster_type") or "—"),
        "estimated_people_need_help": int(row.get("estimated_people_need_help", 0) or 0),
        "latest_report_time":         str(row.get("latest_report_time") or ""),
    }


def aggregate_to_res(base_df: pd.DataFrame, target_res: int) -> list:
    """
    將 resolution-9 資料聚合到任意低解析度，回傳 JS-ready list。
    resolution 9 → 直接轉換，不做聚合。
    """
    if base_df.empty:
        return []

    if target_res == 9:
        return [_row_to_js(row) for _, row in base_df.iterrows()]

    bucket: dict[str, dict] = defaultdict(lambda: {
        "report_count": 0, "event_count": 0,
        "max_priority_score": 0, "estimated_people_need_help": 0,
        "latest_report_time": "", "_type_cnt": Counter(),
    })

    for _, row in base_df.iterrows():
        cell = _get_cell(row)
        if not cell:
            continue
        try:
            parent = h3lib.cell_to_parent(cell, target_res)
        except Exception:
            continue
        b = bucket[parent]
        b["report_count"]               += int(row.get("report_count", 0) or 0)
        b["event_count"]                += int(row.get("event_count",  0) or 0)
        b["max_priority_score"]          = max(b["max_priority_score"],
                                               int(row.get("max_priority_score", 0) or 0))
        b["estimated_people_need_help"] += int(row.get("estimated_people_need_help", 0) or 0)
        t = str(row.get("latest_report_time") or "")
        if t > b["latest_report_time"]:
            b["latest_report_time"] = t
        if row.get("main_disaster_type"):
            b["_type_cnt"][row["main_disaster_type"]] += int(row.get("report_count", 1) or 1)

    result = []
    for cell, b in bucket.items():
        score = b["max_priority_score"]
        result.append({
            "h3_cell":                    cell,
            "report_count":               b["report_count"],
            "event_count":                b["event_count"],
            "max_priority_level":         _priority_level(score),
            "max_priority_score":         score,
            "main_disaster_type":         b["_type_cnt"].most_common(1)[0][0]
                                          if b["_type_cnt"] else "—",
            "estimated_people_need_help": b["estimated_people_need_help"],
            "latest_report_time":         b["latest_report_time"],
        })
    return result

# ═══════════════════════════════════════════════════════════════
# HTML 地圖模板（純 deck.gl JS，不依賴 Mapbox token）
# ═══════════════════════════════════════════════════════════════
MAP_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#080d1a; overflow:hidden; }
#dc { width:100%; height:__MAP_HEIGHT__px; position:relative; }

/* 左上：解析度 badge */
#res-badge {
  position:absolute; top:14px; left:14px; z-index:100; pointer-events:none;
  background:rgba(13,22,40,.92); border:1px solid rgba(56,189,248,.45);
  border-radius:8px; padding:8px 14px; color:#38bdf8;
  font-family:monospace; font-size:13px; line-height:1.7;
}
#res-badge span.sub { font-size:11px; color:#94a3b8; }

/* 右上：篩選按鈕列 */
#filter-bar {
  position:absolute; top:14px; right:14px; z-index:100;
  display:flex; gap:6px;
}
.fb {
  padding:6px 14px; border-radius:999px; cursor:pointer;
  font-size:12px; font-weight:700;
  border:2px solid transparent; transition:border-color .15s;
}
.fb.on { border-color:#38bdf8 !important; }

/* 左下：圖例 */
#legend {
  position:absolute; bottom:24px; left:14px; z-index:100; pointer-events:none;
  background:rgba(13,22,40,.85); border:1px solid rgba(30,64,120,.45);
  border-radius:8px; padding:10px 14px; color:#e2e8f0;
  font-size:12px; line-height:1.9;
}
#legend .leg-title { font-size:10px; color:#94a3b8; letter-spacing:.06em; margin-bottom:2px; }
#legend .hint { font-size:10px; color:#475569; margin-top:4px; }
</style>
</head>
<body>
<div id="dc"></div>

<!-- 解析度 badge -->
<div id="res-badge">
  <div id="res-label">Level 1 · Res 5 · 縣市層級</div>
  <span class="sub" id="zoom-label">zoom 7.0</span>
</div>

<!-- 篩選按鈕 -->
<div id="filter-bar">
  <button class="fb on"  id="btn-all"    style="background:#1e3a5f;color:#38bdf8"
          onclick="setFilter('all')">全部</button>
  <button class="fb"     id="btn-High"   style="background:#1a0808;color:#f87171"
          onclick="setFilter('High')">🔴 High</button>
  <button class="fb"     id="btn-Medium" style="background:#1a1208;color:#fbbf24"
          onclick="setFilter('Medium')">🟡 Medium</button>
  <button class="fb"     id="btn-Low"    style="background:#081a0e;color:#4ade80"
          onclick="setFilter('Low')">🟢 Low</button>
</div>

<!-- 圖例 -->
<div id="legend">
  <div class="leg-title">優先級圖例</div>
  <div>🔴 High &nbsp;&nbsp;高風險</div>
  <div>🟡 Medium 中風險</div>
  <div>🟢 Low &nbsp;&nbsp;低風險</div>
  <div class="hint">⬆⬇ 滾輪縮放自動切換解析度</div>
</div>

<!-- h3-js 必須在 deck.gl 之前載入，H3HexagonLayer 的 peer dependency -->
<script src="https://unpkg.com/h3-js@4/dist/h3-js.umd.js"></script>
<!-- deck.gl 全量 CDN -->
<script src="https://unpkg.com/deck.gl@9/dist.min.js"></script>
<script>
// ─── 資料（由 Python 注入）────────────────────────────────────
const DATA = {
  res5 : __DATA_RES5__,
  res7 : __DATA_RES7__,
  res9 : __DATA_RES9__,
};

// ─── 縮放 → 解析度 對應 ──────────────────────────────────────
// zoom < 8   → Res 5  (縣市)
// zoom 8~11  → Res 7  (行政區)
// zoom ≥ 11  → Res 9  (街區)
const SCALE_MAP = [
  { maxZoom:  8, res: 5, label: 'Level 1 · Res 5 · 縣市層級',   cov: 0.70 },
  { maxZoom: 11, res: 7, label: 'Level 2 · Res 7 · 行政區層級', cov: 0.80 },
  { maxZoom: 99, res: 9, label: 'Level 3 · Res 9 · 街區層級',   cov: 0.90 },
];
function scaleFor(zoom) { return SCALE_MAP.find(s => zoom < s.maxZoom); }

// ─── 顏色 ────────────────────────────────────────────────────
function pc(level) {
  return ({ High:[248,113,113,210], Medium:[251,191,36,210], Low:[74,222,128,210] })[level]
         || [148,163,184,150];
}

// ─── 全域狀態 ────────────────────────────────────────────────
let activeFilter = 'all';
let currentRes   = 5;
let inst         = null;

function filtered(res) {
  const d = DATA['res' + res];
  return activeFilter === 'all' ? d : d.filter(x => x.max_priority_level === activeFilter);
}

// ─── 圖層建構 ────────────────────────────────────────────────
function tileLayer() {
  return new deck.TileLayer({
    id: 'tiles',
    data: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    tileSize: 256, minZoom: 0, maxZoom: 19,
    renderSubLayers(props) {
      const { west, south, east, north } = props.tile.bbox;
      return new deck.BitmapLayer(props, {
        data: null, image: props.data,
        bounds: [west, south, east, north],
      });
    },
  });
}

function h3Layer(res) {
  const info = scaleFor(res < 8 ? 7 : res < 11 ? 10 : 12);  // dummy lookup
  const sc   = SCALE_MAP.find(s => s.res === res);
  return new deck.H3HexagonLayer({
    id:            'h3',
    data:          filtered(res),
    getHexagon:    d => d.h3_cell,
    getFillColor:  d => pc(d.max_priority_level),
    getElevation:  () => 0,
    extruded:      false,
    pickable:      true,
    autoHighlight: true,
    highlightColor:[255,255,255,50],
    coverage:      sc ? sc.cov : 0.85,
    updateTriggers:{ data: [res, activeFilter], getFillColor: activeFilter },
  });
}

// ─── 篩選按鈕 ────────────────────────────────────────────────
function setFilter(f) {
  activeFilter = f;
  ['all','High','Medium','Low'].forEach(k => {
    const el = document.getElementById('btn-' + k);
    if (el) el.classList.toggle('on', k === f);
  });
  if (inst) inst.setProps({ layers: [tileLayer(), h3Layer(currentRes)] });
}

// ─── Badge ────────────────────────────────────────────────────
function updateBadge(zoom) {
  const s = scaleFor(zoom);
  document.getElementById('res-label').textContent  = s.label;
  document.getElementById('zoom-label').textContent = 'zoom ' + zoom.toFixed(1);
}

// ─── Tooltip ────────────────────────────────────────────────
function makeTooltip({ object: d }) {
  if (!d) return null;
  const t = (d.latest_report_time || '').substring(0,16).replace('T',' ') || '—';
  return {
    html: `
      <div style="background:#0d1628;border:1px solid rgba(56,189,248,.4);border-radius:8px;
                  padding:10px 14px;font-size:13px;color:#e2e8f0;min-width:220px">
        <div style="font-size:.6rem;color:#94a3b8;font-family:monospace;margin-bottom:6px">${d.h3_cell}</div>
        <table style="width:100%;border-collapse:collapse">
          <tr><td style="color:#94a3b8;padding:2px 0">回報數</td>
              <td style="text-align:right;font-weight:700">${d.report_count}</td></tr>
          <tr><td style="color:#94a3b8;padding:2px 0">事件數</td>
              <td style="text-align:right;font-weight:700">${d.event_count}</td></tr>
          <tr><td style="color:#94a3b8;padding:2px 0">主要災害</td>
              <td style="text-align:right;font-weight:700">${d.main_disaster_type}</td></tr>
          <tr><td style="color:#94a3b8;padding:2px 0">優先級</td>
              <td style="text-align:right;font-weight:700">${d.max_priority_level}</td></tr>
          <tr><td style="color:#94a3b8;padding:2px 0">待協助人數</td>
              <td style="text-align:right;font-weight:700">${d.estimated_people_need_help}</td></tr>
          <tr><td style="color:#94a3b8;padding:2px 0">最新回報</td>
              <td style="text-align:right;font-size:.75rem">${t}</td></tr>
        </table>
      </div>`,
    style: { backgroundColor:'transparent', border:'none', padding:'0' }
  };
}

// ─── 初始化 Deck ────────────────────────────────────────────
inst = new deck.Deck({
  parent: document.getElementById('dc'),
  width:  '100%',
  height: '100%',
  initialViewState: {
    longitude: 120.97,
    latitude:  23.97,
    zoom:      7,
    pitch:     0,
    bearing:   0,
    minZoom:   4,
    maxZoom:   16,
  },
  controller: true,
  layers: [tileLayer(), h3Layer(5)],

  onViewStateChange({ viewState }) {
    const newRes = scaleFor(viewState.zoom).res;
    updateBadge(viewState.zoom);
    if (newRes !== currentRes) {
      currentRes = newRes;
      inst.setProps({ layers: [tileLayer(), h3Layer(newRes)] });
    }
  },

  getTooltip: makeTooltip,
});
</script>
</body>
</html>"""

def build_map_html(d5: list, d7: list, d9: list) -> str:
    return (MAP_TEMPLATE
            .replace("__MAP_HEIGHT__", str(MAP_HEIGHT))
            .replace("__DATA_RES5__",  json.dumps(d5, ensure_ascii=False))
            .replace("__DATA_RES7__",  json.dumps(d7, ensure_ascii=False))
            .replace("__DATA_RES9__",  json.dumps(d9, ensure_ascii=False)))

# ═══════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════

# ── Sidebar 控制 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗺️ 顯示設定")
    show_closed = st.toggle(
        "顯示已關閉事件的格網",
        value=False,
        help="關閉 → 只顯示含有 pending_review / active 事件的格網；\n開啟 → 同時顯示 resolved / archived 歷史格網。"
    )

_active_only = not show_closed

# ── 讀取所有 grid 類型的摘要 ─────────────────────────────────
h3_summaries       = get_grid_summaries(grid_type="h3",       active_only=_active_only)
district_summaries = get_grid_summaries(grid_type="district", active_only=_active_only)
city_summaries     = get_grid_summaries(grid_type="city",     active_only=_active_only)

# ── 若無 H3 資料，注入台灣測試格網讓地圖可以驗證渲染 ─────────
_using_demo = False
if not h3_summaries:
    _using_demo = True
    import h3 as _h3
    # 台灣主要城市座標 → 測試 H3 cells (Res 9)
    _demo_coords = [
        (25.0330, 121.5654, "High",   "淹水",   5, 3),
        (25.0475, 121.5173, "High",   "火災",   3, 2),
        (24.1477, 120.6736, "Medium", "土石流", 2, 1),
        (22.9998, 120.2269, "Medium", "淹水",   4, 2),
        (25.1276, 121.7390, "Low",    "其他",   1, 1),
        (22.6273, 120.3014, "Low",    "火災",   2, 1),
        (24.8066, 120.9686, "High",   "地震",   6, 4),
    ]
    h3_summaries = []
    for lat, lng, lvl, dtype, rcnt, ecnt in _demo_coords:
        cell = _h3.latlng_to_cell(lat, lng, 9)
        h3_summaries.append({
            "h3_cell": cell, "h3_resolution": 9,
            "report_count": rcnt, "event_count": ecnt, "image_count": rcnt,
            "main_disaster_type": dtype,
            "max_priority_score": {"High":80,"Medium":55,"Low":20}[lvl],
            "max_priority_level": lvl,
            "max_report_severity_score": 50,
            "estimated_people_need_help": rcnt * 2,
            "latest_report_time": "2025-05-25T12:00:00",
            "center_lat": lat, "center_lng": lng, "updated_at": "",
        })

# H3 資料用於地圖渲染
base_df = pd.DataFrame(h3_summaries)

# 全部 grid 資料用於統計卡
all_summaries = h3_summaries + district_summaries + city_summaries
all_df = pd.DataFrame(all_summaries) if all_summaries else base_df

# ── Demo / 部分資料提示 ───────────────────────────────────────
if _using_demo:
    non_h3_cnt = len(district_summaries) + len(city_summaries)
    if non_h3_cnt > 0:
        st.info(
            f"📍 有 **{non_h3_cnt}** 個行政區 / 縣市格網（無 GPS 回報），"
            "已統計在資料卡中，但地圖只顯示 H3 格網。\n\n"
            "地圖目前顯示**示範資料**；送出含 GPS 座標的回報後即顯示真實格網。"
        )
    else:
        st.warning(
            "⚠️ 尚無真實 H3 資料，目前顯示**示範格網**（台灣幾個城市）以確認地圖渲染正常。\n\n"
            "在「災情回報」頁面開啟 GPS 定位或輸入手動座標後送出，這裡即會顯示真實資料。"
        )
elif district_summaries or city_summaries:
    _filter_note = "（僅顯示進行中事件）" if _active_only else "（含已關閉事件）"
    st.info(
        f"🗺️ 地圖顯示 **{len(h3_summaries)}** 個 H3 格網 {_filter_note}（含 GPS 座標）。"
        f"另有 **{len(district_summaries)}** 個行政區格網、**{len(city_summaries)}** 個縣市格網"
        "（僅地址、無 GPS）已計入統計但未顯示在地圖上。"
    )
elif _active_only:
    st.success("✅ 所有格網的事件均已關閉，目前無進行中的災情。")

# ── 頂部統計卡 ────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
def _stat(col, label, val, tone="blue"):
    with col:
        st.markdown(stat_card(label, val, tone=tone), unsafe_allow_html=True)

total_reports = int(all_df["report_count"].sum()) if not all_df.empty else 0
high_grids    = int((all_df["max_priority_level"] == "High").sum()) if not all_df.empty else 0
total_ppl     = int(all_df["estimated_people_need_help"].sum()) if not all_df.empty else 0

_stat(c1, "H3 格網數 (含聚合)",  len(h3_summaries),  "blue")
_stat(c2, "總回報數（所有格網）", total_reports,       "purple")
_stat(c3, "高風險格網",           high_grids,          "red")
_stat(c4, "疑似待協助人數",       total_ppl,           "yellow")

st.markdown("<hr>", unsafe_allow_html=True)
st.caption("💡 滑鼠滾輪縮放地圖 → 自動切換 H3 解析度　｜　右上角按鈕可篩選優先級　｜　懸停格網查看詳情")

# ── 計算三個尺度資料 ──────────────────────────────────────────
with st.spinner("計算多尺度聚合資料..."):
    data_res5 = aggregate_to_res(base_df, 5)
    data_res7 = aggregate_to_res(base_df, 7)
    data_res9 = aggregate_to_res(base_df, 9)

# 資料診斷（確認有資料傳入地圖）
st.caption(
    f"📊 格網資料筆數 → "
    f"Res 5（縣市）: **{len(data_res5)}** 格　"
    f"Res 7（行政區）: **{len(data_res7)}** 格　"
    f"Res 9（街區）: **{len(data_res9)}** 格"
)

# ── 渲染地圖 ──────────────────────────────────────────────────
html = build_map_html(data_res5, data_res7, data_res9)
st.markdown('<div class="cl-map-shell">', unsafe_allow_html=True)
components.html(html, height=MAP_HEIGHT + 10, scrolling=False)
st.markdown('</div>', unsafe_allow_html=True)
