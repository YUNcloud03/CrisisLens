"""
MLOps 版本常數。
每次更新模型、Prompt、RAG Index 或規則時，在此遞增版號。
所有版本號都會被寫入 model_runs 表，供未來 retraining 追蹤。
"""

# ── 模型版本 ──────────────────────────────────────────────────
CLIP_MODEL_VERSION       = "clip-vitb32-v1"
CLIP_PROMPT_VERSION      = "B-complete-sentence-v1"   # 對應 PROMPT_SETS["B｜完整句版"]

RESNET_MODEL_VERSION     = "resnet50-linear-probe-v1"

RAG_INDEX_VERSION        = "faiss-multilingual-minilm-v1"
RAG_PROMPT_VERSION       = "gemini-flash-rag-v1"

# ── 規則版本 ──────────────────────────────────────────────────
AGGREGATION_RULE_VERSION = "h3-district-city-fallback-v2"
PRIORITY_RULE_VERSION    = "severity-weighted-v1"

# ── 判斷閾值 ──────────────────────────────────────────────────
CLIP_LOW_CONF_THRESHOLD  = 0.50   # CLIP 信心度低於此值 → need_review
RESNET_ENABLED           = True   # 是否啟用 ResNet50 輔助判斷
