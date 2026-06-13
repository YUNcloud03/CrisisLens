# CLIP Linear Probe 復活 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 取回舊的 6 類 CLIP linear-probe 權重，依類別名稱切片成現在的 5 類，作為雙主投票中的 CLIP 訊號取代 zero-shot，並保留 zero-shot 為可選退路。

**Architecture:** 凍結的 CLIP ViT-L/14（768 維）特徵不變，舊 `nn.Linear(768, 6)` 權重的前 5 行（名稱對應現在 `CLASSES_EN`）切出成 `nn.Linear(768, 5)`，丟掉 `Other or No Disaster`，重新 softmax。對外用 `classify_clip(prefer_probe=)` 統一入口，載入失敗自動退回 `classify_multi_prompt`。app.py 選單新增 probe / zero-shot 兩條可選路徑。

**Tech Stack:** Python, PyTorch, OpenAI CLIP, Streamlit, pytest（新引入）。

---

## File Structure

- `models/clip_linear_head.pth` — **取回**（git checkout f39c2b4），舊 6 類 linear head 權重。
- `.gitignore` — **修改**，加例外讓 `clip_linear_head.pth` 被追蹤。
- `models/clip_classifier.py` — **修改**，新增 `_slice_head_to_current_classes` / `_load_linear_head` / `classify_linear_probe` / `classify_clip` / `linear_probe_available`。
- `utils/versions.py` — **修改**，新增 `CLIP_PROBE_VERSION`。
- `app.py` — **修改**，選單 4 項、CLIP 呼叫改 `classify_clip`、UI 顯示 method。
- `tests/test_clip_linear_probe.py` — **新建**，純邏輯與路由測試（不載入 CLIP）。
- `requirements.txt` — **修改**，加 `pytest`（若已有則略過）。

---

## Task 1: 取回舊權重並讓 git 追蹤

**Files:**
- Recover: `models/clip_linear_head.pth`
- Modify: `.gitignore`（在 `!models/efficientnet_b0_5class_v2.pth` 下一行）

- [ ] **Step 1: 從舊 commit 取回權重檔**

Run:
```bash
git checkout f39c2b4 -- models/clip_linear_head.pth
```

- [ ] **Step 2: 驗證檔案存在且大小正確**

Run:
```bash
git cat-file -s f39c2b4:models/clip_linear_head.pth && ls -l models/clip_linear_head.pth
```
Expected: 顯示 `20517`，且本機檔案存在、約 20KB。

- [ ] **Step 3: 在 .gitignore 加例外**

在 `.gitignore` 第 30 行 `!models/efficientnet_b0_5class_v2.pth` 之後新增一行：
```
!models/clip_linear_head.pth
```

- [ ] **Step 4: 確認檔案已被 git 納入追蹤**

Run:
```bash
git add models/clip_linear_head.pth .gitignore && git status --short
```
Expected: 看到 `A  models/clip_linear_head.pth` 與 `M  .gitignore`。

- [ ] **Step 5: Commit**

```bash
git commit -m "chore: 取回 clip_linear_head.pth（舊 6 類 linear probe 權重）並納入追蹤"
```

---

## Task 2: 純切片函式 `_slice_head_to_current_classes`（TDD）

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`（空檔）
- Create: `tests/test_clip_linear_probe.py`
- Modify: `models/clip_classifier.py`

- [ ] **Step 1: 安裝 pytest 並登錄到 requirements**

Run:
```bash
python -m pip install pytest
```
然後在 `requirements.txt` 末尾新增一行（若尚無 pytest）：
```
pytest
```

- [ ] **Step 2: 建立空的 tests 套件檔**

建立 `tests/__init__.py`，內容為空。

- [ ] **Step 3: 寫失敗測試**

建立 `tests/test_clip_linear_probe.py`：
```python
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
```

- [ ] **Step 4: 跑測試確認失敗**

Run:
```bash
python -m pytest tests/test_clip_linear_probe.py -v
```
Expected: FAIL（`ImportError: cannot import name '_slice_head_to_current_classes'`）。

- [ ] **Step 5: 實作切片函式**

在 `models/clip_classifier.py` 的 import 區之後（約第 19 行 `_GENERATED_PATH` 定義附近）加入：
```python
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
    idx = []
    for cls in target_classes_en:
        if cls not in saved_classes_en:
            return None
        idx.append(saved_classes_en.index(cls))
    return weight[idx], bias[idx]
