"""CrisisLens — 災情圖文分類與應變建議系統。"""
# ── 壓制 transformers __path__ 棄用警告（不影響功能）──────────
import warnings
warnings.filterwarnings("ignore", message=".*__path__.*")

import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
# ─────────────────────────────────────────────────────────────

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from utils.image_utils import load_image, resize_for_display
from utils.config import CLASSES_ZH, PROMPT_SETS, GEMINI_API_KEY
from utils.ui_theme import apply_theme
from rag.retriever import index_exists

# ── 頁面設定 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="CrisisLens｜災情分類系統",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ── Dark Theme CSS ────────────────────────────────────────────
st.markdown("""
<style>
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background-color: #080d1a !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] {
    background-color: #0a1220 !important;
    border-right: 1px solid rgba(30,64,120,0.45);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
h1, h2, h3, h4 { color: #e2e8f0 !important; }

.metric-card {
    background: #0d1628;
    border: 1px solid rgba(30,64,120,0.45);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.metric-card:hover { border-color: rgba(56,189,248,0.35); }

.score-label { font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.07em; }
.score-value { font-size:2rem; font-weight:800; color:#38bdf8; line-height:1.1; }
.score-sub   { font-size:0.85rem; color:#94a3b8; margin-top:4px; }

.risk-high   { color:#f87171 !important; }
.risk-medium { color:#fbbf24 !important; }
.risk-low    { color:#4ade80 !important; }

.advice-item {
    background: rgba(56,189,248,0.06);
    border-left: 3px solid #38bdf8;
    padding: 8px 12px;
    margin: 6px 0;
    border-radius: 0 6px 6px 0;
    color: #e2e8f0;
    font-size: 0.9rem;
    line-height: 1.6;
}
.source-badge {
    display:inline-block;
    background:rgba(56,189,248,0.12);
    border:1px solid rgba(56,189,248,0.3);
    color:#38bdf8;
    font-size:0.72rem;
    padding:2px 8px;
    border-radius:999px;
    margin:2px 4px 2px 0;
}
.bar-bg { background:rgba(255,255,255,0.06); border-radius:999px; height:8px; overflow:hidden; }
.bar-high   { height:8px; border-radius:999px; background:linear-gradient(90deg,#dc2626,#f87171); }
.bar-medium { height:8px; border-radius:999px; background:linear-gradient(90deg,#d97706,#fbbf24); }
.bar-low    { height:8px; border-radius:999px; background:linear-gradient(90deg,#16a34a,#4ade80); }
.bar-blue   { height:8px; border-radius:999px; background:linear-gradient(90deg,#0284c7,#38bdf8); }

.safety-box {
    background: rgba(220,38,38,0.08);
    border: 1px solid rgba(248,113,113,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 16px;
    font-size: 0.82rem;
    color: #fca5a5;
    line-height: 1.7;
}
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(30,64,120,0.6) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}
div.stButton > button {
    background: linear-gradient(135deg,#0284c7,#38bdf8) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    box-shadow: 0 0 16px rgba(56,189,248,0.25) !important;
    width: 100%;
}
div.stButton > button:hover { opacity: 0.9 !important; }
hr { border-color: rgba(30,64,120,0.45) !important; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


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


def render_model_card(title: str, result: dict):
    conf      = result["confidence"]
    zh        = result["top_class_zh"]
    top3      = result["top_3"]
    rclass    = score_to_risk_class(conf)

    src       = result.get("prompt_source")
    src_html  = (f'<div style="font-size:0.7rem;color:#64748b;margin-top:4px">'
                 f'Prompt：{src}</div>') if src else ""

    card_html = f"""
    <div class="metric-card">
      <div class="score-label">{title}</div>
      <div class="score-value {rclass}">{zh}</div>
      <div class="score-sub">信心度 {conf:.1%}</div>
      {confidence_bar(conf, score_to_bar_class(conf))}
      {src_html}
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
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px">
      <div style="width:36px;height:36px;background:rgba(56,189,248,0.15);
                  border:1px solid rgba(56,189,248,0.3);border-radius:8px;
                  display:flex;align-items:center;justify-content:center;
                  font-weight:800;font-size:0.9rem;color:#38bdf8">CL</div>
      <div>
        <div style="font-weight:700;font-size:1rem;color:#e2e8f0">CrisisLens</div>
        <div style="font-size:0.7rem;color:#475569">災情分類與應變建議</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ 模型設定")
    model_mode = st.selectbox(
        "使用模型",
        ["CLIP（Zero-Shot）", "ResNet50（Baseline）", "兩者比較"],
    )

    from models.clip_classifier import linear_probe_available
    MULTI_PROMPT_OPTION  = "D｜多描述投票版（推薦）"
    LINEAR_PROBE_OPTION  = "E｜Linear Probe（MEDIC訓練）"
    _clip_options = [MULTI_PROMPT_OPTION] + list(PROMPT_SETS.keys())
    if linear_probe_available():
        _clip_options = [LINEAR_PROBE_OPTION] + _clip_options   # 有訓練權重才顯示，且設為首選

    prompt_set_key = _clip_options[0]  # 預設
    if "CLIP" in model_mode or "比較" in model_mode:
        prompt_set_key = st.selectbox(
            "CLIP Prompt Set",
            _clip_options,
            index=0,
            help="E=訓練分類器（最準，需權重）、D=多描述投票（Gemini）、A/B/C=zero-shot prompt",
        )

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

    st.markdown("---")
    st.caption("v1.0 · CLIP + ResNet50 + RAG")


# ═══════════════════════════════════════════════════
# Main Page
# ═══════════════════════════════════════════════════
st.markdown("""
<section class="cl-hero">
  <div>
    <div class="cl-kicker">CrisisLens AI</div>
    <h1 class="cl-title">災情圖文分類與應變建議系統</h1>
    <div class="cl-subtitle">
      上傳災情照片，系統自動分類災害類型並提供應變建議。
    </div>
  </div>
</section>
<hr>
""", unsafe_allow_html=True)

# ── 輸入區 ────────────────────────────────────────────────────
col_upload, col_meta = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("#### 📷 上傳災情照片")
    uploaded_file = st.file_uploader(
        "支援 JPG、PNG、WEBP",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )
    if uploaded_file:
        img_preview = load_image(uploaded_file)
        st.image(resize_for_display(img_preview), use_container_width=True)

with col_meta:
    st.markdown("#### 📝 補充資訊（選填）")
    user_desc = st.text_area(
        "描述",
        placeholder="例如：道路旁有大量積水，無法通行...",
        height=110,
        label_visibility="collapsed",
    )
    location = st.text_input(
        "地點",
        placeholder="例如：台北市信義區...",
        label_visibility="collapsed",
    )
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 開始分析", use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── 分析邏輯 ──────────────────────────────────────────────────
if analyze_btn:
    if not uploaded_file:
        st.error("請先上傳災情照片。")
        st.stop()

    # 重新讀取圖片（file_uploader 可能已 seek 到底）
    uploaded_file.seek(0)
    img = load_image(uploaded_file)

    clip_result   = None
    resnet_result = None

    with st.spinner("模型推論中..."):
        if "CLIP" in model_mode or "比較" in model_mode:
            from models.clip_classifier import (
                classify as clip_classify, classify_multi_prompt, classify_linear_probe,
            )
            if prompt_set_key.startswith("E"):
                clip_result = classify_linear_probe(img)          # MEDIC 訓練的分類器
            elif prompt_set_key.startswith("D"):
                clip_result = classify_multi_prompt(img)          # 多描述投票 + Gemini prompt
            else:
                clip_result = clip_classify(img, prompt_set_key)  # 舊單 prompt（A/B/C 比較用）

        if "ResNet50" in model_mode or "比較" in model_mode:
            from models.resnet_baseline import classify as resnet_classify
            resnet_result = resnet_classify(img)

    primary = clip_result or resnet_result

    # ── 模型結果 ───────────────────────────────────────────
    st.markdown("## 📊 分類結果")

    if "比較" in model_mode and clip_result and resnet_result:
        mc1, mc2 = st.columns(2)
        with mc1:
            render_model_card("CLIP Zero-Shot", clip_result)
        with mc2:
            loaded_label = "✅ 已訓練" if resnet_result["model_loaded"] else "⚠️ 未訓練（隨機）"
            render_model_card(f"ResNet50 {loaded_label}", resnet_result)
    else:
        col_card, col_blank = st.columns([1, 1])
        with col_card:
            label = "CLIP Zero-Shot" if clip_result else (
                "ResNet50 ✅" if resnet_result and resnet_result["model_loaded"] else "ResNet50 ⚠️ 未訓練"
            )
            render_model_card(label, primary)

    # ── RAG 應變建議 ───────────────────────────────────────
    st.markdown("## 💡 應變建議")
    with st.spinner("生成建議..."):
        from rag.generator import generate_advice
        rag_result = generate_advice(
            disaster_type_zh=primary["top_class_zh"],
            confidence=primary["confidence"],
            user_description=user_desc,
            location=location,
        )
    render_rag_result(rag_result, primary["top_class_zh"])

    # ── Safety 提醒 ────────────────────────────────────────
    st.markdown("""
    <div class="safety-box">
      ⚠️ <strong>AI Safety 提醒</strong><br>
      本系統分類與建議僅供災害資訊整理與初步參考，不代表官方災害判定。<br>
      若有人員受困、受傷或有立即危險，請<strong>優先撥打 119、110</strong> 或依政府公告行動。<br>
      RAG 建議來自系統整理之防災文件，仍需由使用者與管理者自行判斷適用性。
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
      <div style="font-size:3rem;margin-bottom:16px">🖼️</div>
      <div style="font-size:1.1rem;font-weight:600;color:#475569">上傳照片後點擊「開始分析」</div>
      <div style="font-size:0.85rem;margin-top:8px;color:#334155">
        系統將自動辨識災害類型並提供應變建議
      </div>
    </div>
    """, unsafe_allow_html=True)
