"""CLIP Zero-Shot 災情分類模組。"""
import warnings, logging
warnings.filterwarnings("ignore", message=".*__path__.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import clip
from PIL import Image
from typing import Optional
import functools

from utils.config import CLASSES_EN, CLASSES_ZH, PROMPT_SETS, CLIP_MODEL_NAME


@functools.lru_cache(maxsize=1)
def _load_clip():
    """載入 CLIP 模型（快取，只載入一次）。"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load(CLIP_MODEL_NAME, device=device)
    model.eval()
    return model, preprocess, device


def classify(
    image: Image.Image,
    prompt_set_key: str = "B｜完整句版",
) -> dict:
    """
    使用 CLIP 對圖片做 zero-shot 分類。

    Parameters
    ----------
    image         : PIL RGB Image
    prompt_set_key: PROMPT_SETS 的 key（A / B / C）

    Returns
    -------
    {
        "top_class":    "Flood",
        "top_class_zh": "淹水",
        "confidence":   0.82,
        "top_3": [
            {"class": "Flood",     "class_zh": "淹水",   "score": 0.82},
            {"class": "Typhoon ..", "class_zh": "颱風..", "score": 0.11},
            {"class": "Landslide", "class_zh": "土石流", "score": 0.04},
        ]
    }
    """
    model, preprocess, device = _load_clip()
    prompts = PROMPT_SETS[prompt_set_key]

    # ── 圖片預處理 ──────────────────────────────────────────
    image_input = preprocess(image).unsqueeze(0).to(device)

    # ── 文字 token ──────────────────────────────────────────
    text_tokens = clip.tokenize(prompts).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        text_features  = model.encode_text(text_tokens)

        # cosine similarity → softmax
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features  = text_features  / text_features.norm(dim=-1, keepdim=True)
        logits = (100.0 * image_features @ text_features.T).softmax(dim=-1)

    scores = logits[0].cpu().numpy()  # shape: (6,)

    # ── Top-3 ───────────────────────────────────────────────
    top_indices = scores.argsort()[::-1][:3]
    top_3 = [
        {
            "class":    CLASSES_EN[i],
            "class_zh": CLASSES_ZH[i],
            "score":    float(scores[i]),
        }
        for i in top_indices
    ]

    best = top_3[0]
    return {
        "top_class":    best["class"],
        "top_class_zh": best["class_zh"],
        "confidence":   best["score"],
        "top_3":        top_3,
        "all_scores":   {CLASSES_ZH[i]: float(scores[i]) for i in range(len(scores))},
    }


def compare_prompt_sets(image: Image.Image) -> dict:
    """一次跑三組 prompt set，回傳各組結果供比較。"""
    return {key: classify(image, key) for key in PROMPT_SETS}