```

- [ ] **Step 6: 跑測試確認通過**

Run:
```bash
python -m pytest tests/test_clip_linear_probe.py -v
```
Expected: 3 passed。

- [ ] **Step 7: Commit**

```bash
git add requirements.txt tests/__init__.py tests/test_clip_linear_probe.py models/clip_classifier.py
git commit -m "feat: 加入 linear head 依類別名稱切片函式（含測試）"
```

---

## Task 3: `_load_linear_head` 載入並切片（TDD）

**Files:**
- Modify: `tests/test_clip_linear_probe.py`
- Modify: `models/clip_classifier.py`

- [ ] **Step 1: 寫失敗測試（用真實取回的 .pth）**

在 `tests/test_clip_linear_probe.py` 末尾新增：
```python
from models.clip_classifier import _load_linear_head


def test_load_linear_head_outputs_five_classes():
    loaded = _load_linear_head()
    assert loaded is not None, "clip_linear_head.pth 應已由 Task 1 取回"
    head, temperature = loaded
    # 切片後輸出維度應為現在的 5 類
    assert head.out_features == 5
    assert head.in_features == 768
    assert isinstance(temperature, float)
    # 隨機 768 維特徵應產生 5 個 logit
    out = head(torch.randn(1, 768))
    assert out.shape == (1, 5)
```

- [ ] **Step 2: 跑測試確認失敗**

Run:
```bash
python -m pytest tests/test_clip_linear_probe.py::test_load_linear_head_outputs_five_classes -v
```
Expected: FAIL（`cannot import name '_load_linear_head'`）。

- [ ] **Step 3: 實作 `_load_linear_head`**

在 `models/clip_classifier.py` 的 `_slice_head_to_current_classes` 之後加入：
```python
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
```

- [ ] **Step 4: 跑測試確認通過**

Run:
```bash
python -m pytest tests/test_clip_linear_probe.py -v
```
Expected: 4 passed。

- [ ] **Step 5: Commit**

```bash
git add tests/test_clip_linear_probe.py models/clip_classifier.py
git commit -m "feat: _load_linear_head 載入舊權重並切片成 5 類（含測試）"
```

---

## Task 4: `classify_linear_probe` + `classify_clip` 路由（TDD）

**Files:**
- Modify: `tests/test_clip_linear_probe.py`
- Modify: `models/clip_classifier.py`

- [ ] **Step 1: 寫失敗測試（用 monkeypatch 避免載入 CLIP）**

在 `tests/test_clip_linear_probe.py` 末尾新增：
```python
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
```

- [ ] **Step 2: 跑測試確認失敗**

Run:
```bash
python -m pytest tests/test_clip_linear_probe.py -k classify_clip -v
```
Expected: FAIL（`module 'models.clip_classifier' has no attribute 'classify_clip'`）。

- [ ] **Step 3: 實作 `classify_linear_probe` 與 `classify_clip`**

在 `models/clip_classifier.py` 的 `classify_multi_prompt` 函式之後加入：
```python
def classify_linear_probe(image: Image.Image) -> dict:
    """
    用切片後的 5 類 linear probe 分類（凍結 CLIP 特徵 + 線性層）。
    回傳格式與 classify_multi_prompt 相同，額外帶 method="linear_probe"。
    """
    loaded = _load_linear_head()
    if loaded is None:
        raise FileNotFoundError("無法載入 models/clip_linear_head.pth（缺失或類別對不上）。")
    head, temperature = loaded

    model, preprocess, device = _load_clip()
    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        feat = model.encode_image(image_input)
        feat = feat / feat.norm(dim=-1, keepdim=True)        # 與訓練端一致的 L2 normalize
        logits = head(feat.float().cpu())
        scores = (logits / temperature).softmax(dim=-1)[0].numpy()   # (5,) 溫度校準

    top_indices = scores.argsort()[::-1][:3]
    top_3 = [
        {"class": CLASSES_EN[i], "class_zh": CLASSES_ZH[i], "score": float(scores[i])}
        for i in top_indices
    ]
    best = top_3[0]
    return {
        "top_class":     best["class"],
        "top_class_zh":  best["class_zh"],
        "confidence":    best["score"],
        "top_3":         top_3,
        "all_scores":    {CLASSES_ZH[i]: float(scores[i]) for i in range(len(scores))},
        "method":        "linear_probe",
        "prompt_source": "Linear Probe (MEDIC 6→5)",
    }


