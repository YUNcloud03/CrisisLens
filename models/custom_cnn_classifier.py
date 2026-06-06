"""自訓 CNN 推論模組 — 介面對齊 clip_classifier.classify()。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import functools
from PIL import Image

import torch
from torchvision import transforms

from models.custom_cnn_model import DisasterCNN_v1

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "custom_cnn.pth")
MAPPING_PATH = os.path.join(os.path.dirname(__file__), "custom_cnn_classes.json")

# 預設 fallback（權重不在時）
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


_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


def classify(image: Image.Image) -> dict:
    """
    自訓 CNN 推論。回傳格式與 clip_classifier.classify() 一致。

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

    tensor = _TRANSFORM(image.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1)[0].cpu().numpy()

    top_indices = probs.argsort()[::-1][:3]
    top_3 = [
        {
            "class":    classes_en[i],
            "class_zh": classes_zh[i],
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
        "model_loaded": loaded,
    }


def weights_exist() -> bool:
    """Streamlit 側邊欄狀態檢查用。"""
    return os.path.exists(WEIGHTS_PATH) and os.path.exists(MAPPING_PATH)
