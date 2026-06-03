"""Page 1 — 災情回報 Submit Report"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json, uuid
from datetime import datetime
import streamlit as st

from db.database import init_db
from db.queries import insert_report, insert_model_run, update_model_run_report
from aggregation.scoring import calc_report_severity
from aggregation.event_matcher import aggregate, _derive_grid_id
from aggregation.h3_utils import latlng_to_h3_cell, DEFAULT_RESOLUTION
from utils.image_utils import load_image, resize_for_display
from utils.ui_theme import apply_theme
from utils.versions import (
    CLIP_MODEL_VERSION, CLIP_PROMPT_VERSION,
    CNN_MODEL_VERSION, RAG_INDEX_VERSION, RAG_PROMPT_VERSION,
    AGGREGATION_RULE_VERSION, PRIORITY_RULE_VERSION,
    CLIP_LOW_CONF_THRESHOLD, CLIP_TOP2_GAP_THRESHOLD, CNN_AUX_ENABLED,
)

try:
    from streamlit_js_eval import get_geolocation as _get_geo
    _HAS_GEO = True
except ImportError:
    _HAS_GEO = False

init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "reports")
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="災情回報｜CrisisLens", page_icon="📋", layout="wide")
apply_theme()
st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background:#080d1a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background:#0a1220!important;border-right:1px solid rgba(30,64,120,.45)}
h1,h2,h3,h4{color:#e2e8f0!important}
.card{background:#0d1628;border:1px solid rgba(30,64,120,.45);border-radius:10px;padding:16px 20px;margin-bottom:12px}
.advice-item{background:rgba(56,189,248,.06);border-left:3px solid #38bdf8;padding:8px 12px;margin:6px 0;border-radius:0 6px 6px 0;font-size:.9rem}
.h3-badge{display:inline-block;background:rgba(56,189,248,.12);border:1px solid rgba(56,189,248,.3);
          color:#38bdf8;font-size:.72rem;padding:3px 10px;border-radius:999px;font-family:monospace}
div.stButton>button{background:linear-gradient(135deg,#0284c7,#38bdf8)!important;color:white!important;
    border:none!important;font-weight:700!important;border-radius:8px!important;width:100%}
hr{border-color:rgba(30,64,120,.45)!important}
footer{visibility:hidden}
</style>""", unsafe_allow_html=True)

st.markdown("## 📋 災情回報")
st.markdown("<hr>", unsafe_allow_html=True)

# ── GPS 取得 ──────────────────────────────────────────────────
st.markdown("#### 📍 位置取得方式")

_gps_options = ["🛰️ 手動輸入 GPS 座標", "🗺️ 輸入縣市行政區"]
if _HAS_GEO:
    _gps_options.append("📡 自動偵測（瀏覽器 GPS）")

loc_mode = st.radio("", _gps_options, horizontal=True, label_visibility="collapsed")

latitude  = None
longitude = None
location_source = "manual"
h3_cell   = None

# ── 模式 A：手動輸入座標 ──────────────────────────────────────
if loc_mode == "🛰️ 手動輸入 GPS 座標":
    gc1, gc2 = st.columns(2)
    with gc1:
        lat_in = st.number_input("緯度 Latitude", value=25.0330, format="%.6f",
                                 help="例如台北信義區約 25.0330")
    with gc2:
        lng_in = st.number_input("經度 Longitude", value=121.5654, format="%.6f",
                                 help="例如台北信義區約 121.5654")
    if lat_in != 0.0 and lng_in != 0.0:
        latitude, longitude = lat_in, lng_in
        location_source = "gps"
        h3_cell = latlng_to_h3_cell(latitude, longitude)
        st.markdown(
            f'H3 Cell（Resolution {DEFAULT_RESOLUTION}）：'
            f'<span class="h3-badge">{h3_cell}</span>',
            unsafe_allow_html=True
        )

# ── 模式 B：縣市行政區（不取 GPS） ───────────────────────────
elif loc_mode == "🗺️ 輸入縣市行政區":
    pass  # city / district 已在表單中填寫

