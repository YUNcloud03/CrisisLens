"""CLIP Zero-Shot 災情分類模組。"""
import warnings, logging
warnings.filterwarnings("ignore", message=".*__path__.*")
logging.getLogger("transformers").setLevel(logging.ERROR)

import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import clip
from PIL import Image
from typing import Optional
import functools

from utils.config import CLASSES_EN, CLASSES_ZH, PROMPT_SETS, MULTI_PROMPT_SETS, CLIP_MODEL_NAME

_GENERATED_PATH = os.path.join(os.path.dirname(__file__), "..", "utils", "prompts_generated.json")


def _load_active_multi_prompts() -> tuple[dict, str]:
    """
    載入 Gemini 生成的 prompt（若存在），否則使用手寫的 MULTI_PROMPT_SETS。
    回傳 (prompt_dict, source)，source 為 "Gemini生成" 或 "內建"。
    """
    if os.path.exists(_GENERATED_PATH):
        with open(_GENERATED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # 確保每個類別都有資料，缺少的補回 MULTI_PROMPT_SETS
        merged = {}
        for cls in CLASSES_EN:
            generated = data.get(cls, [])
            merged[cls] = generated if len(generated) >= 3 else MULTI_PROMPT_SETS.get(cls, [])
        return merged, "Gemini生成"
    return MULTI_PROMPT_SETS, "內建"


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


def classify_multi_prompt(image: Image.Image) -> dict:
    """
    多描述投票版分類：每個類別用多條 prompt，取平均 cosine similarity 後 softmax。
    優先載入 Gemini 生成的 prompts_generated.json，找不到才用 MULTI_PROMPT_SETS。
    回傳格式與 classify() 相同。
    """
    model, preprocess, device = _load_clip()
    image_input = preprocess(image).unsqueeze(0).to(device)
    active_prompts, prompt_source = _load_active_multi_prompts()

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        class_mean_sims = []
        for class_name in CLASSES_EN:
            prompts = active_prompts[class_name]
            tokens  = clip.tokenize(prompts).to(device)
            text_features = model.encode_text(tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            # 每條 prompt 的相似度平均作為該類別分數
            sims = (image_features @ text_features.T)[0]
            class_mean_sims.append(sims.mean())

        # ×100 logit 縮放後再 softmax（與單 prompt 版 classify() 一致），
        # 否則原始 cosine 值太接近，softmax 後會擠成平坦的 ~17%。
        scores = (100.0 * torch.stack(class_mean_sims)).softmax(dim=0).cpu().numpy()

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
        "top_class":     best["class"],
        "top_class_zh":  best["class_zh"],
        "confidence":    best["score"],
        "top_3":         top_3,
        "all_scores":    {CLASSES_ZH[i]: float(scores[i]) for i in range(len(scores))},
        "prompt_source": prompt_source,
    }


_LINEAR_HEAD_PATH = os.path.join(os.path.dirname(__file__), "clip_linear_head.pth")


@functools.lru_cache(maxsize=1)
def _load_linear_head():
    """載入 Colab 訓練好的 linear probe 權重（clip_linear_head.pth）。"""
    if not os.path.exists(_LINEAR_HEAD_PATH):
        return None
    import torch.nn as nn
    ckpt = torch.load(_LINEAR_HEAD_PATH, map_location="cpu")
    head = nn.Linear(ckpt["in_dim"], len(ckpt["classes_en"]))
    head.load_state_dict(ckpt["state_dict"])
    head.eval()
    temperature = float(ckpt.get("temperature", 1.0))   # 舊權重無此欄則 1.0
    return head, ckpt["classes_en"], temperature


def linear_probe_available() -> bool:
    """UI 用：是否已放入訓練好的 linear probe 權重。"""
    return os.path.exists(_LINEAR_HEAD_PATH)


def classify_linear_probe(image: Image.Image) -> dict:
    """
    用 MEDIC 訓練的 linear probe 分類（凍結 CLIP 特徵 + 線性層）。
    需先在 Colab 訓練並把 clip_linear_head.pth 放到 models/。
    回傳格式與 classify() 相同。
    """
    loaded = _load_linear_head()
    if loaded is None:
        raise FileNotFoundError(
            "找不到 models/clip_linear_head.pth。\n"
            "請先用 notebooks/clip_linear_probe_medic.ipynb 在 Colab 訓練並下載權重。"
        )
    head, classes_en, temperature = loaded
    zh_map = dict(zip(CLASSES_EN, CLASSES_ZH))

    model, preprocess, device = _load_clip()
    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        feat = model.encode_image(image_input)
        feat = feat / feat.norm(dim=-1, keepdim=True)   # 與訓練端一致的 L2 normalize
        logits = head(feat.float().cpu())
        scores = (logits / temperature).softmax(dim=-1)[0].numpy()   # 溫度校準

    top_indices = scores.argsort()[::-1][:3]
    top_3 = [
        {
            "class":    classes_en[i],
            "class_zh": zh_map.get(classes_en[i], classes_en[i]),
            "score":    float(scores[i]),
        }
        for i in top_indices
    ]
    best = top_3[0]
    return {
        "top_class":     best["class"],
        "top_class_zh":  best["class_zh"],
        "confidence":    best["score"],
        "top_3":         top_3,
        "all_scores":    {zh_map.get(classes_en[i], classes_en[i]): float(scores[i])
                          for i in range(len(scores))},
        "prompt_source": "Linear Probe (MEDIC)",
    }


def compare_prompt_sets(image: Image.Image) -> dict:
    """一次跑三組 prompt set，回傳各組結果供比較。"""
    return {key: classify(image, key) for key in PROMPT_SETS}
