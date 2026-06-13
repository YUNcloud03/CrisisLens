"""CrisisLens — 災情圖文分類與應變建議系統。"""
# ── 壓制 transformers 棄用警告（不影響功能）────────────────────
# 必須在任何 import 之前設定環境變數，才能在 transformers 載入時生效
import os
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")      # transformers 自身日誌等級
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")      # 避免 tokenizers fork 警告

import warnings
# warnings 模組層面：過濾任何含 __path__ 的 UserWarning / FutureWarning
warnings.filterwarnings("ignore", message=r".*__path__.*")
warnings.filterwarnings("ignore", message=r".*Accessing.*", module=r"transformers.*")
warnings.filterwarnings("ignore", category=FutureWarning,    module=r"transformers.*")
warnings.filterwarnings("ignore", category=UserWarning,      module=r"transformers.*")

import logging
# logging 模組層面：transformers 的 warning_once() 走 logging，需在此過濾
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
# ─────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import json
import os
import sys
import uuid
from datetime import datetime

try:
    from streamlit_js_eval import get_geolocation as _get_geo
    _HAS_GEO = True
except ImportError:
    _HAS_GEO = False

sys.path.insert(0, os.path.dirname(__file__))

from aggregation.event_matcher import _derive_grid_id, aggregate
from aggregation.h3_utils import DEFAULT_RESOLUTION, latlng_to_h3_cell
from aggregation.scoring import calc_report_severity
from db.database import init_db
from db.queries import insert_model_run, insert_report, update_model_run_report, count_recent_reports_by_user
from utils.auth import require_login
from utils.image_utils import load_image, resize_for_display
from utils.config import CLASSES_ZH, PROMPT_SETS, GEMINI_API_KEY
from utils.ui_theme import apply_theme, empty_state, page_header, top_pill
from utils.versions import (
    AGGREGATION_RULE_VERSION,
    CLIP_LOW_CONF_THRESHOLD,
    CLIP_TOP2_GAP_THRESHOLD,
    CLIP_MODEL_VERSION,
    CLIP_PROMPT_VERSION,
    EFFNET_MODEL_VERSION,
    PRIORITY_RULE_VERSION,
    RAG_INDEX_VERSION,
    RAG_PROMPT_VERSION,
)
from rag.retriever import index_exists

init_db()

# ── 頁面設定 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="CrisisLens｜災情分類系統",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
user = require_login()

st.session_state.pop("just_logged_in", None)
if user.get("role") == "admin" and user.get("permission_status") == "approved":
    st.switch_page("pages/2_Event_Dashboard.py")

from utils.storage import save_image as _save_image

if "gps_approved" not in st.session_state:
    st.session_state["gps_approved"] = False


# ═══════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════
def confidence_bar(score: float, bar_class: str = "bar-blue") -> str:
    pct = int(score * 100)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
        f'<div class="bar-bg" style="flex:1">'
        f'<div class="{bar_class}" style="width:{pct}%"></div></div>'
        f'<span style="font-size:0.8rem;color:#94a3b8;width:38px;text-align:right">{pct}%</span>'
        f'</div>'
    )


def score_to_bar_class(score: float) -> str:
    if score >= 0.7: return "bar-high"
    if score >= 0.4: return "bar-medium"
    return "bar-low"


def score_to_risk_class(score: float) -> str:
    if score >= 0.7: return "risk-high"
    if score >= 0.4: return "risk-medium"
    return "risk-low"


