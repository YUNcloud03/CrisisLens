"""Page 3 — 事件詳情 Event Detail"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import streamlit as st
from db.database import init_db
from db.queries import get_event, get_reports_by_event, get_all_events
from utils.ui_theme import apply_theme

init_db()

st.set_page_config(page_title="事件詳情｜CrisisLens", page_icon="🔎", layout="wide")
apply_theme()

st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background:#080d1a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background:#0a1220!important;border-right:1px solid rgba(30,64,120,.45)}
h1,h2,h3,h4{color:#e2e8f0!important}
.card{background:#0d1628;border:1px solid rgba(30,64,120,.45);border-radius:10px;padding:16px 20px;margin-bottom:12px}
.report-card{background:#0a1220;border:1px solid rgba(30,64,120,.35);border-radius:8px;padding:12px 14px;margin-bottom:8px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.72rem;font-weight:600}
.badge-high{background:rgba(220,38,38,.18);color:#f87171;border:1px solid rgba(248,113,113,.35)}
.badge-medium{background:rgba(217,119,6,.18);color:#fbbf24;border:1px solid rgba(251,191,36,.35)}
.badge-low{background:rgba(22,163,74,.18);color:#4ade80;border:1px solid rgba(74,222,128,.35)}
.badge-blue{background:rgba(56,189,248,.18);color:#38bdf8;border:1px solid rgba(56,189,248,.35)}
.advice-item{background:rgba(56,189,248,.06);border-left:3px solid #38bdf8;padding:8px 12px;margin:4px 0;border-radius:0 6px 6px 0;font-size:.85rem}
hr{border-color:rgba(30,64,120,.45)!important}
footer{visibility:hidden}
</style>""", unsafe_allow_html=True)

# ── 事件選擇 ──────────────────────────────────────────────────
events = get_all_events()
if not events:
    st.warning("尚無事件資料，請先到「災情回報」頁面新增回報。")
    st.stop()

event_options = {f"#{e['event_id']} {e.get('event_name','（未命名）')} [{e.get('event_priority_level','')}]": e["event_id"]
                 for e in events}
selected_label = st.selectbox("選擇事件", list(event_options.keys()))
event_id = event_options[selected_label]

ev      = get_event(event_id)
reports = get_reports_by_event(event_id)

if not ev:
    st.error("找不到事件")
    st.stop()

st.markdown(f"## 🔎 {ev.get('event_name','事件詳情')}")
st.markdown("<hr>", unsafe_allow_html=True)

# ── 事件摘要卡片 ──────────────────────────────────────────────
def _badge(level: str) -> str:
    cls = {"High":"badge-high","Medium":"badge-medium","Low":"badge-low",
           "Verified":"badge-blue"}.get(level,"badge-low")
    return f'<span class="badge {cls}">{level}</span>'

pri   = ev.get("event_priority_level","Low")
cred  = ev.get("credibility_level","Low")
sev   = ev.get("max_report_severity_level","Low")
ppl   = ev.get("estimated_people_need_help", 0) or 0
loc   = f"{ev.get('city','') or ''}{ev.get('district','') or ''}{ev.get('location_name','') or ''}"

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""<div class="card">
    <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">事件優先級</div>
    <div style="font-size:1.8rem;font-weight:800;{'color:#f87171' if pri=='High' else 'color:#fbbf24' if pri=='Medium' else 'color:#4ade80'}">{pri}</div>
    <div style="color:#94a3b8;font-size:.82rem">分數 {ev.get('event_priority_score',0)}</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="card">
    <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">疑似待協助人數</div>
    <div style="font-size:1.8rem;font-weight:800;color:#38bdf8">約 {ppl} 人</div>
    <div style="color:#94a3b8;font-size:.75rem">來源：使用者回報 · 需人工確認</div>
    </div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""<div class="card">
    <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">回報數 / 可信度</div>
    <div style="font-size:1.8rem;font-weight:800;color:#e2e8f0">{ev.get('report_count',0)} 筆</div>
    <div style="margin-top:4px">{_badge(cred)}</div>
    </div>""", unsafe_allow_html=True)
with m4:
    trapped_t = "🔴 有人受困" if ev.get("has_trapped_people") else "✅ 無受困回報"
    injured_t = "🟠 有人受傷" if ev.get("has_injured_people") else "✅ 無受傷回報"
    blocked_t = "🚧 道路阻斷" if ev.get("road_blocked")       else "✅ 道路可通"
    st.markdown(f"""<div class="card">
    <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">現場狀況</div>
    <div style="font-size:.85rem;line-height:2;margin-top:4px">{trapped_t}<br>{injured_t}<br>{blocked_t}</div>
    </div>""", unsafe_allow_html=True)

# ── 地點 & 時間 ────────────────────────────────────────────────
st.markdown(f"""<div class="card" style="display:flex;gap:32px;flex-wrap:wrap">
  <div><span style="color:#94a3b8;font-size:.75rem">📍 地點</span><br>
       <span style="color:#e2e8f0">{loc or '未填'}</span></div>
  <div><span style="color:#94a3b8;font-size:.75rem">🕒 最新回報</span><br>
       <span style="color:#e2e8f0">{(ev.get('latest_report_time') or '')[:16]}</span></div>
  <div><span style="color:#94a3b8;font-size:.75rem">📌 狀態</span><br>
       <span style="color:#38bdf8">{ev.get('status','')}</span></div>
  <div><span style="color:#94a3b8;font-size:.75rem">🌪️ 災害類型</span><br>
       <span style="color:#e2e8f0">{ev.get('disaster_type','')}</span></div>
