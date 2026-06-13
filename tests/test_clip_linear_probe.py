"""CLIP linear-probe 切片與路由邏輯測試（不載入 CLIP 模型）。"""
import torch

from models.clip_classifier import _slice_head_to_current_classes

# 舊 6 類（與 f39c2b4 的 CLASSES_EN 一致）
SAVED_6 = [
    "Earthquake Damage",
    "Flood",
    "Fire",
    "Typhoon or Storm Damage",
    "Landslide",
    "Other or No Disaster",
]
TARGET_5 = [
    "Earthquake Damage",
    "Flood",
    "Fire",
    "Typhoon or Storm Damage",
    "Landslide",
]


def test_slice_keeps_five_and_drops_other():
    # weight 每行用行號填值，方便驗證對應關係
    weight = torch.arange(6 * 4, dtype=torch.float32).reshape(6, 4)
    bias = torch.arange(6, dtype=torch.float32)

    sliced_w, sliced_b = _slice_head_to_current_classes(weight, bias, SAVED_6, TARGET_5)

    assert sliced_w.shape == (5, 4)
    assert sliced_b.shape == (5,)
    # 前 5 類名稱順序相同 → 應取行 0..4，丟掉行 5（Other or No Disaster）
    assert torch.equal(sliced_w, weight[:5])
    assert torch.equal(sliced_b, bias[:5])


def test_slice_matches_by_name_not_position():
    # 故意打亂 saved 順序，確認靠名稱對應而非位置
    saved = ["Flood", "Fire", "Other or No Disaster",
             "Earthquake Damage", "Landslide", "Typhoon or Storm Damage"]
    weight = torch.arange(6 * 3, dtype=torch.float32).reshape(6, 3)
    bias = torch.arange(6, dtype=torch.float32)

    sliced_w, sliced_b = _slice_head_to_current_classes(weight, bias, saved, TARGET_5)

    # TARGET_5[0]=Earthquake 在 saved 第 3 列
    assert torch.equal(sliced_w[0], weight[saved.index("Earthquake Damage")])
    assert torch.equal(sliced_w[1], weight[saved.index("Flood")])
    assert sliced_w.shape == (5, 3)


def test_slice_returns_none_when_target_class_missing():
    saved = ["Flood", "Fire", "Earthquake Damage"]  # 缺 Typhoon / Landslide
    weight = torch.arange(3 * 4, dtype=torch.float32).reshape(3, 4)
    bias = torch.arange(3, dtype=torch.float32)

    assert _slice_head_to_current_classes(weight, bias, saved, TARGET_5) is None


from models.clip_classifier import _load_linear_head


def test_load_linear_head_outputs_five_classes():
    loaded = _load_linear_head()
    assert loaded is not None, "clip_linear_head.pth 應已由 Task 1 取回"
    head, temperature = loaded
    # 切片後輸出維度應為現在的 5 類
    assert head.out_features == 5
    assert head.in_features == 768
    assert isinstance(temperature, float)
    assert temperature > 0
    # 隨機 768 維特徵應產生 5 個 logit
    out = head(torch.randn(1, 768))
    assert out.shape == (1, 5)


import models.clip_classifier as cc


def test_classify_clip_falls_back_to_zero_shot(monkeypatch):
    # 模擬 linear probe 不可用
    monkeypatch.setattr(cc, "_load_linear_head", lambda: None)
    monkeypatch.setattr(cc, "classify_multi_prompt",
                        lambda img: {"top_class": "Flood", "top_class_zh": "淹水",
                                     "confidence": 0.9, "top_3": [], "all_scores": {}})
    out = cc.classify_clip(object(), prefer_probe=True)
    assert out["method"] == "zero_shot"
    assert out["top_class"] == "Flood"


def test_classify_clip_uses_probe_when_available(monkeypatch):
    monkeypatch.setattr(cc, "_load_linear_head", lambda: ("dummy_head", 1.0))
    monkeypatch.setattr(cc, "classify_linear_probe",
                        lambda img: {"top_class": "Fire", "top_class_zh": "火災",
                                     "confidence": 0.8, "top_3": [], "all_scores": {},
                                     "method": "linear_probe"})
    out = cc.classify_clip(object(), prefer_probe=True)
    assert out["method"] == "linear_probe"
    assert out["top_class"] == "Fire"


def test_classify_clip_prefer_probe_false_uses_zero_shot(monkeypatch):
    monkeypatch.setattr(cc, "_load_linear_head", lambda: ("dummy_head", 1.0))
    monkeypatch.setattr(cc, "classify_multi_prompt",
                        lambda img: {"top_class": "Landslide", "top_class_zh": "土石流或坍方",
                                     "confidence": 0.7, "top_3": [], "all_scores": {}})
    out = cc.classify_clip(object(), prefer_probe=False)
    assert out["method"] == "zero_shot"