def render_browser_geolocation_button() -> None:
    """GPS 定位按鈕：使用 streamlit_js_eval 避免 iframe 跨域導航問題。"""
    if not _HAS_GEO:
        st.warning("請安裝 streamlit-js-eval：`pip install streamlit-js-eval`")
        return

    if not st.session_state.get("gps_approved"):
        if st.button("取得目前 GPS 定位", use_container_width=True, key="gps_btn"):
            st.session_state["gps_approved"] = True
            st.rerun()
        return

    st.caption("瀏覽器會彈出授權視窗，請點選「允許」。若瀏覽器封鎖定位，可點「✖ 取消」改用手動輸入。")
    geo = _get_geo()

    if geo and isinstance(geo, dict) and geo.get("coords"):
        lat = geo["coords"]["latitude"]
        lng = geo["coords"]["longitude"]
        acc = geo["coords"].get("accuracy", "?")
        st.session_state["report_latitude"]  = lat
        st.session_state["report_longitude"] = lng
        st.session_state["latitude_input"]   = lat
        st.session_state["longitude_input"]  = lng
        st.session_state["gps_status"]       = f"已取得 GPS 定位（精確度 ±{acc:.0f}m）"
        st.session_state["gps_approved"]     = False
        st.rerun()
    elif geo and isinstance(geo, dict) and geo.get("error"):
        # 瀏覽器明確拒絕或發生錯誤
        err_msg = geo.get("error", {})
        code = err_msg.get("code", "") if isinstance(err_msg, dict) else ""
        if code == 1:
            st.warning("瀏覽器定位已被拒絕（Permission Denied）。請切換為「手動輸入座標 / 僅填行政區」。")
        else:
            st.warning("無法取得 GPS 定位（可能逾時或環境不支援）。請切換為「手動輸入座標 / 僅填行政區」。")
        st.session_state["gps_approved"] = False
        st.rerun()
    else:
        # geo = None 表示瀏覽器還在等待授權，讓 component 拿到結果後自動 rerun
        st.info("等待瀏覽器回應定位授權……")
        if st.button("✖ 取消定位", key="gps_cancel"):
            st.session_state["gps_approved"] = False
            st.rerun()