# ── 模式 C：瀏覽器自動偵測 ──────────────────────────────────
elif loc_mode == "📡 自動偵測（瀏覽器 GPS）":
    st.info("⚠️ 點擊下方按鈕後，瀏覽器會詢問是否允許存取您的位置資訊。\n\n"
            "本系統僅將座標用於災情回報定位，不會儲存或傳送至第三方。")

    if "gps_approved" not in st.session_state:
        st.session_state["gps_approved"] = False

    if not st.session_state["gps_approved"]:
        if st.button("✅ 我同意，取得我的 GPS 位置"):
            st.session_state["gps_approved"] = True
            st.rerun()
    else:
        with st.spinner("正在取得位置，請在瀏覽器彈窗中按「允許」..."):
            geo = _get_geo()

        if geo and geo.get("coords"):
            auto_lat = geo["coords"]["latitude"]
            auto_lng = geo["coords"]["longitude"]
            acc      = geo["coords"].get("accuracy", "?")
            latitude, longitude = auto_lat, auto_lng
            location_source = "gps"
            h3_cell = latlng_to_h3_cell(latitude, longitude)

            gcol1, gcol2 = st.columns(2)
            gcol1.success(f"📍 緯度：{auto_lat:.6f}")
            gcol2.success(f"📍 經度：{auto_lng:.6f}")
            st.caption(f"定位精確度：±{acc:.0f} 公尺")
            st.markdown(
                f'H3 Cell（Resolution {DEFAULT_RESOLUTION}）：'
                f'<span class="h3-badge">{h3_cell}</span>',
                unsafe_allow_html=True
            )
        else:
            st.warning("尚未取得位置。請確認已在瀏覽器彈窗中點選「允許」，或改用手動輸入。")
            if st.button("🔄 重試"):
                st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ── 主表單 ────────────────────────────────────────────────────
with st.form("report_form"):
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("#### 📷 照片")
        uploaded = st.file_uploader("上傳災情照片", type=["jpg","jpeg","png","webp"])
        if uploaded:
            img_preview = load_image(uploaded)
            st.image(resize_for_display(img_preview), use_container_width=True)

        st.markdown("#### 📝 描述")
        description = st.text_area("文字描述", placeholder="例如：路燈倒塌，道路積水...",
                                   height=100, label_visibility="collapsed")

    with col2:
        st.markdown("#### 🏘️ 地點資訊")
        location_name = st.text_input("地點名稱", placeholder="例如：信義路五段100號附近")
        c1, c2 = st.columns(2)
        with c1:
            city = st.selectbox("縣市", ["","台北市","新北市","桃園市","台中市","台南市","高雄市",
                                         "基隆市","新竹市","新竹縣","苗栗縣","彰化縣","南投縣",
                                         "雲林縣","嘉義市","嘉義縣","屏東縣","宜蘭縣","花蓮縣",
                                         "台東縣","澎湖縣","金門縣","連江縣"])
        with c2:
            district = st.text_input("行政區", placeholder="例如：信義區")

        st.markdown("#### ⏰ 時間")
        event_time_in = st.text_input("事件發生時間", placeholder="例如：2025-05-25 14:30")

        st.markdown("#### 🚨 現場狀況")
        need_help    = st.checkbox("需要協助")
        ppl_count    = st.number_input("大約需要協助人數", min_value=0, max_value=999, value=0)
        has_trapped  = st.checkbox("有人受困")
        has_injured  = st.checkbox("有人受傷")
        road_blocked = st.checkbox("道路不可通行")

    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("🚀 送出回報", use_container_width=True)

