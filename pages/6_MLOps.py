"""Page 6 — MLOps 監控儀表板"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from datetime import datetime
from db.database import init_db
from db.queries import get_model_runs, get_admin_corrections, get_need_review_reports
from utils.auth import require_admin
from utils.ui_theme import apply_theme, page_header, stat_card, top_pill

init_db()

st.set_page_config(
    page_title="MLOps 監控｜CrisisLens",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
require_admin()

top_pill(7, "管理端 - MLOps 監控", "MLOps Dashboard")
page_header(
    "MLOps 監控儀表板",
    "追蹤模型版本、推論記錄、人工修正與系統品質指標，支援持續改善與 Retraining 決策。",
    "MLOps Dashboard",
)

# ─── 讀取資料 ─────────────────────────────────────────────────
model_runs   = get_model_runs(limit=50)
corrections  = get_admin_corrections()
review_rpts  = get_need_review_reports()

total_runs        = len(model_runs)
total_corrections = len(corrections)
need_review_cnt   = len(review_rpts)
review_rate       = f"{need_review_cnt / total_runs * 100:.1f}%" if total_runs else "—"

# ─── 統計卡 ───────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(stat_card("推論記錄數", total_runs,        "Model runs",       "blue"),   unsafe_allow_html=True)
with k2:
    st.markdown(stat_card("人工修正數", total_corrections, "Admin corrections","purple"), unsafe_allow_html=True)
with k3:
    st.markdown(stat_card("待審核回報", need_review_cnt,   "Need review",      "yellow"), unsafe_allow_html=True)
with k4:
    st.markdown(stat_card("待審核率",   review_rate,       "Review rate",      "red"),    unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ─── Tab 佈局 ─────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Model Runs（版本記錄）", "✏️ Admin Corrections（人工修正）", "🔍 待審核回報"])

# ══════════════════════════════════════════════════════════════
# Tab 1 — Model Runs
# ══════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    每次使用者送出回報時，系統會記錄使用的模型版本與規則版本。
    這是 MLOps 的核心追蹤機制，確保每個預測都可溯源。
    """)

    if not model_runs:
        st.info("尚無 Model Run 記錄。送出第一筆回報後即會出現。")
    else:
        # 版本摘要
        clip_versions   = sorted({r.get("clip_model_version", "—") or "—" for r in model_runs})
        resnet_versions = sorted({r.get("resnet_model_version", "—") or "—" for r in model_runs})
        agg_versions    = sorted({r.get("aggregation_rule_version", "—") or "—" for r in model_runs})

        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            st.markdown("**CLIP 版本**")
            for v in clip_versions:
                st.code(v, language=None)
        with vc2:
            st.markdown("**ResNet/CNN 版本**")
            for v in resnet_versions:
                st.code(v, language=None)
        with vc3:
            st.markdown("**聚合規則版本**")
            for v in agg_versions:
                st.code(v, language=None)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**最近 {len(model_runs)} 筆推論記錄**")

        for run in model_runs[:20]:
            t = (run.get("run_time") or "")[:16].replace("T", " ")
            rid = run.get("report_id", "—")
            cv  = run.get("clip_model_version", "—") or "—"
            rv  = run.get("resnet_model_version", "—") or "—"
            av  = run.get("aggregation_rule_version", "—") or "—"
            pv  = run.get("priority_rule_version", "—") or "—"
            st.markdown(
                f'<div style="padding:6px 12px;margin:3px 0;border-radius:6px;'
                f'background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);'
                f'font-size:.8rem;display:flex;gap:24px;flex-wrap:wrap;align-items:center">'
                f'<span style="color:#475569;min-width:120px">{t}</span>'
                f'<span style="color:#94a3b8">Run <strong>#{run["run_id"]}</strong> → Report #{rid}</span>'
                f'<span style="color:#38bdf8">CLIP: {cv}</span>'
                f'<span style="color:#a78bfa">ResNet: {rv}</span>'
                f'<span style="color:#4ade80">Agg: {av}</span>'
                f'<span style="color:#fb923c">Priority: {pv}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════
# Tab 2 — Admin Corrections
# ══════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    管理員在「事件詳情」頁面手動修正的 AI 分類結果。
    這些修正資料可用於未來的 Retraining（`used_for_retraining = 1`）。
    """)

    if not corrections:
        st.info("尚無修正記錄。在事件詳情頁面提交修正後會出現在此。")
    else:
        unused = [c for c in corrections if not c.get("used_for_retraining")]
        used   = [c for c in corrections if c.get("used_for_retraining")]

        c1, c2 = st.columns(2)
        with c1:
            st.metric("待用於 Retraining", len(unused))
        with c2:
            st.metric("已用於 Retraining", len(used))

        st.markdown("<br>", unsafe_allow_html=True)

        for cx in corrections:
            t        = (cx.get("corrected_at") or "")[:16].replace("T", " ")
            by       = cx.get("corrected_by", "?")
            old_v    = cx.get("original_value", "?")
            new_v    = cx.get("corrected_value", "?")
            reason   = cx.get("correction_reason", "") or ""
            retrain  = cx.get("used_for_retraining", 0)
            retrain_badge = (
                '<span style="color:#4ade80;font-size:.72rem">✅ 已用於 Retraining</span>'
                if retrain else
                '<span style="color:#94a3b8;font-size:.72rem">待 Retraining</span>'
            )
            st.markdown(
                f'<div style="padding:8px 12px;margin:4px 0;border-radius:6px;'
                f'background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);'
                f'font-size:.82rem">'
                f'<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">'
                f'<span style="color:#475569">{t}</span>'
                f'<span style="color:#94a3b8">Report #{cx.get("report_id","?")} · 由 <strong>{by}</strong></span>'
                f'<span style="color:#f87171">{old_v}</span>'
                f'<span style="color:#94a3b8">→</span>'
                f'<span style="color:#4ade80;font-weight:700">{new_v}</span>'
                f'{retrain_badge}'
                f'</div>'
                + (f'<div style="color:#94a3b8;font-size:.75rem;margin-top:3px">原因：{reason}</div>' if reason else "")
                + f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════
# Tab 3 — 待審核回報
# ══════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    `need_review = 1` 的回報：AI 信心度低、Top-2 差距小、或兩模型不一致。
    **待審核率持續偏高（> 30%）是觸發 Retraining 的信號。**
    """)

    if not review_rpts:
        st.success("✅ 目前無待審核回報。")
    else:
        st.markdown(f"**共 {len(review_rpts)} 筆**（依上傳時間排序）")
        for rpt in review_rpts[:30]:
            t     = (rpt.get("upload_time") or "")[:16].replace("T", " ")
            dtype = rpt.get("disaster_type", "?")
            conf  = rpt.get("clip_confidence", 0) or 0
            agree = rpt.get("model_agreement", 1)
            desc  = (rpt.get("description") or "")[:60]
            _agree_txt = (
                '<span style="color:#4ade80">模型一致</span>'
                if agree else
                '<span style="color:#fb923c">模型不一致</span>'
            )
            st.markdown(
                f'<div style="padding:7px 12px;margin:3px 0;border-radius:6px;'
                f'background:rgba(251,191,36,.04);border:1px solid rgba(251,191,36,.2);'
                f'font-size:.8rem;display:flex;gap:18px;flex-wrap:wrap;align-items:center">'
                f'<span style="color:#475569;min-width:130px">{t}</span>'
                f'<span style="color:#94a3b8">Report #{rpt["report_id"]}</span>'
                f'<span style="color:#38bdf8">{dtype}</span>'
                f'<span style="color:#fbbf24">信心 {conf:.0%}</span>'
                f'{_agree_txt}'
                + (f'<span style="color:#64748b;font-size:.75rem">{desc}…</span>' if desc else "")
                + f'</div>',
                unsafe_allow_html=True,
            )

        if len(review_rpts) > total_runs * 0.30 and total_runs >= 10:
            st.warning(
                f"⚠️ **待審核率 {review_rate} > 30%**（{need_review_cnt}/{total_runs} 筆）  \n"
                "建議收集更多修正標籤後執行 Retraining。"
            )
