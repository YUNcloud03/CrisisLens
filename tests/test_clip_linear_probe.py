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
