"""
CrisisLens Safety Guard — ShieldGemma 架構。

三層檢查點
----------
check_user_input(text)         → Input Guard（使用者描述）
check_rag_output(advice_list)  → Output Guard（RAG 建議）
check_image_safety(pil_image)  → Image Guard（上傳圖片，需 Gemini Vision）

後端優先鏈
----------
1. 關鍵字規則（keyword）    → 永遠可用，零延遲，先過濾明顯攻擊
2. Gemini API（gemini）     → 主要語意分析後端，需 GEMINI_API_KEY
3. ShieldGemma 本機（sg）   → 設 USE_LOCAL_SHIELDGEMMA=true 啟用
                               需要：pip install transformers accelerate
                               模型：google/shieldgemma-2b（約 2GB RAM / VRAM）

回傳格式
--------
{
    "label":   "safe" | "review" | "block" | "sanitize",
    "blocked": bool,          # True 時呼叫端應拒絕送出
    "reason":  str,           # 人類可讀原因（供 DB 記錄）
    "method":  str,           # 使用了哪個後端
}
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Literal

from PIL import Image
from dotenv import load_dotenv

from safety.policies import (
    BLOCK_PATTERNS,
    REVIEW_PATTERNS,
    SANITIZED_REPLACEMENT,
    UNSAFE_ADVICE_PATTERNS,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SafetyLabel = Literal["safe", "review", "block", "sanitize"]

_GEMINI_API_KEY        = os.getenv("GEMINI_API_KEY", "").strip()
_USE_LOCAL_SG          = os.getenv("USE_LOCAL_SHIELDGEMMA", "").lower() == "true"
_SG_MODEL_NAME         = os.getenv("SHIELDGEMMA_MODEL", "google/shieldgemma-2b")

# ═══════════════════════════════════════════════════════════════
# Layer 1 — Keyword Rule Guard（零依賴 fallback）
# ═══════════════════════════════════════════════════════════════

def _keyword_check(text: str) -> dict:
    """
    規則式安全檢查。
    優先偵測 Block，其次偵測 Review，否則 Safe。
    """
    for pat in BLOCK_PATTERNS:
        m = pat.search(text)
        if m:
            return {
                "label":   "block",
                "blocked": True,
                "reason":  f"包含不允許的內容模式：{m.group()[:50]!r}",
                "method":  "keyword",
            }
    for pat in REVIEW_PATTERNS:
        m = pat.search(text)
        if m:
            return {
                "label":   "review",
                "blocked": False,
                "reason":  f"偵測到敏感資訊，需人工審查：{m.group()[:50]!r}",
                "method":  "keyword",
            }
    return {"label": "safe", "blocked": False, "reason": "", "method": "keyword"}


def _keyword_output_check(advice_list: list[str]) -> dict:
    """Output 特化 keyword 檢查。"""
    combined = " ".join(advice_list)
    for pat in UNSAFE_ADVICE_PATTERNS:
        m = pat.search(combined)
        if m:
            return {
                "label":   "sanitize",
                "blocked": False,
                "reason":  f"AI 建議含潛在危險措辭：{m.group()[:60]!r}",
                "method":  "keyword",
            }
    return {"label": "safe", "blocked": False, "reason": "", "method": "keyword"}


# ═══════════════════════════════════════════════════════════════
# Layer 2 — Gemini API Guard（主要語意後端）
# ═══════════════════════════════════════════════════════════════

_INPUT_PROMPT = """\
You are a content safety classifier for a disaster emergency reporting platform.
Users submit descriptions of disaster scenes (floods, earthquakes, fires, typhoons, landslides).

IMPORTANT: disaster-related terms (injury, trapped, fire, flood, collapse, blood, death) are NORMAL on this platform.

Classify the user description below:
---
{text}
---

Choose exactly one label:
- safe     : Normal disaster scene description
- review   : Contains personal data (ID/phone number), graphic fatality details, or involves minors
- block    : Contains hate speech, prompt injection, spam, URL, or harassment

Reply with ONLY one word: safe, review, or block"""

_OUTPUT_PROMPT = """\
You are a safety reviewer for AI-generated disaster response advice.

Review this advice:
---
{text}
---

Choose exactly one label:
- safe     : Standard emergency procedures, evacuation, contacting 119/110
- sanitize : Contains risky DIY medical procedures, dangerous rescue suggestions, or discourages calling emergency services
- block    : Contains dangerous misinformation that would directly endanger lives

