"""
MLOps 版本常數。
每次更新模型、Prompt、RAG Index 或規則時，在此遞增版號。
所有版本號都會被寫入 model_runs 表，供未來 retraining 追蹤。
"""

# ── 模型版本 ──────────────────────────────────────────────────
CLIP_MODEL_VERSION       = "clip-vitl14-v1"
CLIP_PROMPT_VERSION      = "multi-prompt-avg-v1"      # classify_multi_prompt 多描述平均

CNN_MODEL_VERSION        = "custom-cnn-medic-6class-v1"

RAG_INDEX_VERSION        = "faiss-multilingual-minilm-v1"
RAG_PROMPT_VERSION       = "gemini-flash-rag-v1"

# ── 規則版本 ──────────────────────────────────────────────────
AGGREGATION_RULE_VERSION = "disaster-group-distance-timewindow-v4"
PRIORITY_RULE_VERSION    = "svcp-weighted-v2"  # Severity+Vulnerability+Credibility+Priority

# ── 判斷閾值 ──────────────────────────────────────────────────
CLIP_LOW_CONF_THRESHOLD  = 0.50   # CLIP 信心度低於此值 → need_review
CLIP_TOP2_GAP_THRESHOLD  = 0.15   # Top-1 − Top-2 差距低於此值 → need_review（模型模糊）
                                  # 例：淹水 52% vs 颱風 49%，gap=3% < 15% → 送審
CNN_AUX_ENABLED          = True   # 是否啟用自訓 CNN 輔助交叉驗證
