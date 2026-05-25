"""Page 2 — 事件列表 Event Dashboard"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from db.database import init_db
from db.queries import get_all_events, update_event_status
from utils.ui_theme import apply_theme

init_db()

st.set_page_config(page_title="事件列表｜CrisisLens", page_icon="📊", layout="wide")
apply_theme()

st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background:#080d1a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background:#0a1220!important;border-right:1px solid rgba(30,64,120,.45)}
h1,h2,h3{color:#e2e8f0!important}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.72rem;font-weight:600}
.badge-high{background:rgba(220,38,38,.18);color:#f87171;border:1px solid rgba(248,113,113,.35)}
.badge-medium{background:rgba(217,119,6,.18);color:#fbbf24;border:1px solid rgba(251,191,36,.35)}
.badge-low{background:rgba(22,163,74,.18);color:#4ade80;border:1px solid rgba(74,222,128,.35)}
.badge-verified{background:rgba(56,189,248,.18);color:#38bdf8;border:1px solid rgba(56,189,248,.35)}
.event-row{background:#0d1628;border:1px solid rgba(30,64,120,.45);border-radius:8px;
           padding:12px 16px;margin-bottom:8px;cursor:pointer}
.event-row:hover{border-color:rgba(56,189,248,.35)}
hr{border-color:rgba(30,64,120,.45)!important}
footer{visibility:hidden}
</style>""", unsafe_allow_html=True)

st.markdown("## 📊 事件列表")

# ── 篩選 ─────────────────────────────────────────────────────
fc1, fc2, fc3, fc4 = st.columns(4)
with fc1: filter_type  = st.selectbox("災害類型", ["全部","Damaged Infrastructure","Fire Disaster","Land Disaster","Water Disaster","Non Damage"])
with fc2: filter_city  = st.selectbox("縣市",     ["全部","台北市","新北市","桃園市","台中市","台南市","高雄市","花蓮縣","台東縣","其他"])
with fc3: filter_pri   = st.selectbox("優先級",   ["全部","High","Medium","Low"])
with fc4: filter_status= st.selectbox("狀態",     ["全部","pending_review","verified","closed"])

events = get_all_events(
    disaster_type = None if filter_type   == "全部" else filter_type,
    city          = None if filter_city   == "全部" else filter_city,
    priority_level= None if filter_pri    == "全部" else filter_pri,
    status        = None if filter_status == "全部" else filter_status,
)

st.markdown(f"<p style='color:#94a3b8;font-size:.85rem'>共 {len(events)} 個事件</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

if not events:
    st.markdown("""<div style="text-align:center;padding:60px;color:#334155">
    <div style="font-size:2.5rem">📭</div>
    <div style="font-size:1rem;margin-top:12px">尚無事件資料</div>
    <div style="font-size:.85rem;margin-top:4px">先到「災情回報」頁面新增回報</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

def _badge(level: str, kind: str = "priority") -> str:
    cls = {"High":"badge-high","Medium":"badge-medium","Low":"badge-low",
           "Verified":"badge-verified","High Cred":"badge-verified"}.get(level, "badge-low")
    return f'<span class="badge {cls}">{level}</span>'

# ── 事件卡片列表 ──────────────────────────────────────────────
for ev in events:
    pri   = ev.get("event_priority_level","Low")
    cred  = ev.get("credibility_level","Low")
    sev   = ev.get("max_report_severity_level","Low")
    loc   = f"{ev.get('city','') or ''}{ev.get('district','') or ''}{ev.get('location_name','') or ''}"
    ppl   = ev.get("estimated_people_need_help", 0) or 0
    t_str = (ev.get("latest_report_time") or "")[:16]

    trapped_icon = "🔴 有人受困  " if ev.get("has_trapped_people") else ""
    injured_icon = "🟠 有人受傷  " if ev.get("has_injured_people") else ""
    blocked_icon = "🚧 道路阻斷"  if ev.get("road_blocked")       else ""

    st.markdown(f"""
    <div class="event-row">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="font-size:.7rem;color:#475569">事件 #{ev['event_id']} · {ev.get('disaster_type','')}</div>
          <div style="font-weight:700;font-size:1rem;color:#e2e8f0;margin:2px 0">
            {ev.get('event_name','（未命名事件）')}
          </div>
          <div style="font-size:.82rem;color:#94a3b8">📍 {loc or '未填地點'}</div>
          <div style="margin-top:6px;font-size:.82rem;color:#94a3b8">
            {trapped_icon}{injured_icon}{blocked_icon}
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0;margin-left:16px">
          <div>優先級 {_badge(pri)} 嚴重度 {_badge(sev)} 可信度 {_badge(cred)}</div>
          <div style="margin-top:6px;font-size:.8rem;color:#94a3b8">
            回報 {ev.get('report_count',1)} 筆 ·
            疑似 {ppl} 人需協助 ·
            {t_str}
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"▶ 查看事件 #{ev['event_id']} 詳情 / 更改狀態"):
        sc1, sc2 = st.columns([2, 1])
        with sc1:
            st.page_link(f"pages/3_Event_Detail.py",
                         label=f"📋 開啟事件 #{ev['event_id']} 完整頁面")
        with sc2:
            new_status = st.selectbox(
                "更改狀態",
                ["pending_review","verified","closed"],
                index=["pending_review","verified","closed"].index(ev.get("status","pending_review")),
                key=f"status_{ev['event_id']}",
            )
            if st.button("更新", key=f"upd_{ev['event_id']}"):
                update_event_status(ev["event_id"], new_status)
                st.success("狀態已更新")
                st.rerun()