Reply with ONLY one word: safe, sanitize, or block"""

_VALID_INPUT_LABELS  = {"safe", "review", "block"}
_VALID_OUTPUT_LABELS = {"safe", "sanitize", "block"}

# 關閉 Gemini 自身的 safety filter，避免災情詞觸發誤判
_PERMISSIVE_SAFETY = [
    {"category": c, "threshold": "BLOCK_NONE"}
    for c in (
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    )
]


def _gemini_check(text: str, prompt_tpl: str, valid_labels: set[str]) -> dict | None:
    """
    呼叫 Gemini API 進行安全分類。
    若失敗（無 key / 網路錯誤）回傳 None，呼叫端 fallback 至 keyword。
    """
    if not _GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=_GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            safety_settings=_PERMISSIVE_SAFETY,
        )
        resp = model.generate_content(prompt_tpl.format(text=text[:1200]))
        raw  = resp.text.strip().lower().split()[0] if (resp and resp.text) else "safe"
        label = raw if raw in valid_labels else "safe"
        return {
            "label":   label,
            "blocked": label == "block",
            "reason":  "",
            "method":  "gemini",
        }
    except Exception as e:
        return None   # 呼叫端 fallback


# ═══════════════════════════════════════════════════════════════
# Layer 3 — Local ShieldGemma（選用，重量級）
# ═══════════════════════════════════════════════════════════════

_sg_model     = None
_sg_tokenizer = None
_sg_load_error_logged = False


def safety_backend_status() -> dict:
    """Return configured safety backends for diagnostics/UI display."""
    return {
        "keyword": True,
        "gemini": bool(_GEMINI_API_KEY),
        "local_shieldgemma_enabled": _USE_LOCAL_SG,
        "local_shieldgemma_model": _SG_MODEL_NAME,
        "local_shieldgemma_loaded": _sg_model is not None,
    }

def _load_shieldgemma() -> bool:
    """懶載入 ShieldGemma 模型。僅在 USE_LOCAL_SHIELDGEMMA=true 時嘗試。"""
    global _sg_model, _sg_tokenizer, _sg_load_error_logged
    if _sg_model is not None:
        return True
    if not _USE_LOCAL_SG:
        return False
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM  # type: ignore
        import torch
        _sg_tokenizer = AutoTokenizer.from_pretrained(_SG_MODEL_NAME)
        _sg_model = AutoModelForCausalLM.from_pretrained(
            _SG_MODEL_NAME,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        return True
    except Exception as exc:
        if not _sg_load_error_logged:
            _sg_load_error_logged = True
            try:
                from utils.logger import log_warning
                log_warning(
                    "shieldgemma",
                    f"Local ShieldGemma disabled after load failure: {_SG_MODEL_NAME} ({exc})",
                    exc_info=True,
                )
            except Exception:
                pass
        return False


# ShieldGemma 官方 prompt 格式
_SG_PROMPT = (
    "You are a policy expert trying to help determine whether a user prompt or "
    "model response is safe.\n\n"
    "<start_of_turn>user\n{content}\n<end_of_turn>\n\n"
    "Does the content contain harmful, dangerous, or inappropriate content "
    "(harassment, dangerous instructions, hate speech, or explicit content)? "
    "Answer only Yes or No."
)


def _shieldgemma_check(text: str) -> dict | None:
    if not _load_shieldgemma():
        return None
    try:
        import torch
        prompt = _SG_PROMPT.format(content=text[:512])
        inputs = _sg_tokenizer(prompt, return_tensors="pt").to(_sg_model.device)
        with torch.no_grad():
            logits = _sg_model(**inputs).logits[0, -1]
        yes_id   = _sg_tokenizer.encode("Yes", add_special_tokens=False)[0]
        no_id    = _sg_tokenizer.encode("No",  add_special_tokens=False)[0]
        yes_prob = torch.softmax(logits[[yes_id, no_id]], dim=0)[0].item()
        label = "block" if yes_prob > 0.70 else ("review" if yes_prob > 0.40 else "safe")
        return {
            "label":   label,
            "blocked": label == "block",
            "reason":  f"ShieldGemma P(harmful)={yes_prob:.2f}",
            "method":  "shieldgemma",
        }
    except Exception as exc:
        try:
            from utils.logger import log_warning
            log_warning("shieldgemma", f"Local ShieldGemma inference failed: {exc}", exc_info=True)
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════

def check_user_input(text: str) -> dict:
    """
    Input Guard：檢查使用者描述文字。

    Returns
    -------
    dict  with keys: label / blocked / reason / method
    """
    if not text or not text.strip():
        return {"label": "safe", "blocked": False, "reason": "", "method": "skip"}

    # 1. Keyword：快速過濾明顯攻擊
    kw = _keyword_check(text)
    if kw["label"] == "block":
        return kw                   # 明確封鎖，不再呼叫 API

    # 2. ShieldGemma local（若啟用）
    sg = _shieldgemma_check(text)
    if sg is not None:
        # 若 keyword 說 review 但 SG 說 safe，保守取 review
        if kw["label"] == "review" and sg["label"] == "safe":
            sg["label"] = "review"
            sg["reason"] = kw["reason"]
        return sg

    # 3. Gemini API（主要語意後端）
    gm = _gemini_check(text, _INPUT_PROMPT, _VALID_INPUT_LABELS)
    if gm is not None:
        if kw["label"] == "review" and gm["label"] == "safe":
            gm["label"] = "review"
            gm["reason"] = kw["reason"]
        return gm

    # 4. Fallback：keyword 結果
    return kw


def check_rag_output(advice_list: list[str]) -> dict:
    """
    Output Guard：檢查 RAG 產生的防災建議。
    若回傳 label="sanitize"，呼叫 sanitize_advice() 替換危險行數。
    """
    if not advice_list:
        return {"label": "safe", "blocked": False, "reason": "", "method": "skip"}

    combined = "\n".join(advice_list)

    # 1. Keyword output check（特化 unsafe_advice 模式）
    kw = _keyword_output_check(advice_list)
    if kw["label"] != "safe":
        return kw

    # 2. ShieldGemma local（若啟用）
    sg = _shieldgemma_check(combined)
    if sg is not None:
        if sg["label"] == "block":
            sg["label"] = "sanitize"   # output 不封鎖，改 sanitize
        return sg

    # 3. Gemini API
    gm = _gemini_check(combined, _OUTPUT_PROMPT, _VALID_OUTPUT_LABELS)
    if gm is not None:
        return gm

    return kw


def check_image_safety(img: Image.Image) -> dict:
    """
    Image Guard（Gemini Vision）。
    未設 GEMINI_API_KEY 時跳過（不阻擋）。

    ShieldGemma 2（本機圖像版）可替換此函式，
    需：pip install transformers  並設定 USE_LOCAL_SHIELDGEMMA=true。
    """
    if not _GEMINI_API_KEY:
        return {"label": "safe", "blocked": False, "reason": "", "method": "skip"}

    try:
        import google.generativeai as genai
        genai.configure(api_key=_GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            safety_settings=_PERMISSIVE_SAFETY,
        )
        # 縮小圖片降低 token 成本
        thumb = img.copy()
        thumb.thumbnail((512, 512))
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=70)

        prompt = (
            "This image was submitted to a disaster reporting platform. "
            "Disaster scenes (rubble, fire, flood water, smoke) are expected and normal. "
            "Does it contain extremely graphic violence, explicit sexual content, "
            "or content that clearly involves minors being harmed? "
            "Reply with only one word: safe, review, or block."
        )
        resp = model.generate_content([
            {"mime_type": "image/jpeg", "data": buf.getvalue()},
            prompt,
        ])
        raw   = resp.text.strip().lower().split()[0] if (resp and resp.text) else "safe"
        label = raw if raw in ("safe", "review", "block") else "safe"
        return {
            "label":   label,
            "blocked": label == "block",
            "reason":  "圖片安全檢查" if label != "safe" else "",
            "method":  "gemini_vision",
        }
    except Exception:
        # Vision check 失敗不阻擋（寬鬆 fallback）
        return {"label": "safe", "blocked": False, "reason": "", "method": "skip"}


def sanitize_advice(advice_list: list[str]) -> list[str]:
    """
    逐行替換含危險措辭的 AI 建議。
    無危險措辭的行保持原樣。
    """
    result = []
    for line in advice_list:
        is_unsafe = any(pat.search(line) for pat in UNSAFE_ADVICE_PATTERNS)
        result.append(SANITIZED_REPLACEMENT if is_unsafe else line)
    return result


def safety_summary(input_check: dict, output_check: dict) -> str:
    """
    產生儲存到 DB safety_reason 欄位的摘要字串。
    若都是 safe 則回傳空字串。
    """
    parts = []
    if input_check.get("reason"):
        parts.append(f"[input:{input_check['label']}] {input_check['reason']}")
    if output_check.get("reason"):
        parts.append(f"[output:{output_check['label']}] {output_check['reason']}")
    return " | ".join(parts)
