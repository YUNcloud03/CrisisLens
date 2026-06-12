"""Page 6 — MLOps 監控儀表板"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from db.database import init_db
import pandas as pd
from db.queries import (
    get_model_runs, get_admin_corrections, get_need_review_reports,
    get_correction_accuracy_stats, get_confidence_distribution,
    get_daily_confidence_stats,
)
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
tab1, tab2, tab3, tab4 = st.tabs(["📋 Model Runs（版本記錄）", "✏️ Admin Corrections（人工修正）", "🔍 待審核回報", "📊 效能分析"])

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
            st.markdown("**第二主模型版本（EfficientNet / 舊 ResNet・CNN）**")
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
                f'<span style="color:#a78bfa">2nd: {rv}</span>'
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

# ══════════════════════════════════════════════════════════════
# Tab 4 — 效能分析
# ══════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    以管理員修正記錄為 ground truth，計算線上模型預測準確率與每類別錯誤率。
    樣本數越多，指標越具代表性。
    """)

    acc_stats  = get_correction_accuracy_stats()
    conf_stats = get_confidence_distribution(limit=200)

    # ── 區塊 A：整體準確率 ────────────────────────────────────
    st.markdown("#### A｜整體預測準確率（基於管理員修正）")
    if len(acc_stats) < 5:
        st.info(f"修正資料尚不足以計算準確率，目前僅 {len(acc_stats)} 筆（需至少 5 筆）。")
    else:
        df_acc = pd.DataFrame(acc_stats)
        df_acc["correct"] = df_acc["predicted"] == df_acc["ground_truth"]
        overall_acc = df_acc["correct"].mean()
        n = len(df_acc)

        pa1, pa2 = st.columns(2)
        with pa1:
            st.metric("整體準確率", f"{overall_acc:.1%}", help=f"基於 {n} 筆管理員修正")
        with pa2:
            st.metric("錯誤修正筆數", int((~df_acc["correct"]).sum()), help="模型預測與管理員核實不符的次數")

        st.caption(f"資料來源：{n} 筆 disaster_type 管理員修正記錄")

        # ── 區塊 B：Per-class 錯誤率 ─────────────────────────
        st.markdown("#### B｜各類別錯誤率")
        class_stats = (
            df_acc.groupby("ground_truth")
            .agg(
                總修正筆數=("correct", "count"),
                預測錯誤數=("correct", lambda x: (~x).sum()),
            )
            .assign(錯誤率=lambda d: (d["預測錯誤數"] / d["總修正筆數"] * 100).round(1))
            .sort_values("錯誤率", ascending=False)
            .reset_index()
            .rename(columns={"ground_truth": "類別（Ground Truth）"})
        )
        st.dataframe(
            class_stats.style.background_gradient(subset=["錯誤率"], cmap="Reds"),
            use_container_width=True,
            hide_index=True,
        )

        # ── 區塊 C：混淆矩陣 ─────────────────────────────────
        st.markdown("#### C｜混淆矩陣（列 = Ground Truth，欄 = 模型預測）")
        all_classes = sorted(set(df_acc["predicted"]) | set(df_acc["ground_truth"]))
        cm = pd.crosstab(
            df_acc["ground_truth"],
            df_acc["predicted"],
            rownames=["ground_truth"],
            colnames=["predicted"],
        ).reindex(index=all_classes, columns=all_classes, fill_value=0)
        st.dataframe(
            cm.style.background_gradient(cmap="Blues"),
            use_container_width=True,
        )

    # ── 區塊 D：信心分佈趨勢 ──────────────────────────────────
    st.markdown("#### D｜近期推論信心分佈（最近 200 筆）")
    if not conf_stats:
        st.info("尚無推論記錄。")
    else:
        df_conf = pd.DataFrame(conf_stats)
        df_conf = df_conf.iloc[::-1].reset_index(drop=True)  # 時間升冪

        pd1, pd2, pd3 = st.columns(3)
        with pd1:
            st.metric("平均信心度", f"{df_conf['clip_confidence'].mean():.1%}")
        with pd2:
            agree_rate = df_conf["model_agreement"].mean() if "model_agreement" in df_conf else 0
            st.metric("雙模型一致率", f"{agree_rate:.1%}")
        with pd3:
            review_r = df_conf["need_review"].mean() if "need_review" in df_conf else 0
            st.metric("待審核率", f"{review_r:.1%}")

        st.line_chart(
            df_conf[["clip_confidence"]].rename(columns={"clip_confidence": "CLIP 信心度"}),
            use_container_width=True,
            height=200,
        )

    # ── 區塊 E：7 天信心 Drift 偵測 ──────────────────────────
    st.markdown("#### E｜7 天信心 Drift 偵測")
    daily_stats = get_daily_confidence_stats(days=14)
    if len(daily_stats) < 2:
        st.info("每日信心趨勢需至少 2 天資料，目前不足。")
    else:
        df_daily = pd.DataFrame(daily_stats)
        st.line_chart(
            df_daily.set_index("day")[["avg_conf", "review_rate"]].rename(
                columns={"avg_conf": "每日平均信心", "review_rate": "待審核率"}
            ),
            use_container_width=True,
            height=220,
        )
        if len(df_daily) >= 14:
            prev7 = df_daily.iloc[:7]["avg_conf"].mean()
            last7 = df_daily.iloc[7:]["avg_conf"].mean()
            drift  = (prev7 - last7) / prev7 if prev7 > 0 else 0
            if drift > 0.10:
                st.warning(
                    f"⚠️ **Model Drift 警告**：近 7 天平均信心 {last7:.1%}，"
                    f"較前 7 天 {prev7:.1%} 下滑 {drift:.1%}（閾值 10%）。"
                )
            else:
                st.success(f"✅ 信心分佈穩定（近 7 天 {last7:.1%} vs 前 7 天 {prev7:.1%}）。")

    # ── 區塊 F：推論延遲（P50 / P95）────────────────────────
    st.markdown("#### F｜推論延遲（最近 100 次）")
    df_runs = pd.DataFrame(get_model_runs(limit=100))
    lat = df_runs["inference_latency_ms"].dropna() if "inference_latency_ms" in df_runs.columns else pd.Series([], dtype=float)
    if lat.empty:
        st.info("尚無延遲記錄，送出回報後即開始累積。")
    else:
        lf1, lf2, lf3 = st.columns(3)
        with lf1:
            st.metric("P50 延遲", f"{lat.quantile(0.50):.0f} ms")
        with lf2:
            st.metric("P95 延遲", f"{lat.quantile(0.95):.0f} ms")
        with lf3:
            st.metric("最大延遲", f"{lat.max():.0f} ms")

    # ── 區塊 G：Retraining 觸發狀態燈號 ─────────────────────
    st.markdown("#### G｜Retraining 觸發評估")
    unused_count = len([c for c in corrections if not c.get("used_for_retraining")])
    _acc_for_rule = acc_stats if acc_stats else []
    if len(_acc_for_rule) >= 10:
        _df_r = pd.DataFrame(_acc_for_rule)
        _df_r["correct"] = _df_r["predicted"] == _df_r["ground_truth"]
        _overall_acc = _df_r["correct"].mean()
        r2 = _overall_acc < 0.70
    else:
        r2 = False
    _review_r = df_conf["need_review"].mean() if conf_stats else 0
    r1 = unused_count >= 20
    r3 = _review_r > 0.30

    triggered = []
    if r1: triggered.append(f"R1：未用於 Retraining 的修正數 {unused_count} 筆（閾值 ≥ 20）")
    if r2: triggered.append(f"R2：線上準確率 {_overall_acc:.1%} 低於 70%")
    if r3: triggered.append(f"R3：待審核率 {_review_r:.1%} 高於 30%")

    if triggered:
        st.error("🔴 **建議執行 Retraining**")
        for msg in triggered:
            st.markdown(f"- {msg}")
    else:
        st.success(
            f"🟢 **模型狀態正常，暫不需 Retraining**　"
            f"（未用修正 {unused_count} 筆 ｜ 待審核率 {_review_r:.1%}）"
        )
