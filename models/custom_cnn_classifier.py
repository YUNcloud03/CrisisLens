"""自訓 CNN 災情分類器 ── 介面與 clip_classifier.classify() 相同。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import functools
from PIL import Image

import torch
import torch.nn.functional as F
from torchvision import transforms

from models.custom_cnn_model import DisasterCNN_v1


def _pil_to_tensor(img: Image.Image) -> torch.Tensor:
    """
    PIL Image → float32 tensor (C, H, W)，不依賴 numpy。
    用 torch.frombuffer 繞過 NumPy 2.x / torch 2.1 的相容問題。
    """
    img = img.convert("RGB")
    buf = img.tobytes()
    h, w = img.height, img.width
    t = torch.frombuffer(bytearray(buf), dtype=torch.uint8).reshape(h, w, 3)
    return t.permute(2, 0, 1).float() / 255.0

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "custom_cnn.pth")
MAPPING_PATH = os.path.join(os.path.dirname(__file__), "custom_cnn_classes.json")

# 預設 fallback（權重不存在時）
_DEFAULT_EN = ["Earthquake Damage", "Flood", "Fire",
               "Typhoon or Storm Damage", "Landslide", "Other or No Disaster"]
_DEFAULT_ZH = ["地震或建築損壞", "淹水", "火災",
               "颱風或強風災損", "土石流或坍方", "其他或無明顯災害"]


def _load_class_mapping():
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, encoding="utf-8") as f:
            m = json.load(f)
        return m["classes"], m["zh_labels"]
    return _DEFAULT_EN, _DEFAULT_ZH


@functools.lru_cache(maxsize=1)
def _load_model():
    classes_en, classes_zh = _load_class_mapping()
    num_classes = len(classes_en)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model  = DisasterCNN_v1(num_classes=num_classes).to(device)

    loaded = False
    if os.path.exists(WEIGHTS_PATH):
        state = torch.load(WEIGHTS_PATH, map_location=device, weights_only=True)
        model.load_state_dict(state)
        loaded = True

    model.eval()
    return model, device, loaded, classes_en, classes_zh


# PIL-based 前處理（Resize、CenterCrop 不需要 numpy）
_PIL_TRANSFORMS = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
])

# ImageNet 正規化參數
_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def classify(image: Image.Image) -> dict:
    """
    自訓 CNN 分類。回傳格式與 clip_classifier.classify() 相同。

    Returns
    -------
    {
        "top_class":    "Flood",
        "top_class_zh": "淹水",
        "confidence":   0.74,
        "top_3":        [{...}, {...}, {...}],
        "model_loaded": True / False
    }
    """
    model, device, loaded, classes_en, classes_zh = _load_model()

    # 前處理：PIL resize/crop → tensor（不經過 numpy）
    pil_img = _PIL_TRANSFORMS(image.convert("RGB"))
    tensor  = (_pil_to_tensor(pil_img) - _MEAN) / _STD
    tensor  = tensor.unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs_t = torch.softmax(logits, dim=1)[0]  # keep as tensor

    # Top-3（用 tensor 排序，不用 numpy）
    top_vals, top_idxs = torch.topk(probs_t, k=3)

    top_3 = [
        {
            "class":    classes_en[int(top_idxs[k])],
            "class_zh": classes_zh[int(top_idxs[k])],
            "score":    float(top_vals[k]),
        }
        for k in range(3)
    ]

    best = top_3[0]
    return {
        "top_class":    best["class"],
        "top_class_zh": best["class_zh"],
        "confidence":   best["score"],
        "top_3":        top_3,
        "model_loaded": loaded,
    }


def weights_exist() -> bool:
    """Streamlit 初始化時檢查用。"""
    return os.path.exists(WEIGHTS_PATH) and os.path.exists(MAPPING_PATH)