def render_model_card(title: str, result: dict):
    conf      = result["confidence"]
    zh        = result["top_class_zh"]
    top3      = result["top_3"]
    rclass    = score_to_risk_class(conf)

    card_html = f"""
    <div class="metric-card">
      <div class="score-label">{title}</div>
      <div class="score-value {rclass}">{zh}</div>
      <div class="score-sub">信心度 {conf:.1%}</div>
      {confidence_bar(conf, score_to_bar_class(conf))}
    </div>
    <div style="margin-bottom:8px;font-size:0.8rem;color:#475569;text-transform:uppercase;letter-spacing:0.06em">
      Top-3 類別
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    for item in top3:
        c = item["score"]
        st.markdown(f"""
        <div style="margin:4px 0">
          <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:2px">
            <span style="color:#e2e8f0">{item['class_zh']}</span>
            <span style="color:#94a3b8">{c:.1%}</span>
          </div>
          {confidence_bar(c, score_to_bar_class(c))}
        </div>
        """, unsafe_allow_html=True)


def render_ai_summary_card(title: str, result: dict) -> None:
    st.markdown(
        f"""
        <div class="cl-ai-result">
          <div class="cl-ai-icon">≋</div>
          <div style="flex:1;min-width:0">
            <div class="cl-stat-label">{title}</div>
            <div style="font-size:1.08rem;font-weight:900">{result['top_class_zh']}</div>
            <div class="cl-card-note">Confidence 信心度：{result['confidence']:.1%}</div>
            {confidence_bar(result['confidence'], score_to_bar_class(result['confidence']))}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_rag_result(rag_result: dict, disaster_type_zh: str):
    if rag_result["used_llm"]:
        badge = '<span style="font-size:0.72rem;color:#4ade80;margin-left:8px">✨ Gemini LLM</span>'
    elif rag_result["used_rag"]:
        badge = '<span style="font-size:0.72rem;color:#38bdf8;margin-left:8px">📚 RAG 檢索</span>'
    else:
        badge = '<span style="font-size:0.72rem;color:#94a3b8;margin-left:8px">📋 內建指引</span>'

    st.markdown(f"""
    <div style="display:flex;align-items:center;margin-bottom:12px">
      <span style="color:#e2e8f0;font-weight:600">針對「{disaster_type_zh}」的應變建議</span>
      {badge}
    </div>
    """, unsafe_allow_html=True)

    for line in rag_result["advice"]:
        clean = line.lstrip("・•-").strip()
        if clean:
            st.markdown(f'<div class="advice-item">・{clean}</div>', unsafe_allow_html=True)

    if rag_result["sources"]:
        badges_html = "".join(
            f'<span class="source-badge">{s}</span>' for s in rag_result["sources"]
        )
        st.markdown(
            f'<div style="margin-top:12px;font-size:0.75rem;color:#94a3b8">來源：{badges_html}</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("---")
    st.markdown("### ⚙️ 模型設定")
    model_mode = st.selectbox(
        "使用模型",
        [
            "雙主投票 (CLIP linear-probe + EfficientNet-B0)",
            "CLIP linear-probe",
            "CLIP ViT-L/14 (zero-shot)",
            "EfficientNet-B0",
        ],
        help="「雙主投票」同時執行 CLIP 與 EfficientNet-B0：一致→高信心；不一致→need_review 並取信心較高者。"
             "CLIP 預設走 linear-probe，權重未就緒時自動退回 zero-shot。",
    )
    # 注意：選項標籤以子字串編碼行為（同 _USE_CLIP/_USE_EFFNET）。
    # 兩個 probe 選項的標籤都必須含 "linear-probe"，否則改這裡的判斷。
    _prefer_probe = "linear-probe" in model_mode

    prompt_set_key = list(PROMPT_SETS.keys())[1]  # B 預設（單 prompt 比較用）

    st.markdown("---")
    st.markdown("### 📋 系統狀態")
    if index_exists():
        st.success("✅ FAISS index 已建立")
    else:
        st.warning("⚠️ 尚未建立 FAISS index\n```\npython rag/build_index.py\n```")

    if GEMINI_API_KEY:
        st.success("✅ Gemini API 已設定")
    else:
        st.info("未設定 GEMINI_API_KEY\n將使用內建指引")

    try:
        from safety.shieldgemma_guard import safety_backend_status
        _safety_status = safety_backend_status()
        if _safety_status["local_shieldgemma_enabled"]:
            st.info(
                "🛡️ Safety Guard：Keyword + Gemini + ShieldGemma\n"
                f"`{_safety_status['local_shieldgemma_model']}`"
            )
        elif _safety_status["gemini"]:
            st.info("🛡️ Safety Guard：Keyword + Gemini")
        else:
            st.warning("🛡️ Safety Guard：Keyword fallback")
    except Exception:
        st.warning("🛡️ Safety Guard：狀態讀取失敗")

    st.markdown("---")
    st.caption("v2.1 · CLIP ViT-L/14 + EfficientNet-B0 雙主投票 + RAG")


# ═══════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════
analysis = st.session_state.get("citizen_analysis")
if analysis and analysis.get("model_mode") != model_mode:
    st.session_state.pop("citizen_analysis", None)
    analysis = None

# 模式旗標（集中管理，避免散落多處的字串比對）
# 「雙主投票 (CLIP + EfficientNet-B0)」同時包含兩個關鍵字 → 兩旗標皆 True
_USE_CLIP   = "CLIP"         in model_mode
_USE_EFFNET = "EfficientNet" in model_mode

# ── 輸入區 ────────────────────────────────────────────────────
left_col, right_col = st.columns([1.05, 0.95], gap="large")

with left_col:
    top_pill(2, "民眾端 - 災情回報頁面", "Citizen Portal")
    st.markdown(
        """
        <section class="cl-inline-header">
          <div class="cl-kicker">Citizen Portal</div>
          <h1 class="cl-title">災情回報</h1>
          <div class="cl-subtitle">上傳災害照片，AI 會先辨識災害種類並提供基本防災建議；確認後再送出回報。</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cl-panel-title">災情回報</div>', unsafe_allow_html=True)
    st.markdown('<div class="cl-panel-title">1. 上傳災害照片</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "支援 JPG、PNG、WEBP",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )
    if uploaded_file:
        img_preview = load_image(uploaded_file)
        st.image(resize_for_display(img_preview), use_container_width=True)

    st.markdown('<div class="cl-panel-title">2. 位置授權</div>', unsafe_allow_html=True)
    gps_mode = st.radio(
        "是否允許取得目前 GPS 定位？",
        ["詢問瀏覽器定位", "手動輸入座標 / 僅填行政區"],
        horizontal=True,
        label_visibility="visible",
    )
    if gps_mode == "詢問瀏覽器定位":
        st.caption("按下按鈕後，瀏覽器會詢問是否允許取得目前位置；若拒絕授權，仍可手動輸入座標或只填行政區。")
        render_browser_geolocation_button()
        if st.session_state.get("gps_status"):
            st.success(st.session_state["gps_status"])

    st.markdown('<div class="cl-panel-title">3. 災情資訊確認</div>', unsafe_allow_html=True)
    user_desc = st.text_area(
        "描述",
        placeholder="例如：道路旁有大量積水，無法通行...",
        height=110,
    )
    location_name = st.text_input("地點名稱", placeholder="例如：信義路五段100號附近")
    city_col, district_col = st.columns(2)
    with city_col:
        city = st.selectbox("縣市", ["","台北市","新北市","桃園市","台中市","台南市","高雄市",
                                     "基隆市","新竹市","新竹縣","苗栗縣","彰化縣","南投縣",
                                     "雲林縣","嘉義市","嘉義縣","屏東縣","宜蘭縣","花蓮縣",
                                     "台東縣","澎湖縣","金門縣","連江縣"])
    with district_col:
        district = st.text_input("行政區", placeholder="例如：信義區")
    gps_col1, gps_col2 = st.columns(2)
    with gps_col1:
        latitude = st.number_input(
            "緯度（選填）",
            value=float(st.session_state.get("report_latitude", 0.0)),
            format="%.6f",
            key="latitude_input",
        )
    with gps_col2:
        longitude = st.number_input(
            "經度（選填）",
            value=float(st.session_state.get("report_longitude", 0.0)),
            format="%.6f",
            key="longitude_input",
        )
    st.markdown('<div class="cl-step-label">現場狀況</div>', unsafe_allow_html=True)
    need_help = st.checkbox("需要協助")
    ppl_count = st.number_input("大約需要協助人數", min_value=0, max_value=999, value=0)
    has_trapped = st.checkbox("有人受困")
    has_injured = st.checkbox("有人受傷")
    road_blocked = st.checkbox("道路不可通行")
    power_outage = st.checkbox("停電")
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("AI 辨識並產生建議", use_container_width=True)

with right_col:
    if latitude != 0.0 and longitude != 0.0:
        import pandas as pd
        st.caption("📍 回報位置預覽")
        st.map(pd.DataFrame({"lat": [latitude], "lon": [longitude]}), zoom=14, use_container_width=True)
        loc_label = f"{city}{district}".strip() or "未填地點"
        preview_h3 = None
        try:
            preview_h3 = latlng_to_h3_cell(latitude, longitude)
        except Exception:
            pass
        st.caption(f"{loc_label}　{latitude:.6f}, {longitude:.6f}")
        if preview_h3:
            st.caption(f"H3 Cell：`{preview_h3}`")
    else:
        st.markdown(
            """
            <div class="cl-location-empty">
              <strong>尚未提供 GPS 座標</strong>
              <span>可先填寫地點名稱與行政區，送出時仍會保留回報資料。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('<div style="height:.85rem"></div>', unsafe_allow_html=True)
    if analysis:
        clip_preview   = analysis.get("clip_result")
        second_preview = analysis.get("effnet_result")
        second_label   = "EfficientNet-B0"
        primary_preview = analysis["primary"]
        m_agree  = analysis.get("model_agreement", 1)
        n_review = analysis.get("need_review", 0)
        gap_val  = analysis.get("clip_top2_gap", 1.0)

        st.markdown('<div class="cl-panel-title">AI 辨識結果</div>', unsafe_allow_html=True)
        if "雙主" in analysis.get("model_mode", "") and clip_preview and second_preview:
            _c1, _c2 = st.columns(2)
            with _c1:
                render_ai_summary_card("CLIP ViT-L/14", clip_preview)
            with _c2:
                render_ai_summary_card(second_label, second_preview)
        else:
            render_ai_summary_card("主要辨識結果", primary_preview)

        # ── model_agreement & need_review badges ────────────
        if clip_preview and second_preview:
            _agree_color = "#4ade80" if m_agree else "#fb923c"
            _agree_icon  = "✅" if m_agree else "⚠️"
            _agree_text  = "模型一致（model_agreement = 1）" if m_agree else "模型不一致（model_agreement = 0）"
            st.markdown(
                f'<div style="margin:8px 0 4px;padding:7px 12px;border-radius:6px;'
                f'background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);'
                f'font-size:.82rem;display:flex;gap:18px;align-items:center">'
                f'<span style="color:{_agree_color};font-weight:700">{_agree_icon} {_agree_text}</span>'
                f'<span style="color:#94a3b8">Top-2 gap：{gap_val:.1%}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if n_review:
            st.markdown(
                '<div style="margin-bottom:10px;padding:7px 12px;border-radius:6px;'
                'background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.35);'
                'font-size:.82rem;color:#fbbf24;font-weight:600">'
                '🔍 need_review = 1 — AI 信心度不足或兩模型結果不一致，建議人工確認</div>',
                unsafe_allow_html=True,
            )

        # ── Safety Guard 結果卡片（三層防護可視化）────────────
        _in_s   = analysis.get("input_safety",  {})
        _img_s  = analysis.get("image_safety",  {})
        _out_s  = analysis.get("output_safety", {})

        def _safety_label_html(label: str, method: str) -> str:
            _label_map  = {"safe": ("✅ 安全", "#4ade80"), "review": ("🔍 需審查", "#fbbf24"),
                           "sanitize": ("🔧 已淨化", "#fb923c"), "block": ("🚫 封鎖", "#f87171")}
            _method_map = {"keyword": "關鍵字規則", "gemini": "Gemini API",
                           "shieldgemma": "ShieldGemma 本地", "gemini_vision": "Gemini Vision",
                           "skip": "略過（空白）"}
            lbl_text, lbl_color = _label_map.get(label, (label or "—", "#94a3b8"))
            mth_text = _method_map.get(method, method or "—")
            return (
                f'<span style="color:{lbl_color};font-weight:700">{lbl_text}</span>'
                f'<span style="color:#64748b;font-size:.75rem;margin-left:4px">({mth_text})</span>'
            )

        _sg_rows = [
            ("📝 文字輸入", _in_s.get("label","safe"),  _in_s.get("method","keyword")),
            ("🖼️ 圖片內容", _img_s.get("label","safe"), _img_s.get("method","skip")),
            ("📋 建議輸出", _out_s.get("label","safe"),  _out_s.get("method","keyword")),
        ]
        _sg_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:3px 0;border-bottom:1px solid rgba(255,255,255,.05)">'
            f'<span style="color:#94a3b8;font-size:.8rem">{name}</span>'
            f'{_safety_label_html(lbl, mth)}</div>'
            for name, lbl, mth in _sg_rows
        )
        st.markdown(
            f'<div style="margin:10px 0 14px;padding:10px 14px;border-radius:8px;'
            f'background:rgba(56,189,248,.05);border:1px solid rgba(56,189,248,.2)">'
            f'<div style="font-size:.78rem;font-weight:700;color:#38bdf8;margin-bottom:6px">'
            f'🛡️ ShieldGemma 3-層安全檢查結果</div>'
            f'{_sg_html}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="cl-panel-title">AI 防災建議</div>', unsafe_allow_html=True)
        render_rag_result(analysis["rag_result"], primary_preview["top_class_zh"])
        st.markdown("""
        <div class="safety-box" style="margin-top:14px">
          ⚠️ <strong>AI Safety 提醒</strong><br>
          本系統分類與建議僅供初步參考，不代表官方災害判定。<br>
          若有立即危險，請<strong>優先撥打 119 / 110</strong>。
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div class="cl-location-empty" style="min-height:180px">
              <strong>尚未進行 AI 辨識</strong>
              <span>上傳照片並按下「AI 辨識並產生建議」後，才會顯示災害類型與防災建議。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<hr>", unsafe_allow_html=True)

# ── 分析邏輯 ──────────────────────────────────────────────────
if analyze_btn:
    if not uploaded_file:
        st.error("請先上傳災情照片。")
        st.stop()

    # 重新讀取圖片（file_uploader 可能已 seek 到底）
    uploaded_file.seek(0)
    img = load_image(uploaded_file)

    # ── Safety: Input Guard（描述文字）──────────────────────
    from safety.shieldgemma_guard import (
        check_user_input, check_image_safety,
        check_rag_output, sanitize_advice, safety_summary,
    )
    _input_check = check_user_input(user_desc)
    if _input_check["blocked"]:
        st.error(
            f"⚠️ 您的描述含有不允許的內容，請修改後重新送出。\n"
            f"原因：{_input_check['reason']}"
        )
        st.stop()
    if _input_check["label"] == "review":
        st.warning("⚠️ 描述中偵測到敏感資訊，此回報將標記為需人工審查。")

    # ── Safety: Image Guard（Gemini Vision，有 key 才執行）──
    _image_check = check_image_safety(img)
    if _image_check["blocked"]:
        st.error("⚠️ 上傳的圖片含有不允許的內容，請換一張照片。")
        st.stop()

    clip_result   = None
    effnet_result = None

    import time as _time
    _infer_t0 = _time.perf_counter()
    with st.spinner("模型推論中..."):
        # ── CLIP ViT-L/14（linear-probe 優先，否則 zero-shot 多 prompt 平均）──
        if _USE_CLIP:
            from models.clip_classifier import classify_clip
            clip_result = classify_clip(img, prefer_probe=_prefer_probe)

        # ── EfficientNet-B0（v2 微調，5 類，雙主投票第二主）──
        if _USE_EFFNET:
            try:
                from models.efficientnet_classifier import classify as effnet_classify, weights_exist
                if weights_exist():
                    effnet_result = effnet_classify(img)
                else:
                    st.warning("⚠️ 找不到 EfficientNet 權重，請確認 models/efficientnet_b0_5class_v2.pth 存在。")
            except Exception as _e:
                from utils.logger import log_error
                log_error("effnet_classify", str(_e), exc_info=True,
                          username=user.get("username"))
                st.warning("⚠️ EfficientNet-B0 載入失敗，本次僅以 CLIP 結果為準。")
    _inference_ms = round((_time.perf_counter() - _infer_t0) * 1000, 1)

    if clip_result is not None and _USE_CLIP:
        _m = clip_result.get("method", "zero_shot")
        if _prefer_probe and _m == "zero_shot":
            st.caption("ℹ️ linear probe 權重未就緒，已退回 zero-shot CLIP")
        else:
            _label = {"linear_probe": "CLIP：linear-probe（MEDIC 6→5）",
                      "zero_shot": "CLIP：zero-shot 多 prompt"}.get(_m, _m)
            st.caption(f"🔎 {_label}")

    if clip_result is None and effnet_result is None:
        st.error("模型推論失敗，請稍後再試。")
        st.stop()

    # ── 雙主投票：一致→高信心；不一致→need_review、primary 取信心高者 ──
    _model_agreement = 1
    if clip_result and effnet_result:
        if effnet_result.get("top_class_zh") != clip_result.get("top_class_zh"):
            _model_agreement = 0
        primary = max(clip_result, effnet_result, key=lambda r: r["confidence"])
    else:
        primary = clip_result or effnet_result

    _top3_for_gap = (clip_result or effnet_result).get("top_3", [])
    _clip_gap     = (_top3_for_gap[0]["score"] - _top3_for_gap[1]["score"]
                     if len(_top3_for_gap) >= 2 else 1.0)
    _need_review  = int(
        primary["confidence"] < CLIP_LOW_CONF_THRESHOLD
        or _clip_gap          < CLIP_TOP2_GAP_THRESHOLD
        or _model_agreement   == 0
    )

    with st.spinner("生成建議..."):
        from rag.generator import generate_advice
        rag_result = generate_advice(
            disaster_type_zh=primary["top_class_zh"],
            confidence=primary["confidence"],
            user_description=user_desc,
            location=f"{city}{district}{location_name}",
        )

    # ── Safety: Output Guard（RAG 建議）─────────────────────
    _output_check = check_rag_output(rag_result["advice"])
    if _output_check["label"] == "sanitize":
        rag_result["advice"] = sanitize_advice(rag_result["advice"])
    elif _output_check["label"] == "block":
        # 極端情況：整批替換
        from safety.policies import SANITIZED_REPLACEMENT
        rag_result["advice"] = [SANITIZED_REPLACEMENT]

    st.session_state["citizen_analysis"] = {
        "clip_result":       clip_result,
        "effnet_result":     effnet_result,
        "primary":           primary,
        "rag_result":        rag_result,
        "model_mode":        model_mode,
        "model_agreement":   _model_agreement,
        "need_review":       _need_review,
        "clip_top2_gap":     _clip_gap,
        "input_safety":      _input_check,
        "output_safety":     _output_check,
        "image_safety":      _image_check,
    }
    st.rerun()

elif not analysis:
    empty_state("上傳照片後點擊「AI 辨識並產生建議」", "系統將自動辨識災害類型並提供應變建議。", "🖼️")

if analysis and uploaded_file:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### 送出災情回報")
    st.caption("管理端會依災害群組與地點距離聚合事件，並依 Priority Score 排序。")

    # ── 速率限制：每用戶每小時最多 10 筆回報 ─────────────────
    _RATE_LIMIT = 10
    _RATE_WINDOW_MIN = 60
    _recent_count = count_recent_reports_by_user(user["username"], minutes=_RATE_WINDOW_MIN)
    if _recent_count >= _RATE_LIMIT:
        st.error(
            f"⚠️ 您在過去 {_RATE_WINDOW_MIN} 分鐘內已送出 {_recent_count} 筆回報，"
            f"超過每小時上限（{_RATE_LIMIT} 筆）。\n請稍後再試，或聯絡管理員。"
        )
        st.stop()

    if st.button("送出災情回報", use_container_width=True):
        uploaded_file.seek(0)
        img = load_image(uploaded_file)
        fname = f"{uuid.uuid4().hex}.jpg"
        fpath = _save_image(img, fname)

        primary       = analysis["primary"]
        clip_result   = analysis.get("clip_result") or primary
        effnet_result = analysis.get("effnet_result")
        # 用於 DB：第二主模型 = EfficientNet-B0（沿用 resnet_* 欄位，免 schema migration）
        _aux_result   = effnet_result
        rag_result    = analysis["rag_result"]

        # ── Safety labels（從 analyze 階段帶入）──────────────
        _in_safety  = analysis.get("input_safety",  {})
        _out_safety = analysis.get("output_safety", {})
        from safety.shieldgemma_guard import safety_summary
        _safety_reason = safety_summary(_in_safety, _out_safety) or None

        has_gps = latitude != 0.0 and longitude != 0.0
        lat_val = float(latitude) if has_gps else None
        lng_val = float(longitude) if has_gps else None
        try:
            h3_val = latlng_to_h3_cell(lat_val, lng_val) if has_gps else None
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()

        # ── 自動補地名（有 GPS 但無 city/district 時反向地理編碼）────
        geo_city     = city     or ""
        geo_district = district or ""
        geo_location = location_name or ""
        if has_gps and not (geo_city and geo_district):
            try:
                from utils.geocoding import reverse_geocode
                geo_info = reverse_geocode(lat_val, lng_val)
                if not geo_city:
                    geo_city = geo_info.get("city", "") or ""
                if not geo_district:
                    geo_district = geo_info.get("district", "") or ""
                if not geo_location and geo_info.get("display_name"):
                    geo_location = geo_info["display_name"]
            except Exception as _e:
                from utils.logger import log_error
                log_error("geocoding", str(_e), exc_info=True)

        grid_id, grid_type_val = _derive_grid_id({
            "h3_cell": h3_val,
            "city": geo_city or None,
            "district": geo_district or None,
        })

        report_base = {
            "has_injured_people": int(has_injured),
            "has_trapped_people": int(has_trapped),
            "road_blocked": int(road_blocked),
            "power_outage": int(power_outage),
            "need_help": int(need_help),
            "reported_people_count": int(ppl_count),
            "disaster_type": primary["top_class"],
            "clip_confidence": primary["confidence"],
        }
        sev_score, sev_level = calc_report_severity(report_base)

        # 使用分析階段已計算的值（避免重算）
        model_agreement  = analysis.get("model_agreement", 1)
        need_review_flag = analysis.get("need_review", 0)

        # model_run 版本記錄（第二主 = EfficientNet-B0；欄位名沿用 resnet_*）
        _aux_ver = EFFNET_MODEL_VERSION if effnet_result else None

        now = datetime.now().isoformat(timespec="seconds")
        run_id = insert_model_run({
            "run_time": now,
            "trigger": "submit",
            "clip_model_version": CLIP_MODEL_VERSION,
            "clip_prompt_version": CLIP_PROMPT_VERSION,
            "resnet_model_version": _aux_ver,
            "rag_index_version": RAG_INDEX_VERSION,
            "rag_prompt_version": RAG_PROMPT_VERSION,
            "aggregation_rule_version": AGGREGATION_RULE_VERSION,
            "priority_rule_version": PRIORITY_RULE_VERSION,
            "report_id": None,
            "notes": f"submitted_by={user['username']}",
            "inference_latency_ms": _inference_ms,
        })

        full_report = {
            "event_id": None,
            "image_path": fpath,
            "description": user_desc,
            "location_name": geo_location or None,
            "city": geo_city or None,
            "district": geo_district or None,
            "latitude": lat_val,
            "longitude": lng_val,
            "location_source": "gps" if has_gps else "manual",
            "h3_cell": h3_val,
            "h3_resolution": DEFAULT_RESOLUTION if h3_val else None,
            "grid_id": grid_id,
            "grid_type": grid_type_val,
            "event_time": now,
            "upload_time": now,
            "clip_model_version": CLIP_MODEL_VERSION,
            "clip_prompt_version": CLIP_PROMPT_VERSION,
            "clip_disaster_type": primary["top_class"],
            "clip_confidence": primary["confidence"],
            "clip_top3": json.dumps(top3, ensure_ascii=False),
            "top3_predictions": json.dumps(top3, ensure_ascii=False),
            # resnet_* 欄位自 v2.1 起存放第二主模型（EfficientNet-B0）結果
            "resnet_model_version": _aux_ver,
            "resnet_disaster_type": _aux_result["top_class"] if _aux_result else None,
            "resnet_confidence":    _aux_result["confidence"] if _aux_result else None,
            "disaster_type": primary["top_class"],
            "model_agreement": model_agreement,
            "need_review": need_review_flag,
            "need_help": int(need_help),
            "reported_people_count": int(ppl_count),
            "has_trapped_people": int(has_trapped),
            "has_injured_people": int(has_injured),
            "road_blocked": int(road_blocked),
            "power_outage": int(power_outage),
            "report_severity_score": sev_score,
            "report_severity_level": sev_level,
            "rag_version": RAG_PROMPT_VERSION,
            "rag_advice": json.dumps(rag_result["advice"], ensure_ascii=False),
            "rag_sources": json.dumps(rag_result["sources"], ensure_ascii=False),
            "model_run_id": run_id,
            "aggregation_rule_version": AGGREGATION_RULE_VERSION,
            "priority_rule_version": PRIORITY_RULE_VERSION,
            # Safety guard 結果
            "input_safety_label":  _in_safety.get("label", "safe"),
            "output_safety_label": _out_safety.get("label", "safe"),
            "safety_reason":       _safety_reason,
            # 提交者（速率限制 / 稽核用）
            "submitted_by":        user["username"],
        }

        report_id = insert_report(full_report)
        update_model_run_report(run_id, report_id)
        agg = aggregate(full_report, report_id)
        st.session_state.pop("citizen_analysis", None)
        st.success(f"已送出回報，事件 #{agg['event_id']}，優先級 {agg['event_priority_level']}。")
