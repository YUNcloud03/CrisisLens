"""
CrisisLens 安全政策定義（ShieldGemma 架構）。

設計原則
--------
災害平台本來就包含「受傷、火災、坍塌、死亡、出血」等詞彙，不應過度封鎖。
目標是防止：惡意測試攻擊、Prompt Injection、騷擾、個資洩露、AI 輸出的危險建議。

Label 說明
----------
safe     : 正常災情內容，直接允許
review   : 敏感但不封鎖，寫入 DB 並標記 need_review=1 供人工審查
block    : 明確不允許，拒絕送出並顯示錯誤
sanitize : 僅用於 Output Guard，危險 AI 建議替換為安全措辭
"""

from __future__ import annotations
import re

# ── 災害平台允許詞（即使出現也不觸發 review）──────────────────
#    這些詞在災情描述中完全正常
DISASTER_ALLOWLIST: frozenset[str] = frozenset({
    "受傷", "受困", "死亡", "傷亡", "火災", "火焰", "煙霧",
    "淹水", "洪水", "積水", "地震", "颱風", "坍方", "土石流",
    "爆炸", "倒塌", "破壞", "損毀", "斷電", "停電",
    "撤離", "疏散", "救援", "避難", "急救",
    "119", "110", "消防", "警察", "醫院", "救護車",
    "blood", "injury", "trapped", "fire", "flood",
    "collapse", "rescue", "earthquake", "typhoon",
})

# ── Input Review 觸發模式（標記但不封鎖）────────────────────
REVIEW_PATTERNS: list[re.Pattern] = [
    # 身分證號格式 A123456789
    re.compile(r"\b[A-Z]\d{9}\b"),
    # 台灣手機號碼
    re.compile(r"\b09\d{2}[-\s]?\d{3}[-\s]?\d{3}\b"),
    # 精確地址：門牌號 + 樓層
    re.compile(r"\d+\s*號\s*\d+\s*樓"),
    # 含兒少關鍵字
    re.compile(r"小孩|兒童|幼童|嬰兒|嬰幼兒|孩童"),
    # 高度圖像化血腥描述（並非正常災情）
    re.compile(r"斷肢|截肢|嚴重燒傷|焦屍|大量出血.*(?!路面|積水)"),
]

# ── Input Block 觸發模式（直接拒絕）──────────────────────────
BLOCK_PATTERNS: list[re.Pattern] = [
    # Prompt Injection 攻擊
    re.compile(r"ignore\s+(previous|all)\s+instructions?", re.IGNORECASE),
    re.compile(r"(system|assistant)\s*:\s*(you are|act as|pretend)", re.IGNORECASE),
    re.compile(r"jailbreak|DAN\s+mode|developer\s+mode", re.IGNORECASE),
    re.compile(r"<\|.*?\|>"),                             # token injection 格式
    re.compile(r"\[INST\]|\[\/INST\]"),                  # Llama 格式注入
    # 仇恨/騷擾
    re.compile(r"去死|種族滅絕|死全家", re.IGNORECASE),
    # 垃圾輸入（15 個以上相同字元）
    re.compile(r"(.)\1{14,}"),
    # 描述欄含 URL（疑似垃圾或釣魚）
    re.compile(r"https?://\S{10,}"),
]

# ── Output Sanitize 模式（危險 AI 建議替換）──────────────────
#    若 RAG 產生以下內容，應替換為安全措辭
UNSAFE_ADVICE_PATTERNS: list[re.Pattern] = [
    # 危險自救醫療
    re.compile(r"自行(手術|縫合|拔出|包紮)(傷口|骨頭|異物)", re.IGNORECASE),
    re.compile(r"服用\s*\d+\s*(毫克|mg|顆|粒)", re.IGNORECASE),
    re.compile(r"靜脈注射|輸血", re.IGNORECASE),
    # 鼓勵冒險進入危險區域
    re.compile(r"(可以|請|立即|直接)[\w ]{0,10}(進入|穿越|衝進)(火場|崩塌|淹水區|災區)", re.IGNORECASE),
    re.compile(r"(獨自|自己)(進入|前往|穿越)(火場|崩塌|淹水區|災區)", re.IGNORECASE),
    # 明確建議不撥打 119
    re.compile(r"不(需要|用|必)打\s*119", re.IGNORECASE),
    re.compile(r"119\s*(不|沒有)必要", re.IGNORECASE),
]

# ── 安全替換文字（Output 被 sanitize 時使用）────────────────
SANITIZED_REPLACEMENT = (
    "請立即撥打 119（消防救援）或 110（警察），"
    "說明您的位置與狀況，並等待專業人員協助。"
    "切勿自行冒險進入危險區域或嘗試非專業急救。"
)

# ── Safety 等級說明（供 UI 顯示）──────────────────────────
LABEL_DISPLAY: dict[str, str] = {
    "safe":     "✅ 安全",
    "review":   "🔍 待審查",
    "block":    "🚫 已封鎖",
    "sanitize": "⚠️ 已修正",
    "skip":     "— 未檢查",
}
