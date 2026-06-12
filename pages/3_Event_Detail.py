"""Page 3 — 事件詳情 Event Detail"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import streamlit as st
from datetime import datetime
from db.database import init_db
from db.queries import (
    get_event, get_reports_by_event, get_all_events,
    insert_admin_correction, get_admin_corrections,
    update_report_disaster_type, update_event_disaster_type,
)
from utils.auth import require_admin
from utils.ui_theme import apply_theme, badge, page_header, stat_card, top_pill

init_db()

st.set_page_config(page_title="事件詳情｜CrisisLens", page_icon="🔎", layout="wide", initial_sidebar_state="expanded")
apply_theme()
admin = require_admin()

# ── 事件選擇 ──────────────────────────────────────────────────
events = get_all_events()
if not events:
    st.warning("尚無事件資料，請先到「災情回報」頁面新增回報。")
    st.stop()

event_options = {f"#{e['event_id']} {e.get('event_name','（未命名）')} [{e.get('event_priority_level','')}]": e["event_id"]
                 for e in events}
_labels = list(event_options.keys())

# 從 Dashboard 跳轉時帶入 selected_event_id
_preselect_id = st.session_state.pop("selected_event_id", None)
_default_idx = 0
if _preselect_id is not None:
    for i, label in enumerate(_labels):
        if event_options[label] == _preselect_id:
            _default_idx = i
            break

selected_label = st.selectbox("選擇事件", _labels, index=_default_idx)
event_id = event_options[selected_label]

ev      = get_event(event_id)
reports = get_reports_by_event(event_id)

if not ev:
    st.error("找不到事件")
    st.stop()

top_pill(4, "事件詳細頁", "Event Detail")
page_header(
    ev.get("event_name", "事件詳情"),
    "查看事件摘要、現場狀況、回報影像與最嚴重回報的應變建議。",
    "Event Detail",
)

# ── 事件摘要卡片 ──────────────────────────────────────────────
def _badge(level: str) -> str:
    return badge(level, level)


def _fmt_time(value: str | None) -> str:
    if not value:
        return "-"
    raw = str(value)
    try:
        return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw[:16].replace("T", " ")

pri   = ev.get("event_priority_level","Low")
cred  = ev.get("credibility_level","Low")
sev   = ev.get("max_report_severity_level","Low")
ppl   = ev.get("estimated_people_need_help", 0) or 0
loc   = f"{ev.get('city','') or ''}{ev.get('district','') or ''}{ev.get('location_name','') or ''}"

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(stat_card("事件優先級", pri, f"分數 {ev.get('event_priority_score',0)}", {"High":"red","Medium":"yellow","Low":"green"}.get(pri, "text")), unsafe_allow_html=True)
with m2:
    st.markdown(stat_card("疑似待協助人數", f"約 {ppl} 人", "來源：使用者回報 · 需人工確認", "blue"), unsafe_allow_html=True)
with m3:
    st.markdown(stat_card("回報數 / 可信度", f"{ev.get('report_count',0)} 筆", cred, "text"), unsafe_allow_html=True)
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
    t_str  = _fmt_time(rpt.get("upload_time"))
    dt_str = rpt.get("disaster_type","")

    trapped_i = "🔴 受困  " if rpt.get("has_trapped_people") else ""
    injured_i = "🟠 受傷  " if rpt.get("has_injured_people") else ""
    blocked_i = "🚧 道路阻斷" if rpt.get("road_blocked")     else ""
    ppl_i     = f"👥 {rpt.get('reported_people_count',0)} 人" if rpt.get("reported_people_count") else ""

    expander_title = f"回報 #{rpt['report_id']} | {sev_r} | {dt_str} | {t_str}"
    with st.expander(expander_title, expanded=(i==1)):
        ec1, ec2 = st.columns([1, 2])

        with ec1:
            img_path = rpt.get("image_path","")
            if img_path and os.path.exists(img_path):
                from PIL import Image
                from utils.image_utils import resize_for_display
                img = Image.open(img_path).convert("RGB")
                st.image(resize_for_display(img), width="stretch")
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

            # ── 安全標籤顯示 ──────────────────────────────────
            in_safety  = rpt.get("input_safety_label",  "safe") or "safe"
            out_safety = rpt.get("output_safety_label", "safe") or "safe"
            safety_rsn = rpt.get("safety_reason", "") or ""
            _SAFETY_COLOR = {"safe": "#4ade80", "review": "#fbbf24", "block": "#f87171", "sanitize": "#fb923c"}
            if in_safety != "safe" or out_safety != "safe":
                _in_c  = _SAFETY_COLOR.get(in_safety, "#94a3b8")
                _out_c = _SAFETY_COLOR.get(out_safety, "#94a3b8")
                st.markdown(
                    f"""<div style="margin-top:8px;padding:6px 10px;border-radius:6px;
                        background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.3);font-size:.78rem">
                      🛡️ 安全標記 —
                      輸入：<span style="color:{_in_c};font-weight:700">{in_safety}</span>
                      ／輸出：<span style="color:{_out_c};font-weight:700">{out_safety}</span>
                      {"<br><span style='color:#94a3b8'>" + safety_rsn + "</span>" if safety_rsn else ""}
                    </div>""",
                    unsafe_allow_html=True,
                )

            # ── need_review 警示 ──────────────────────────────
            if rpt.get("need_review"):
                st.markdown(
                    '<div style="margin-top:6px;font-size:.78rem;color:#fbbf24">'
                    '⚠️ AI 信心度不足或模型結果不一致，建議人工確認災害類型</div>',
                    unsafe_allow_html=True,
                )

        # ── Admin Correction（管理員人工修正）──────────────────
        _DISASTER_TYPES_EN = [
            "Earthquake Damage", "Flood", "Fire",
            "Typhoon or Storm Damage", "Landslide", "Other or No Disaster",
        ]
        _DISASTER_TYPES_ZH = ["地震或建築損壞", "淹水", "火災", "颱風或強風災損", "土石流或坍方", "其他或無明顯災害"]
        _TYPE_LABELS = [f"{zh}（{en}）" for zh, en in zip(_DISASTER_TYPES_ZH, _DISASTER_TYPES_EN)]

        # 現有修正記錄
        existing = get_admin_corrections(report_id=rpt["report_id"])
        st.markdown(f"**📝 管理員修正（{len(existing)} 筆歷史）**")
        with st.container():
            if existing:
                for cx in existing:
                    st.markdown(
                        f"<div style='font-size:.78rem;color:#94a3b8;padding:4px 0'>"
                        f"🕒 {cx.get('corrected_at','')[:16]} · "
                        f"由 <strong>{cx.get('corrected_by','')}</strong> 修正 "
                        f"<code>{cx.get('field_name','')}</code> ：{cx.get('original_value','')} → "
                        f"<strong style='color:#38bdf8'>{cx.get('corrected_value','')}</strong>"
                        f"{'　（' + cx.get('correction_reason','') + '）' if cx.get('correction_reason') else ''}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("尚無修正記錄。")

            st.markdown("**新增修正**")
            _cur_type = rpt.get("disaster_type", _DISASTER_TYPES_EN[0])
            _cur_idx  = _DISASTER_TYPES_EN.index(_cur_type) if _cur_type in _DISASTER_TYPES_EN else 0
            _new_label = st.selectbox(
                "修正後災害類型",
                _TYPE_LABELS,
                index=_cur_idx,
                key=f"corr_type_{rpt['report_id']}",
            )
            _new_en = _DISASTER_TYPES_EN[_TYPE_LABELS.index(_new_label)]
            _reason = st.text_input(
                "修正原因（選填）",
                placeholder="例如：現場確認為土石流非地震損壞",
                key=f"corr_reason_{rpt['report_id']}",
            )
            if st.button("提交修正", key=f"corr_submit_{rpt['report_id']}"):
                if _new_en == _cur_type:
                    st.warning("修正值與原值相同，未寫入。")
                else:
                    _admin_name = (admin or {}).get("username", "admin")
                    try:
                        insert_admin_correction({
                            "corrected_at":       datetime.now().isoformat(timespec="seconds"),
                            "corrected_by":       _admin_name,
                            "report_id":          rpt["report_id"],
                            "event_id":           ev["event_id"],
                            "field_name":         "disaster_type",
                            "original_value":     _cur_type,
                            "corrected_value":    _new_en,
                            "correction_reason":  _reason or None,
                            "used_for_retraining": 0,
                            "retraining_batch_id": None,
                            "notes":              None,
                        })
                        # 同步更新 reports 表
                        update_report_disaster_type(rpt["report_id"], _new_en)
                        # 若此回報所屬事件的 disaster_type 也是舊值，一併更新事件名稱
                        if ev.get("disaster_type") == _cur_type:
                            from utils.config import CLASS_MAP
                            _new_zh = CLASS_MAP.get(_new_en, _new_en)
                            _loc = f"{ev.get('city','') or ''}{ev.get('district','') or ''}"
                            _date = (ev.get("latest_report_time") or "")[:10]
                            _new_name = f"{_date} {_loc} {_new_zh}事件".strip()
                            update_event_disaster_type(ev["event_id"], _new_en, _new_name)
                        st.success(f"已記錄修正：{_cur_type} → {_new_en}，事件名稱已更新")
                        st.rerun()
                    except Exception as _ce:
                        st.error(f"修正失敗：{_ce}")
