"""ResNet50 Linear Probe 推論模組。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import functools

from utils.config import RESNET_WEIGHTS

MAPPING_PATH = RESNET_WEIGHTS.replace(".pth", "_classes.json")

# ── 預設 fallback（訓練前使用）────────────────────────────────
_DEFAULT_ZH = [
    "地震或建築損壞", "火災", "土石流或坍方", "淹水", "其他或無明顯災害"
]
_DEFAULT_EN = [
    "Damaged Infrastructure", "Fire Disaster",
    "Land Disaster", "Water Disaster", "Non Damage"
]


def _load_class_mapping():
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, encoding="utf-8") as f:
            m = json.load(f)
        return m["classes"], m["zh_labels"]
    return _DEFAULT_EN, _DEFAULT_ZH


@functools.lru_cache(maxsize=1)
def _load_resnet():
    classes_en, classes_zh = _load_class_mapping()
    num_classes = len(classes_en)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model  = models.resnet50(weights=None)
    for p in model.parameters():
        p.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    model = model.to(device)

    loaded = False
    if os.path.exists(RESNET_WEIGHTS):
        state = torch.load(RESNET_WEIGHTS, map_location=device)
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
    ResNet50 推論。

    Returns
    -------
    {
        "top_class":    "Water_Disaster",
        "top_class_zh": "淹水",
        "confidence":   0.74,
        "top_3": [...],
        "model_loaded": True / False
    }
    """
    model, device, loaded, classes_en, classes_zh = _load_resnet()

    tensor = _TRANSFORM(image).unsqueeze(0).to(device)
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
