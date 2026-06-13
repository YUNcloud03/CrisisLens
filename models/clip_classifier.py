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
import functools

from utils.config import CLASSES_EN, CLASSES_ZH, PROMPT_SETS, MULTI_PROMPT_SETS, CLIP_MODEL_NAME

_GENERATED_PATH = os.path.join(os.path.dirname(__file__), "..", "utils", "prompts_generated.json")
_LINEAR_HEAD_PATH = os.path.join(os.path.dirname(__file__), "clip_linear_head.pth")


def _slice_head_to_current_classes(weight, bias, saved_classes_en, target_classes_en):
    """
    依「類別名稱」從舊 linear head 的 weight/bias 挑出對應現在類別的列。

    Parameters
    ----------
    weight            : Tensor (N_saved, in_dim)
    bias              : Tensor (N_saved,)
    saved_classes_en  : 舊權重的類別名稱清單（順序對應 weight 各列）
    target_classes_en : 現在要保留的類別名稱清單（決定輸出順序）

    Returns
    -------
    (sliced_weight, sliced_bias) 對齊 target_classes_en 順序；
    若 target 任一類別不存在於 saved，回 None。
    """
    saved_index = {cls: i for i, cls in enumerate(saved_classes_en)}
    idx = []
    for cls in target_classes_en:
        if cls not in saved_index:
            return None
        idx.append(saved_index[cls])
    return weight[idx], bias[idx]


@functools.lru_cache(maxsize=1)
def _load_linear_head():
    """
    載入 clip_linear_head.pth，並把舊類別切片成現在的 CLASSES_EN。
    回傳 (head: nn.Linear, temperature: float) 或 None（檔案缺失 / 維度不符 / 類別對不上）。
    """
    if not os.path.exists(_LINEAR_HEAD_PATH):
        return None
    import torch.nn as nn
    try:
        ckpt = torch.load(_LINEAR_HEAD_PATH, map_location="cpu")
        sd = ckpt["state_dict"]
        weight, bias = sd["weight"], sd["bias"]            # (N_saved, in_dim), (N_saved,)
        if weight.shape[1] != ckpt.get("in_dim", weight.shape[1]):
            return None
        sliced = _slice_head_to_current_classes(weight, bias, ckpt["classes_en"], CLASSES_EN)
        if sliced is None:
            return None
        sliced_w, sliced_b = sliced
        head = nn.Linear(sliced_w.shape[1], sliced_w.shape[0])
        with torch.no_grad():
            head.weight.copy_(sliced_w)
            head.bias.copy_(sliced_b)
        head.eval()
        temperature = float(ckpt.get("temperature", 1.0))
        return head, temperature
    except Exception:
        return None


def linear_probe_available() -> bool:
    """UI 用：linear probe 權重是否可成功載入並切片。"""
    return _load_linear_head() is not None


def _load_active_multi_prompts() -> tuple[dict, str]:
    """
    載入 Gemini 生成的 prompt（若存在），否則使用內建 MULTI_PROMPT_SETS。
    回傳 (prompt_dict, source)，source 為 "Gemini生成" 或 "內建"。
    """
    if os.path.exists(_GENERATED_PATH):
        with open(_GENERATED_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # 確保每類別是完整陣列，不足的回 MULTI_PROMPT_SETS
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
    使用 CLIP 對圖片做 zero-shot 分類（單組 prompt）。

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
    多描述投票分類（主要推論方法）。每個類別用多條 prompt，取平均 cosine similarity 後 softmax。
    優先載入 Gemini 生成的 prompts_generated.json，否則用 MULTI_PROMPT_SETS。
    回傳格式與 classify() 相同，額外附帶 prompt_source 欄位。
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
            # 每條 prompt 的餘弦相似度平均作為該類別分數
            sims = (image_features @ text_features.T)[0]  # (num_prompts,)
            class_mean_sims.append(sims.mean().item())

    # softmax 轉成機率分布
    # ⚠️ 必須乘以 100 再做 softmax，與 classify() 一致。
    # 不乘的話 cosine similarity 差距 ~0.02 → softmax 近均等 → 每類約 16%
    # 乘以 100 後差距放大 → softmax 正常區分
    import torch as _torch
    scaled = 100.0 * _torch.tensor(class_mean_sims)
    probs_t = _torch.softmax(scaled, dim=0)
    probs   = probs_t.numpy()

    top_indices = probs.argsort()[::-1][:3]
    top_3 = [
        {
            "class":    CLASSES_EN[i],
            "class_zh": CLASSES_ZH[i],
            "score":    float(probs[i]),
        }
        for i in top_indices
    ]

    best = top_3[0]
    return {
        "top_class":    best["class"],
        "top_class_zh": best["class_zh"],
        "confidence":   best["score"],
        "top_3":        top_3,
        "all_scores":   {CLASSES_ZH[i]: float(probs[i]) for i in range(len(probs))},
        "prompt_source": prompt_source,
    }


def compare_prompt_sets(image: Image.Image) -> dict:
    """一次跑三組 prompt set，回傳各組結果供比較。"""
    return {key: classify(image, key) for key in PROMPT_SETS}
