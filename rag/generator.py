"""RAG 生成模組：用 Gemini LLM 根據檢索到的文件產生應變建議。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import google.generativeai as genai

from utils.config import GEMINI_API_KEY
from rag.retriever import retrieve, index_exists
from rag.prompts import RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE, FALLBACK_ADVICE


def _init_gemini():
    if not GEMINI_API_KEY:
        return None
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=RAG_SYSTEM_PROMPT,
    )


_gemini_model = None


def generate_advice(
    disaster_type_zh: str,
    confidence: float,
    user_description: str = "",
    location: str = "",
) -> dict:
    """
    根據災害類型檢索文件，呼叫 Gemini 生成建議。

    Returns
    -------
    {
        "advice":  ["・...", "・...", ...],
        "sources": ["flood_sop.md", ...],
        "used_rag": True,
        "used_llm": True,
    }
    """
    global _gemini_model

    # ── 1. 組 Query ──────────────────────────────────────
    query = f"{disaster_type_zh} 應變措施"
    if user_description:
        query += f" {user_description}"
    if location:
        query += f" {location}"

    # ── 2. FAISS 檢索 ─────────────────────────────────────
    docs = retrieve(query) if index_exists() else []
    sources = list(dict.fromkeys(d["source"] for d in docs))  # 去重保序

    # ── 3. LLM 生成 ───────────────────────────────────────
    if GEMINI_API_KEY and docs:
        try:
            if _gemini_model is None:
                _gemini_model = _init_gemini()

            context = "\n\n---\n\n".join(
                f"[{d['source']}]\n{d['text']}" for d in docs
            )
            prompt = RAG_USER_TEMPLATE.format(
                context=context,
                disaster_type=disaster_type_zh,
                confidence=confidence,
                user_description=user_description or "（未填寫）",
                location=location or "（未填寫）",
            )

            response = _gemini_model.generate_content(prompt)
            raw_text = response.text.strip()

            # 解析成列表（按行分割，保留「・」開頭的行）
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            advice_lines = [l for l in lines if l.startswith("・") or l.startswith("•") or l.startswith("-")]
            if not advice_lines:
                advice_lines = lines  # 如果沒有符合格式，直接用所有行

            return {
                "advice":   advice_lines,
                "sources":  sources,
                "used_rag": True,
                "used_llm": True,
                "raw":      raw_text,
            }

        except Exception as e:
            from utils.logger import log_error
            log_error("rag_generate", f"Gemini 呼叫失敗：{e}", exc_info=True)

    # ── 4. Fallback（無 API key 或無 index）─────────────────
    fallback = FALLBACK_ADVICE.get(disaster_type_zh, FALLBACK_ADVICE["其他或無明顯災害"])
    return {
        "advice":   fallback,
        "sources":  sources if sources else ["內建應變指引"],
        "used_rag": bool(docs),
        "used_llm": False,
    }