# ── 送出處理 ──────────────────────────────────────────────────
if submitted:
    if not uploaded:
        st.error("請上傳災情照片")
        st.stop()

    with st.spinner("分析中..."):
        uploaded.seek(0)
        img = load_image(uploaded)
        fname = f"{uuid.uuid4().hex}.jpg"
        fpath = os.path.join(UPLOAD_DIR, fname)
        img.save(fpath, "JPEG")

        # ── 主模型：CLIP（多描述投票版 + ViT-L/14）──────────────
        from models.clip_classifier import classify_multi_prompt as clip_classify
        clip_res = clip_classify(img)

        # ── 輔助模型：自訓 CNN（第二意見交叉驗證，若權重存在）──────────
        cnn_type = cnn_zh = cnn_conf = cnn_ver = None
        if CNN_AUX_ENABLED:
            try:
                from models.custom_cnn_classifier import classify as cnn_classify, weights_exist
                if weights_exist():
                    c = cnn_classify(img)
                    cnn_type = c.get("top_class")
                    cnn_zh   = c.get("top_class_zh")   # 用中文標籤做比對
                    cnn_conf = c.get("confidence")
                    cnn_ver  = CNN_MODEL_VERSION
            except Exception:
                pass  # CNN 未訓練或出錯，靜默略過

        # ── 一致性判斷 & need_review ──────────────────────────
        # 用「中文標籤」比對，避免 CLIP 與自訓 CNN 英文標籤字串略有差異的誤判。
        model_agreement  = 1
        need_review_flag = 0
        review_reasons   = []

        if clip_res["confidence"] < CLIP_LOW_CONF_THRESHOLD:
            need_review_flag = 1
            review_reasons.append(f"CLIP 信心度偏低（{clip_res['confidence']:.1%}）")

        _top3 = clip_res.get("top_3", [])
        clip_top2_gap = None
        if len(_top3) >= 2:
            clip_top2_gap = _top3[0]["score"] - _top3[1]["score"]
            if clip_top2_gap < CLIP_TOP2_GAP_THRESHOLD:
                need_review_flag = 1
                review_reasons.append(
                    f"Top-1／Top-2 差距過小（{clip_top2_gap:.2f}）：可能為"
                    f"「{_top3[0]['class_zh']}」或「{_top3[1]['class_zh']}」"
                )

        if cnn_zh and cnn_zh != clip_res["top_class_zh"]:
            model_agreement  = 0
            need_review_flag = 1
            review_reasons.append(
                f"兩模型結果不一致：CLIP＝**{clip_res['top_class_zh']}** vs "
                f"自訓 CNN＝**{cnn_zh or cnn_type}**"
            )

        # ── RAG 建議 ──────────────────────────────────────────
        from rag.generator import generate_advice
        rag_res = generate_advice(
            disaster_type_zh=clip_res["top_class_zh"],
            confidence=clip_res["confidence"],
            user_description=description,
            location=f"{city}{district}{location_name}",
        )

        # ── 嚴重度評分 ────────────────────────────────────────
        report_base = {
            "has_injured_people":    int(has_injured),
            "has_trapped_people":    int(has_trapped),
            "road_blocked":          int(road_blocked),
            "need_help":             int(need_help),
            "reported_people_count": int(ppl_count),
            "disaster_type":         clip_res["top_class"],
            "clip_confidence":       clip_res["confidence"],
        }
        sev_score, sev_level = calc_report_severity(report_base)

        now      = datetime.now().isoformat(timespec="seconds")
        evt_time = event_time_in.strip() if event_time_in.strip() else now
        h3_val   = h3_cell  # 可能是 None（無 GPS 模式）

        # ── 計算 grid_id / grid_type ──────────────────────────
        _tmp = {
            "h3_cell": h3_val,
            "city": city or None,
            "district": district or None,
        }
        grid_id, grid_type_val = _derive_grid_id(_tmp)

        # ── 先寫入 model_run（事後回填 report_id）────────────
        run_id = insert_model_run({
            "run_time":                  now,
            "trigger":                   "submit",
            "clip_model_version":        CLIP_MODEL_VERSION,
            "clip_prompt_version":       CLIP_PROMPT_VERSION,
            "resnet_model_version":      cnn_ver,
            "rag_index_version":         RAG_INDEX_VERSION,
            "rag_prompt_version":        RAG_PROMPT_VERSION,
            "aggregation_rule_version":  AGGREGATION_RULE_VERSION,
            "priority_rule_version":     PRIORITY_RULE_VERSION,
            "report_id":                 None,
            "notes":                     None,
        })

        full_report = {
            "event_id":                  None,
            "image_path":                fpath,
            "description":               description,
            "location_name":             location_name,
            "city":                      city or None,
            "district":                  district or None,
            "latitude":                  latitude,
            "longitude":                 longitude,
            "location_source":           location_source,
            "h3_cell":                   h3_val,
            "h3_resolution":             DEFAULT_RESOLUTION if h3_val else None,
            "grid_id":                   grid_id,
            "grid_type":                 grid_type_val,
            "event_time":                evt_time,
            "upload_time":               now,
            # CLIP
            "clip_model_version":        CLIP_MODEL_VERSION,
            "clip_prompt_version":       CLIP_PROMPT_VERSION,
            "clip_disaster_type":        clip_res["top_class"],
            "clip_confidence":           clip_res["confidence"],
            "clip_top2_gap":             clip_top2_gap,
            "clip_top3":                 json.dumps(clip_res["top_3"], ensure_ascii=False),
            "top3_predictions":          json.dumps(clip_res["top_3"], ensure_ascii=False),
            # 輔助模型：自訓 CNN（沿用 resnet_* 欄位儲存）
            "resnet_model_version":      cnn_ver,
            "resnet_disaster_type":      cnn_type,
            "resnet_confidence":         cnn_conf,
            # 最終決策
            "disaster_type":             clip_res["top_class"],
            "model_agreement":           model_agreement,
            "need_review":               need_review_flag,
            # 現場
            "need_help":                 int(need_help),
            "reported_people_count":     int(ppl_count),
            "has_trapped_people":        int(has_trapped),
            "has_injured_people":        int(has_injured),
            "road_blocked":              int(road_blocked),
            "report_severity_score":     sev_score,
            "report_severity_level":     sev_level,
            # RAG
            "rag_version":               RAG_PROMPT_VERSION,
            "rag_advice":                json.dumps(rag_res["advice"],  ensure_ascii=False),
            "rag_sources":               json.dumps(rag_res["sources"], ensure_ascii=False),
            # MLOps
            "model_run_id":              run_id,
            "aggregation_rule_version":  AGGREGATION_RULE_VERSION,
            "priority_rule_version":     PRIORITY_RULE_VERSION,
        }

        report_id = insert_report(full_report)
        update_model_run_report(run_id, report_id)   # 回填 run→report
        agg = aggregate(full_report, report_id)

    # ── 結果顯示 ──────────────────────────────────────────────
    st.success("✅ 回報已送出！")

    # need_review / 模型不一致警示
    if need_review_flag:
        st.warning(
            "⚠️ **需人工審核**：" + "、".join(review_reasons) + "\n\n"
            "回報已正常寫入並會顯示在熱圖，管理者可在 Admin Review 頁修正分類。"
        )

    # 自訓 CNN 輔助結果（若有）—— 全部顯示中文標籤
    if cnn_zh or cnn_type:
        agree_icon = "✅ 一致" if model_agreement else "⚠️ 不一致"
        cnn_display = cnn_zh or cnn_type
        st.info(
            f"**模型比對 {agree_icon}** ── "
            f"CLIP: **{clip_res['top_class_zh']}**（{clip_res['confidence']:.1%}）　"
            f"自訓 CNN: **{cnn_display}**（{cnn_conf:.1%}）"
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4)
    def _color(level):
        return {"High":"#f87171","Medium":"#fbbf24","Low":"#4ade80"}.get(level,"#94a3b8")

    with r1:
        _psrc = clip_res.get("prompt_source", "內建")
        st.markdown(f"""<div class="card">
        <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em">災害類型</div>
        <div style="font-size:1.4rem;font-weight:800;color:#38bdf8">{clip_res['top_class_zh']}</div>
        <div style="color:#94a3b8;font-size:.82rem">信心度 {clip_res['confidence']:.1%}</div>
        <div style="color:#64748b;font-size:.7rem;margin-top:4px">Prompt：{_psrc}</div>
        </div>""", unsafe_allow_html=True)
    with r2:
        st.markdown(f"""<div class="card">
        <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">回報嚴重度</div>
        <div style="font-size:1.4rem;font-weight:800;color:{_color(sev_level)}">{sev_level}</div>
        <div style="color:#94a3b8;font-size:.82rem">分數 {sev_score}</div>
        </div>""", unsafe_allow_html=True)
    with r3:
        new_tag = "🆕 新事件" if agg["is_new"] else "🔗 既有事件"
        st.markdown(f"""<div class="card">
        <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">事件優先級 · {new_tag}</div>
        <div style="font-size:1.4rem;font-weight:800;color:{_color(agg['event_priority_level'])}">{agg['event_priority_level']}</div>
        <div style="color:#94a3b8;font-size:.82rem">事件 #{agg['event_id']} · 分數 {agg['event_priority_score']}</div>
        </div>""", unsafe_allow_html=True)
    with r4:
        h3_display = agg.get("h3_cell") or "—"
        src_label  = "GPS" if location_source == "gps" else "手動"
        st.markdown(f"""<div class="card">
        <div style="font-size:.72rem;color:#94a3b8;text-transform:uppercase">位置資訊</div>
        <div style="font-size:.8rem;font-family:monospace;color:#38bdf8;margin-top:4px;word-break:break-all">{h3_display}</div>
        <div style="color:#94a3b8;font-size:.75rem;margin-top:4px">來源：{src_label}
        {f"· {latitude:.4f}, {longitude:.4f}" if latitude else ""}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("#### 💡 應變建議")
    for line in rag_res["advice"]:
        clean = line.lstrip("・•-").strip()
        if clean:
            st.markdown(f'<div class="advice-item">・{clean}</div>', unsafe_allow_html=True)

    st.markdown("""<div style="background:rgba(220,38,38,.08);border:1px solid rgba(248,113,113,.3);
    border-radius:8px;padding:12px 16px;margin-top:16px;font-size:.82rem;color:#fca5a5;line-height:1.7">
    ⚠️ <strong>AI Safety 提醒</strong><br>
    本系統分類與建議僅供初步參考，不代表官方災害判定。<br>
    若有立即危險，請優先撥打 <strong>119、110</strong>。
    </div>""", unsafe_allow_html=True)