</div>""", unsafe_allow_html=True)

# ── RAG 建議（來自最嚴重 report）─────────────────────────────
if reports:
    top_report  = reports[0]
    rag_advice_raw = top_report.get("rag_advice")
    if rag_advice_raw:
        try:
            advice_list = json.loads(rag_advice_raw)
        except Exception:
            advice_list = [rag_advice_raw]

        st.markdown("#### 💡 最嚴重回報的應變建議")
        for line in advice_list:
            clean = line.lstrip("・•-").strip()
            if clean:
                st.markdown(f'<div class="advice-item">・{clean}</div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"#### 📋 事件內所有回報（共 {len(reports)} 筆，依嚴重度排序）")

# ── 回報列表 ──────────────────────────────────────────────────
for i, rpt in enumerate(reports, 1):
    sev_r  = rpt.get("report_severity_level","Low")
    sev_s  = rpt.get("report_severity_score", 0)
    conf   = rpt.get("clip_confidence", 0) or 0
    t_str  = (rpt.get("upload_time") or "")[:16]
    dt_str = rpt.get("disaster_type","")

    trapped_i = "🔴 受困  " if rpt.get("has_trapped_people") else ""
    injured_i = "🟠 受傷  " if rpt.get("has_injured_people") else ""
    blocked_i = "🚧 道路阻斷" if rpt.get("road_blocked")     else ""
    ppl_i     = f"👥 {rpt.get('reported_people_count',0)} 人" if rpt.get("reported_people_count") else ""

    with st.expander(f"回報 #{rpt['report_id']}  |  {_badge(sev_r)}  |  {dt_str}  |  {t_str}", expanded=(i==1)):
        ec1, ec2 = st.columns([1, 2])

        with ec1:
            img_path = rpt.get("image_path","")
            if img_path and os.path.exists(img_path):
                from PIL import Image
                from utils.image_utils import resize_for_display
                img = Image.open(img_path).convert("RGB")
                st.image(resize_for_display(img), use_container_width=True)
            else:
                st.markdown("<div style='color:#475569;text-align:center;padding:30px'>無圖片</div>", unsafe_allow_html=True)

        with ec2:
            st.markdown(f"""
            <div style="margin-bottom:8px">
              {_badge(sev_r)} 嚴重度分數 <strong style="color:#38bdf8">{sev_s}</strong>
              &nbsp;·&nbsp; CLIP 信心度 {conf:.1%}
            </div>
            <div style="font-size:.85rem;color:#94a3b8;margin-bottom:8px">
              {trapped_i}{injured_i}{blocked_i}{ppl_i}
            </div>
            """, unsafe_allow_html=True)

            desc = rpt.get("description","")
            if desc:
                st.markdown(f'<div style="background:rgba(255,255,255,.03);border-radius:6px;padding:8px 12px;font-size:.85rem;color:#e2e8f0">{desc}</div>', unsafe_allow_html=True)

            loc_r = f"{rpt.get('city','') or ''}{rpt.get('district','') or ''}{rpt.get('location_name','') or ''}"
            if loc_r.strip():
                st.markdown(f'<div style="font-size:.8rem;color:#94a3b8;margin-top:6px">📍 {loc_r}</div>', unsafe_allow_html=True)

            top3_raw = rpt.get("top3_predictions")
            if top3_raw:
                try:
                    top3 = json.loads(top3_raw)
                    st.markdown("<div style='font-size:.75rem;color:#475569;margin-top:8px'>Top-3 預測</div>", unsafe_allow_html=True)
                    for item in top3:
                        pct = int(item["score"] * 100)
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:8px;margin:2px 0;font-size:.8rem">
                          <span style="color:#94a3b8;width:100px">{item['class_zh']}</span>
                          <div style="flex:1;background:rgba(255,255,255,.06);border-radius:4px;height:6px;overflow:hidden">
                            <div style="width:{pct}%;height:6px;background:#38bdf8;border-radius:4px"></div>
                          </div>
                          <span style="color:#94a3b8;width:32px;text-align:right">{pct}%</span>
                        </div>""", unsafe_allow_html=True)
                except Exception:
                    pass