def classify_clip(image: Image.Image, prefer_probe: bool = True) -> dict:
    """
    CLIP 統一入口。prefer_probe 時優先用 linear probe，載入失敗或推論出錯則退回
    zero-shot（classify_multi_prompt）。結果以 method 欄位標示實際使用的路徑。
    """
    if prefer_probe and _load_linear_head() is not None:
        try:
            return classify_linear_probe(image)
        except Exception:
            pass  # 退回 zero-shot
    result = classify_multi_prompt(image)
    result["method"] = "zero_shot"
    return result
```

- [ ] **Step 4: 跑測試確認通過**

Run:
```bash
python -m pytest tests/test_clip_linear_probe.py -v
```
Expected: 7 passed。

- [ ] **Step 5: Commit**

```bash
git add tests/test_clip_linear_probe.py models/clip_classifier.py
git commit -m "feat: classify_linear_probe 與 classify_clip 統一入口（含 fallback 與路由測試）"
```

---

## Task 5: 新增版本常數

**Files:**
- Modify: `utils/versions.py`（約第 10 行 `CLIP_PROMPT_VERSION` 之後）

- [ ] **Step 1: 新增 CLIP_PROBE_VERSION**

在 `utils/versions.py` 的 `CLIP_PROMPT_VERSION = ...` 那一行之後新增：
```python
CLIP_PROBE_VERSION       = "linear-probe-medic-6to5-v1"  # 舊 6 類 linear probe 切片成 5 類
```

- [ ] **Step 2: 確認可被匯入**

Run:
```bash
python -c "from utils.versions import CLIP_PROBE_VERSION; print(CLIP_PROBE_VERSION)"
```
Expected: 印出 `linear-probe-medic-6to5-v1`。

- [ ] **Step 3: Commit**

```bash
git add utils/versions.py
git commit -m "chore: 新增 CLIP_PROBE_VERSION 版本常數"
```

---

## Task 6: app.py 整合（選單 + 路由 + UI 顯示）

**Files:**
- Modify: `app.py`（選單約第 236-241 行；CLIP 呼叫約第 533-537 行；推論後）

- [ ] **Step 1: 改選單為 4 項**

把 `app.py` 的 selectbox（約第 236-241 行）：
```python
    model_mode = st.selectbox(
        "使用模型",
        ["雙主投票 (CLIP + EfficientNet-B0)", "CLIP ViT-L/14", "EfficientNet-B0"],
        help="「雙主投票」同時執行 CLIP 與 EfficientNet-B0：一致→高信心；不一致→need_review 並取信心較高者",
    )
```
改為：
```python
    model_mode = st.selectbox(
        "使用模型",
        [
            "雙主投票 (CLIP linear-probe + EfficientNet-B0)",
            "CLIP linear-probe",
            "CLIP ViT-L/14 (zero-shot)",
            "EfficientNet-B0",
        ],
        help="「雙主投票」同時執行 CLIP 與 EfficientNet-B0：一致→高信心；不一致→need_review 並取信心較高者。"
             "CLIP 預設走 linear-probe，權重未就緒時自動退回 zero-shot。",
    )
    _prefer_probe = "linear-probe" in model_mode
