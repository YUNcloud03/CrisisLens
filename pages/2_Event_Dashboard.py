"""Page 2 — 事件列表 Event Dashboard"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from db.database import init_db
from db.queries import get_all_events, update_event_status, get_event_ids_with_need_review, get_need_review_reports
from utils.auth import require_admin
from utils.logger import log_error
from utils.ui_theme import apply_theme, badge, empty_state, page_header, stat_card, top_pill

init_db()

st.set_page_config(page_title="事件列表｜CrisisLens", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
apply_theme()
admin = require_admin()

top_pill(3, "管理端 - Dashboard 總覽", "Admin Dashboard")
page_header(
    "事件列表",
    "依災害類型、地點、優先級與狀態篩選事件，快速掌握需要處理的災情。",
    "Event Dashboard",
)

# ── 篩選 ─────────────────────────────────────────────────────
fc1, fc2, fc3, fc4 = st.columns(4)
with fc1: filter_type  = st.selectbox("災害類型", ["全部","Earthquake Damage","Flood","Fire","Typhoon or Storm Damage","Landslide"])
with fc2: filter_city  = st.selectbox("縣市",     ["全部","台北市","新北市","桃園市","台中市","台南市","高雄市","花蓮縣","台東縣","其他"])
with fc3: filter_pri   = st.selectbox("優先級",   ["全部","High","Medium","Low"])
with fc4: filter_status= st.selectbox("狀態",     ["全部","pending_review","active","resolved","archived"])

# 待審核篩選
filter_need_review = st.checkbox("🔍 只顯示含待審核回報的事件（AI 信心不足或模型不一致）")

events = get_all_events(
    disaster_type = None if filter_type   == "全部" else filter_type,
    city          = None if filter_city   == "全部" else filter_city,
    priority_level= None if filter_pri    == "全部" else filter_pri,
    status        = None if filter_status == "全部" else filter_status,
)

# 若勾選「待審核」，進一步過濾
_need_review_event_ids = None
if filter_need_review:
    _need_review_event_ids = get_event_ids_with_need_review()
    events = [e for e in events if e["event_id"] in _need_review_event_ids]

total_reports = sum(int(ev.get("report_count", 0) or 0) for ev in events)
high_events   = sum(1 for ev in events if ev.get("event_priority_level") == "High")
avg_cred = 0
if events:
    cred_map = {"Low": 42, "Medium": 68, "High": 82, "Verified": 92}
    avg_cred = int(sum(cred_map.get(ev.get("credibility_level"), 50) for ev in events) / len(events))

# 待審核事件 ID（查詢一次，卡片渲染時重用，避免 N+1）
if _need_review_event_ids is None:
    _need_review_event_ids = get_event_ids_with_need_review()
need_review_event_cnt = len(_need_review_event_ids)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(stat_card("總回報數", total_reports, "All reports", "blue"), unsafe_allow_html=True)
with k2:
    st.markdown(stat_card("聚合事件數", len(events), "Aggregated events", "purple"), unsafe_allow_html=True)
with k3:
    st.markdown(stat_card("高風險事件", high_events, "High priority", "red"), unsafe_allow_html=True)
with k4:
    st.markdown(stat_card("待審核事件", need_review_event_cnt, "Need review", "yellow"), unsafe_allow_html=True)

st.markdown(f"<p style='color:#94a3b8;font-size:.85rem'>目前篩選結果：共 {len(events)} 個事件</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

if not events:
    empty_state("尚無事件資料", "先到「災情回報」頁面新增回報。", "📭")
    st.stop()

_STATUS_ZH = {
    "pending_review": "待審核",
    "active":         "進行中",
    "resolved":       "已處理",
    "archived":       "已封存",
}
_STATUS_OPTIONS = ["pending_review", "active", "resolved", "archived"]

def _badge(level: str, kind: str = "priority") -> str:
    return badge(level, level)

st.markdown('<div class="cl-panel-title">事件優先排序（依 Priority Score）</div>', unsafe_allow_html=True)

# ── 事件卡片列表 ──────────────────────────────────────────────
for idx, ev in enumerate(events, 1):
    pri   = ev.get("event_priority_level","Low")
    cred  = ev.get("credibility_level","Low")
    sev   = ev.get("max_report_severity_level","Low")
    loc   = f"{ev.get('city','') or ''}{ev.get('district','') or ''}{ev.get('location_name','') or ''}"
    ppl   = ev.get("estimated_people_need_help", 0) or 0
    t_str = (ev.get("latest_report_time") or "")[:16]

    trapped_icon = "🔴 有人受困  " if ev.get("has_trapped_people") else ""
    injured_icon = "🟠 有人受傷  " if ev.get("has_injured_people") else ""
    blocked_icon = "🚧 道路阻斷"  if ev.get("road_blocked")       else ""

    priority_score = ev.get("event_priority_score", 0) or 0
    idx_color  = "#fb7185" if idx <= 3 else "#b6c2d2"
    pri_color  = "#f87171" if pri == "High" else "#fbbf24" if pri == "Medium" else "#4ade80"
    badge_pri  = _badge(pri)
    badge_sev  = _badge(sev)
    badge_cred = _badge(cred)
    # 待審核標記
    has_review = ev["event_id"] in _need_review_event_ids
    review_badge = ' <span style="font-size:.72rem;padding:1px 6px;border-radius:4px;background:rgba(251,191,36,.15);color:#fbbf24;border:1px solid rgba(251,191,36,.3)">⚠️ 待審核</span>' if has_review else ""
    st.markdown(
        f'<div class="event-row" style="padding:14px 16px;margin-bottom:10px">'
        f'<div style="display:flex;gap:14px;align-items:flex-start">'
        # 序號
        f'<div style="min-width:32px;font-size:1.4rem;font-weight:900;color:{idx_color}">{idx}</div>'
        # 主內容
        f'<div style="flex:1;min-width:0">'
        f'<div style="font-size:.7rem;color:#475569">事件 #{ev["event_id"]} · {ev.get("disaster_type","")}</div>'
        f'<div style="font-weight:700;font-size:1rem;color:#e2e8f0;margin:2px 0">{ev.get("event_name","（未命名事件）")}{review_badge}</div>'
        f'<div style="font-size:.82rem;color:#94a3b8">📍 {loc or "未填地點"}</div>'
        f'<div style="margin-top:4px;font-size:.82rem;color:#94a3b8">{trapped_icon}{injured_icon}{blocked_icon}</div>'
        f'</div>'
        # 右側評分
        f'<div style="text-align:right;white-space:nowrap">'
        f'<div style="font-size:1.25rem;font-weight:900;color:{pri_color}">{priority_score}</div>'
        f'<div style="margin:4px 0">優先級 {badge_pri} 嚴重度 {badge_sev} 可信度 {badge_cred}</div>'
        f'<div style="font-size:.78rem;color:#94a3b8">回報 {ev.get("report_count",1)} 筆 · 疑似 {ppl} 人 · {t_str}</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander(f"▶ 查看事件 #{ev['event_id']} 詳情 / 更改狀態"):
        sc1, sc2 = st.columns([2, 1])
        with sc1:
            if st.button(f"📋 開啟事件 #{ev['event_id']} 完整頁面", key=f"goto_{ev['event_id']}"):
                st.session_state["selected_event_id"] = ev["event_id"]
                st.switch_page("pages/3_Event_Detail.py")
        with sc2:
            cur_status = ev.get("status", "pending_review")
            # 向下相容：舊資料可能還有 verified/closed，安全 fallback
            if cur_status not in _STATUS_OPTIONS:
                cur_status = {"verified": "active", "closed": "resolved"}.get(cur_status, "pending_review")
            new_status = st.selectbox(
                "更改狀態",
                _STATUS_OPTIONS,
                format_func=lambda s: f"{_STATUS_ZH.get(s, s)} ({s})",
                index=_STATUS_OPTIONS.index(cur_status),
                key=f"status_{ev['event_id']}",
            )
            reason_input = st.text_input(
                "原因（選填）", key=f"reason_{ev['event_id']}",
                placeholder="例如：現場確認已解除"
            )
            if st.button("更新", key=f"upd_{ev['event_id']}"):
                try:
                    admin_username = (admin or {}).get("username", "admin")
                    update_event_status(
                        ev["event_id"], new_status,
                        admin_user=admin_username,
                        reason=reason_input or None,
                    )
                    st.success(f"狀態已更新 → {_STATUS_ZH.get(new_status, new_status)}")
                    st.rerun()
                except Exception as e:
                    log_error("dashboard.update_status", str(e), exc_info=True,
                              username=(admin or {}).get("username"))
                    st.error(f"更新失敗：{e}")