```

- [ ] **Step 2: 改 CLIP 推論呼叫**

把 CLIP 推論段（約第 533-537 行）：
```python
        # ── CLIP ViT-L/14（零樣本，多 prompt 平均）──────────
        if _USE_CLIP:
            from models.clip_classifier import classify_multi_prompt as clip_classify
            clip_result = clip_classify(img)
```
改為：
```python
        # ── CLIP ViT-L/14（linear-probe 優先，否則 zero-shot 多 prompt 平均）──
        if _USE_CLIP:
            from models.clip_classifier import classify_clip
            clip_result = classify_clip(img, prefer_probe=_prefer_probe)
```

- [ ] **Step 3: 在推論結果計算後顯示 CLIP 實際路徑**

在 `_inference_ms = round(...)` 那一行之後（雙主投票 `_model_agreement` 計算之前）插入：
```python
    if clip_result is not None and _USE_CLIP:
        _m = clip_result.get("method", "zero_shot")
        if _prefer_probe and _m == "zero_shot":
            st.caption("ℹ️ linear probe 權重未就緒，已退回 zero-shot CLIP")
        else:
            _label = {"linear_probe": "CLIP：linear-probe（MEDIC 6→5）",
                      "zero_shot": "CLIP：zero-shot 多 prompt"}.get(_m, _m)
            st.caption(f"🔎 {_label}")
```

- [ ] **Step 4: 啟動 app 確認語法與選單正常**

Run（背景啟動數秒後關閉，確認無 import/語法錯誤）：
```bash
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('app.py syntax OK')"
```
Expected: 印出 `app.py syntax OK`。

- [ ] **Step 5: 全測試回歸**

Run:
```bash
python -m pytest tests/ -v
```
Expected: 7 passed。

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: app 選單接入 CLIP linear-probe（預設）並保留 zero-shot 退路，UI 標示路徑"
```

---

## Task 7: 手動煙霧測試（驗證真正跑得動）

**Files:** 無（純執行驗證）

- [ ] **Step 1: 用一張測試圖跑 linear probe，確認端到端可推論**

> 注意：此步會載入 CLIP ViT-L/14（首次可能下載約 890MB），時間較長屬正常。

建立暫時腳本 `_smoke.py`（驗證後刪除）：
```python
from PIL import Image
from models.clip_classifier import classify_clip, linear_probe_available

print("linear_probe_available:", linear_probe_available())
# 換成專案內任一張存在的測試圖路徑
img = Image.open("static/sample.jpg").convert("RGB")
out = classify_clip(img, prefer_probe=True)
print("method:", out["method"])
print("top:", out["top_class_zh"], round(out["confidence"], 3))
print("all_scores:", {k: round(v, 3) for k, v in out["all_scores"].items()})
assert out["method"] == "linear_probe"
assert len(out["all_scores"]) == 5
print("OK")
```

Run（若 `static/sample.jpg` 不存在，改成任一張實際存在的圖片路徑）：
```bash
python _smoke.py
```
Expected: `linear_probe_available: True`、`method: linear_probe`、`all_scores` 含 5 類且總和約 1、最後印出 `OK`。

- [ ] **Step 2: 刪除暫時腳本**

Run:
```bash
rm _smoke.py
```

- [ ] **Step 3: 最終全測試 + 確認工作區乾淨**

Run:
```bash
python -m pytest tests/ -v && git status --short
```
Expected: 7 passed；`git status` 無未預期的殘留檔案（`_smoke.py` 已刪）。

---

## 完成定義

- `models/clip_linear_head.pth` 被 git 追蹤，`_load_linear_head()` 能切片成 5 類。
- `classify_clip(prefer_probe=True)` 預設走 linear probe、失敗自動退回 zero-shot。
- app.py 選單 4 項可切換，雙主投票 / need_review 邏輯不變，UI 顯示 CLIP 實際路徑。
- `tests/` 全綠（7 passed），煙霧測試端到端通過。
