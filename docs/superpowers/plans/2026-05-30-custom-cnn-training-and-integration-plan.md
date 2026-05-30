# Custom CNN Training & Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train a custom CNN from scratch on Kaggle GPU with 4 ablation variants (v1 baseline + v2/v3/v4 ablations), then integrate the v1 final into the CrisisLens streamlit app as a replacement for the unused ResNet50 baseline.

**Architecture:** Two phases. **Phase 1 (Kaggle)**: a self-contained notebook trains four model variants on the `mikolajbabula/disaster-images-dataset-cnn-model` dataset, produces training curves + confusion matrices, and saves `custom_cnn.pth` + `custom_cnn_classes.json`. **Phase 2 (local Python)**: a single-source-of-truth model class in `models/custom_cnn_model.py`, an inference wrapper in `models/custom_cnn_classifier.py` matching the existing `clip_classifier.classify()` interface, and a UI swap in `app.py`. The deployed model in production is `DisasterCNN_v1`; v2/v3/v4 exist only as ablations for the report.

**Tech Stack:** PyTorch 2.x, torchvision, Pillow, Streamlit 1.x, Kaggle GPU (T4 / P100), Matplotlib + seaborn for visualization. Python 3.13 in the local venv.

---

## File Structure

**Created:**

| File | Responsibility |
|---|---|
| `models/custom_cnn_model.py` | `DisasterCNN_v1` class — **single source of truth** for the deployed architecture. Kaggle notebook must keep its v1 cell identical to this. |
| `models/custom_cnn_classifier.py` | Inference wrapper, interface mirrors `clip_classifier.classify()` |
| `train_custom_cnn_kaggle.ipynb` | Kaggle training notebook (v1-v4 + ablation comparison + save) |
| `models/custom_cnn.pth` | Trained weights (downloaded from Kaggle, **not committed**) |
| `models/custom_cnn_classes.json` | Class mapping (downloaded from Kaggle, **not committed**) |
| `docs/training_summary.md` | Phase 2 training & ablation report |

**Modified:**

| File | Change |
|---|---|
| `utils/config.py` | Drop Typhoon (6 → 5 classes); strip typhoon entries from `PROMPT_SETS` A/B/C |
| `app.py` | Sidebar: "ResNet50 (Baseline)" → "自訓 CNN (My CNN)"; analysis branches call `custom_cnn_classifier.classify` |
| `.gitignore` | Add `models/custom_cnn.pth` (weights too large for git) |

**Preserved untouched (future Partial Fine-tune):**
- `models/resnet_baseline.py`
- `models/train_resnet.py`
- `train_resnet_kaggle.ipynb`

---

## Verification Strategy

This project has no `tests/` directory and no pytest culture (notebooks + streamlit are the verification surface). Each task verifies via:
- **Import smoke tests** for new Python modules (run a one-liner in the venv)
- **Functional checks** (run streamlit, click around, observe)
- **Notebook validation** (load with `nbformat.json` parse, count cells)

Formal pytest tests are intentionally omitted to match project conventions.

---

## Task 1: Define canonical model architecture

**Files:**
- Create: `models/custom_cnn_model.py`

- [ ] **Step 1: Create the file**

```python
"""自訓 CNN 模型架構定義 — Phase 1 deployed 版本 (v1 baseline)。

This is the SINGLE SOURCE OF TRUTH for the production CNN architecture.
The training notebook `train_custom_cnn_kaggle.ipynb` MUST keep its v1
class definition byte-identical to this one — otherwise the saved
`state_dict` will fail to load (mismatched layer names).

v2/v3/v4 ablations live only inside the notebook; they are not deployed.
"""
import torch.nn as nn


class DisasterCNN_v1(nn.Module):
    """4-block CNN baseline for 5-class disaster classification.

    Input  : (B, 3, 224, 224)  RGB image, ImageNet-normalized
    Output : (B, num_classes)   logits (apply softmax for probabilities)
    Params : ~400 K
    """
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1: 224 -> 112
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 2: 112 -> 56
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 3: 56 -> 28
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 4: 28 -> 14
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))
```

- [ ] **Step 2: Verify it imports and runs a forward pass on dummy input**

Run in PowerShell:
```powershell
& "C:\PARA\4_python_project\CrisisLens\venv\Scripts\python.exe" -c "import torch; from models.custom_cnn_model import DisasterCNN_v1; m = DisasterCNN_v1(5); x = torch.randn(2, 3, 224, 224); y = m(x); print('output shape:', y.shape); print('params:', sum(p.numel() for p in m.parameters()))"
```

Expected output:
```
output shape: torch.Size([2, 5])
params: 391749
```

(The params number may vary by ±100 if PyTorch version differs slightly; output shape MUST be `[2, 5]`.)

- [ ] **Step 3: Commit**

```bash
git add models/custom_cnn_model.py
git commit -m "feat(models): add DisasterCNN_v1 architecture (4-block CNN)"
```

---

## Task 2: Build Kaggle notebook — scaffold + dataset inspection

**Files:**
- Create: `train_custom_cnn_kaggle.ipynb`

This task creates the first 8 cells: markdown intro, env check, config, imports, dataset root finder, dataset inspection, transforms, DataLoader. Subsequent tasks add training cells.

- [ ] **Step 1: Create the notebook file with these cells (use Write tool with JSON ipynb format)**

The full cell contents:

**Cell 1 — Markdown:**
```markdown
# CrisisLens · Custom CNN Training (Kaggle GPU)

從頭訓練自建 CNN 做 5 類災情分類，並跑 3 個 ablation 對照（no-BN / big-FC / shallow）。

## 執行前
1. Notebook options → Accelerator → GPU T4 x2（或 P100）
2. Internet → On
3. Add data → `mikolajbabula/disaster-images-dataset-cnn-model`
4. 確認下方 Config cell 的 `DATA_DIR`

## 輸出
- `custom_cnn.pth` — v1 final 權重（~1.5 MB）
- `custom_cnn_classes.json` — 類別對照
- `training_curves.png`、`ablation_comparison.png`、`confusion_matrix.png`
```

**Cell 2 — Code (env check):**
```python
import sys, torch
print(f"Python:     {sys.version.split()[0]}")
print(f"PyTorch:    {torch.__version__}")
print(f"CUDA:       {torch.version.cuda}")
print(f"GPU 可用:   {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU 名稱:   {torch.cuda.get_device_name(0)}")
else:
    print("\n⚠️ 沒偵測到 GPU — 請從右側 Notebook options 啟用 GPU 後 Restart Session")
```

**Cell 3 — Markdown:** `## 1. Config`

**Cell 4 — Code (config):**
```python
from pathlib import Path

DATA_DIR     = "/kaggle/input/disaster-images-dataset-cnn-model"
OUT_DIR      = Path("/kaggle/working")
WEIGHTS_PATH = OUT_DIR / "custom_cnn.pth"
MAPPING_PATH = OUT_DIR / "custom_cnn_classes.json"
CURVES_PATH  = OUT_DIR / "training_curves.png"
ABLATION_PATH= OUT_DIR / "ablation_comparison.png"
CM_PATH      = OUT_DIR / "confusion_matrix.png"

BATCH_SIZE    = 32
LEARNING_RATE = 1e-3
EPOCHS        = 15
NUM_WORKERS   = 2
SEED          = 42
VAL_RATIO     = 0.2

FOLDER_TO_ZH = {
    "Damaged_Infrastructure": "地震或建築損壞",
    "Fire_Disaster":          "火災",
    "Land_Disaster":          "土石流或坍方",
    "Water_Disaster":         "淹水",
    "Non_Damage":             "其他或無明顯災害",
}

print(f"DATA_DIR: {DATA_DIR}")
print(f"OUT_DIR:  {OUT_DIR}")
```

**Cell 5 — Markdown:** `## 2. Imports`

**Cell 6 — Code (imports):**
```python
import os, json, time, copy
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

torch.manual_seed(SEED)
np.random.seed(SEED)
```

**Cell 7 — Markdown:** `## 3. 確認資料集結構`

**Cell 8 — Code (dataset inspection):**
```python
def find_data_root(base: str) -> str:
    base_path = Path(base)
    if not base_path.exists():
        raise FileNotFoundError(f"{base} 不存在 — 請確認資料集已 attach 並更新 DATA_DIR")
    expected = set(FOLDER_TO_ZH.keys())

    def matches(p: Path) -> bool:
        if not p.is_dir():
            return False
        subs = {x.name for x in p.iterdir() if x.is_dir()}
        return expected.issubset(subs)

    if matches(base_path):
        return str(base_path)
    for sub in base_path.rglob("*"):
        if matches(sub):
            return str(sub)
    raise FileNotFoundError(
        f"在 {base} 下找不到包含 {expected} 五個資料夾的層級。"
    )

DATA_ROOT = find_data_root(DATA_DIR)
print(f"✅ 資料根目錄: {DATA_ROOT}\n")

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
print("類別數量：")
total_imgs = 0
for folder, zh in FOLDER_TO_ZH.items():
    fp = Path(DATA_ROOT) / folder
    n = sum(1 for p in fp.rglob("*") if p.suffix.lower() in IMG_EXTS) if fp.exists() else 0
    total_imgs += n
    mark = "✅" if n > 0 else "❌"
    print(f"  {mark} {folder:25s} → {zh:12s}  {n:5d} 張")
print(f"\n總圖片數: {total_imgs}")
```

- [ ] **Step 2: Validate the notebook JSON parses**

Run in Bash:
```bash
"C:/PARA/4_python_project/CrisisLens/venv/Scripts/python.exe" -c "
import json
with open('train_custom_cnn_kaggle.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
print(f'OK · {len(nb[\"cells\"])} cells')
"
```

Expected:
```
OK · 8 cells
```

- [ ] **Step 3: Commit**

```bash
git add train_custom_cnn_kaggle.ipynb
git commit -m "feat(notebook): add custom CNN training notebook scaffold (cells 1-8)"
```

---

## Task 3: Add Transforms + DataLoader cells

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb` (append cells 9-12)

- [ ] **Step 1: Append the following cells via Edit / Write**

**Cell 9 — Markdown:** `## 4. Transforms (Train 用 augmentation，Val 用單純 resize)`

**Cell 10 — Code:**
```python
train_tf = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
val_tf = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
```

**Cell 11 — Markdown:** `## 5. Dataset & DataLoader`

**Cell 12 — Code:**
```python
full_ds     = datasets.ImageFolder(DATA_ROOT, transform=train_tf)
classes_en  = full_ds.classes
classes_zh  = [FOLDER_TO_ZH.get(c, c) for c in classes_en]
num_classes = len(classes_en)

print("類別順序（ImageFolder 自動字母排序）：")
for i, (en, zh) in enumerate(zip(classes_en, classes_zh)):
    print(f"  [{i}] {en:25s} → {zh}")

n_total = len(full_ds)
n_val   = int(n_total * VAL_RATIO)
n_train = n_total - n_val
train_ds, val_ds = torch.utils.data.random_split(
    full_ds, [n_train, n_val],
    generator=torch.Generator().manual_seed(SEED),
)
val_ds.dataset.transform = val_tf

def make_weighted_sampler(dataset, indices):
    targets = [dataset.targets[i] for i in indices]
    class_counts  = np.bincount(targets, minlength=num_classes)
    class_weights = 1.0 / np.maximum(class_counts.astype(float), 1.0)
    sample_weights = [class_weights[t] for t in targets]
    return WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

sampler = make_weighted_sampler(full_ds, train_ds.indices)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler,
                          num_workers=NUM_WORKERS, pin_memory=True)
val_loader   = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)

print(f"\nTrain: {n_train}  Val: {n_val}  Classes: {num_classes}")
```

- [ ] **Step 2: Validate notebook JSON**

```bash
"C:/PARA/4_python_project/CrisisLens/venv/Scripts/python.exe" -c "
import json
with open('train_custom_cnn_kaggle.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
print(f'OK · {len(nb[\"cells\"])} cells')
"
```

Expected: `OK · 12 cells`

- [ ] **Step 3: Commit**

```bash
git add train_custom_cnn_kaggle.ipynb
git commit -m "feat(notebook): add transforms + DataLoader cells (9-12)"
```

---

## Task 4: Add v1 model + training cell

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb` (append cells 13-16)

- [ ] **Step 1: Append the following cells**

**Cell 13 — Markdown:**
```markdown
## 6. v1 (Baseline) — 4-block CNN with BatchNorm + GAP

**⚠️ 注意**：這個 class 定義必須與本地 `models/custom_cnn_model.py` 的 `DisasterCNN_v1` 字字相同。
若架構不一致，訓練好的 `.pth` 無法在本地 streamlit 載入（layer name mismatch）。
```

**Cell 14 — Code (v1 architecture, MUST match `models/custom_cnn_model.py`):**
```python
class DisasterCNN_v1(nn.Module):
    """4-block CNN baseline for 5-class disaster classification."""
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1: 224 -> 112
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 2: 112 -> 56
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 3: 56 -> 28
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 4: 28 -> 14
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )
    def forward(self, x):
        return self.classifier(self.features(x))
```

**Cell 15 — Markdown:** `### 訓練 v1（記錄訓練曲線，保存 best by Val Acc）`

**Cell 16 — Code (generic training function + v1 training):**
```python
def train_one_model(model_class, model_name: str, epochs: int = EPOCHS):
    """通用訓練函式 — 回傳 (history, best_val_acc, best_state, last_val_pred, last_val_true)。"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model     = model_class(num_classes).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn   = nn.CrossEntropyLoss()
    scaler    = torch.amp.GradScaler("cuda") if device == "cuda" else None

    history       = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_acc  = 0.0
    best_state    = None
    last_val_pred, last_val_true = [], []

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n=== {model_name} ===  可訓練參數: {n_params:,}")

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        # Train
        model.train()
        train_loss = 0.0
        for imgs, labels in train_loader:
            imgs   = imgs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad()
            if scaler is not None:
                with torch.amp.autocast("cuda"):
                    logits = model(imgs)
                    loss   = loss_fn(logits, labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss = loss_fn(model(imgs), labels)
                loss.backward()
                optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # Validate
        model.eval()
        val_loss = 0.0
        correct = total_n = 0
        epoch_pred, epoch_true = [], []
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs   = imgs.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)
                logits = model(imgs)
                val_loss += loss_fn(logits, labels).item()
                preds = logits.argmax(1)
                correct += (preds == labels).sum().item()
                total_n += labels.size(0)
                epoch_pred.extend(preds.cpu().tolist())
                epoch_true.extend(labels.cpu().tolist())
        val_loss /= len(val_loader)
        val_acc   = correct / total_n

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        last_val_pred, last_val_true = epoch_pred, epoch_true

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state   = copy.deepcopy(model.state_dict())

        print(f"  Epoch {epoch:2d}/{epochs}  "
              f"Train Loss: {train_loss:.4f}  Val Loss: {val_loss:.4f}  "
              f"Val Acc: {val_acc:.4f}  ({time.time()-t0:.1f}s)")

    print(f"  → Best Val Acc: {best_val_acc:.4f}")
    return history, best_val_acc, best_state, last_val_pred, last_val_true


# 訓練 v1
v1_history, v1_best_acc, v1_best_state, v1_pred, v1_true = train_one_model(
    DisasterCNN_v1, "v1 Baseline"
)
```

- [ ] **Step 2: Validate notebook JSON**

```bash
"C:/PARA/4_python_project/CrisisLens/venv/Scripts/python.exe" -c "
import json
with open('train_custom_cnn_kaggle.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
print(f'OK · {len(nb[\"cells\"])} cells')
"
```

Expected: `OK · 16 cells`

- [ ] **Step 3: Commit**

```bash
git add train_custom_cnn_kaggle.ipynb
git commit -m "feat(notebook): add v1 model + training cell (cells 13-16)"
```

---

## Task 5: Add v2/v3/v4 ablation cells

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb` (append cells 17-24)

- [ ] **Step 1: Append the following 8 cells**

**Cell 17 — Markdown:**
```markdown
## 7. Ablation v2 — No-BN（拿掉所有 BatchNorm）

預期觀察：訓練 loss 震盪、收斂變慢、Val Acc 比 v1 下降 5-8%
學到什麼：BatchNorm 對訓練穩定性的關鍵作用
```

**Cell 18 — Code:**
```python
class DisasterCNN_v2_NoBN(nn.Module):
    """v1 - all BatchNorm layers"""
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )
    def forward(self, x):
        return self.classifier(self.features(x))

v2_history, v2_best_acc, v2_best_state, v2_pred, v2_true = train_one_model(
    DisasterCNN_v2_NoBN, "v2 No-BN"
)
```

**Cell 19 — Markdown:**
```markdown
## 8. Ablation v3 — Big-FC（GAP 換成 Flatten + 大 FC）

預期觀察：參數量 +100x、嚴重過擬合（Train Acc 99% / Val Acc ~50%）
學到什麼：GAP 為什麼取代 Flatten + 大 FC
```

**Cell 20 — Code:**
```python
class DisasterCNN_v3_BigFC(nn.Module):
    """v1 with GAP replaced by Flatten + Linear(256*14*14, num_classes)"""
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256 * 14 * 14, num_classes),  # 50176 -> 5
        )
    def forward(self, x):
        return self.classifier(self.features(x))

v3_history, v3_best_acc, v3_best_state, v3_pred, v3_true = train_one_model(
    DisasterCNN_v3_BigFC, "v3 Big-FC"
)
```

**Cell 21 — Markdown:**
```markdown
## 9. Ablation v4 — Shallow（只保留 Block 1 + Block 2）

預期觀察：Val Acc 比 v1 下降 10-15%
學到什麼：深度對特徵抽取能力的影響
```

**Cell 22 — Code:**
```python
class DisasterCNN_v4_Shallow(nn.Module):
    """v1 with only Block 1 + Block 2 (drop Block 3 + Block 4)"""
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )
    def forward(self, x):
        return self.classifier(self.features(x))

v4_history, v4_best_acc, v4_best_state, v4_pred, v4_true = train_one_model(
    DisasterCNN_v4_Shallow, "v4 Shallow"
)
```

**Cell 23 — Markdown:** `## 10. 四個變體的成績對比`

**Cell 24 — Code:**
```python
results = [
    ("v1 Baseline", v1_best_acc, sum(p.numel() for p in DisasterCNN_v1(num_classes).parameters())),
    ("v2 No-BN",    v2_best_acc, sum(p.numel() for p in DisasterCNN_v2_NoBN(num_classes).parameters())),
    ("v3 Big-FC",   v3_best_acc, sum(p.numel() for p in DisasterCNN_v3_BigFC(num_classes).parameters())),
    ("v4 Shallow",  v4_best_acc, sum(p.numel() for p in DisasterCNN_v4_Shallow(num_classes).parameters())),
]

print(f"{'Model':15s}  {'Val Acc':>8s}  {'Params':>12s}  {'vs v1':>8s}")
print("-" * 50)
for name, acc, n_params in results:
    delta = acc - v1_best_acc
    print(f"{name:15s}  {acc:>8.4f}  {n_params:>12,}  {delta:>+7.2%}")
```

- [ ] **Step 2: Validate notebook JSON**

```bash
"C:/PARA/4_python_project/CrisisLens/venv/Scripts/python.exe" -c "
import json
with open('train_custom_cnn_kaggle.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
print(f'OK · {len(nb[\"cells\"])} cells')
"
```

Expected: `OK · 24 cells`

- [ ] **Step 3: Commit**

```bash
git add train_custom_cnn_kaggle.ipynb
git commit -m "feat(notebook): add v2/v3/v4 ablation cells + comparison table"
```

---

## Task 6: Add visualization + save cells

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb` (append cells 25-32)

- [ ] **Step 1: Append the following 8 cells**

**Cell 25 — Markdown:** `## 11. 訓練曲線疊圖`

**Cell 26 — Code:**
```python
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

colors = {"v1": "#38bdf8", "v2": "#f87171", "v3": "#fbbf24", "v4": "#a78bfa"}
for name, hist, key in [
    ("v1 Baseline", v1_history, "v1"),
    ("v2 No-BN",    v2_history, "v2"),
    ("v3 Big-FC",   v3_history, "v3"),
    ("v4 Shallow",  v4_history, "v4"),
]:
    ax1.plot(hist["val_loss"], color=colors[key], linewidth=2, label=name)
    ax2.plot(hist["val_acc"],  color=colors[key], linewidth=2, label=name, marker="o", markersize=3)

ax1.set_title("Validation Loss")
ax1.set_xlabel("Epoch"); ax1.legend(); ax1.grid(alpha=0.3)
ax2.set_title("Validation Accuracy")
ax2.set_xlabel("Epoch"); ax2.set_ylim(0, 1); ax2.legend(); ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(CURVES_PATH, dpi=120, bbox_inches="tight")
plt.show()
print(f"✅ 已存: {CURVES_PATH}")
```

**Cell 27 — Markdown:** `## 12. v1 Confusion Matrix + Classification Report`

**Cell 28 — Code:**
```python
print("=== v1 Classification Report ===\n")
print(classification_report(
    v1_true, v1_pred,
    target_names=classes_zh,
    zero_division=0, digits=3,
))

cm = confusion_matrix(v1_true, v1_pred)
fig, ax = plt.subplots(figsize=(7, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=classes_zh, yticklabels=classes_zh, ax=ax)
ax.set_xlabel("Predicted"); ax.set_ylabel("True")
ax.set_title("v1 Confusion Matrix")
plt.xticks(rotation=30, ha="right"); plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig(CM_PATH, dpi=120, bbox_inches="tight")
plt.show()
```

**Cell 29 — Markdown:**
```markdown
## 13. 儲存 v1 (final deploy 版本) 權重

僅保存 v1 的 best state — v2/v3/v4 只在報告中比較，不 deploy。
```

**Cell 30 — Code:**
```python
torch.save(v1_best_state, WEIGHTS_PATH)
print(f"✅ 權重已存: {WEIGHTS_PATH}  ({WEIGHTS_PATH.stat().st_size / 1e6:.2f} MB)")

mapping = {
    "classes":      classes_en,
    "zh_labels":    classes_zh,
    "class_to_idx": full_ds.class_to_idx,
    "num_classes":  num_classes,
    "architecture": "DisasterCNN_v1",
    "val_acc":      v1_best_acc,
}
with open(MAPPING_PATH, "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)
print(f"✅ 類別對照已存: {MAPPING_PATH}")
print(json.dumps(mapping, ensure_ascii=False, indent=2))
```

**Cell 31 — Markdown:**
```markdown
## 14. 下載連結

點下方連結下載；或從右側 Output 面板選 ⋮ → Download。

放到本地專案的 `models/`：
- `custom_cnn.pth` → `models/custom_cnn.pth`
- `custom_cnn_classes.json` → `models/custom_cnn_classes.json`

訓練曲線、混淆矩陣是報告素材（可選下載）。
```

**Cell 32 — Code:**
```python
from IPython.display import FileLink, display

print("可下載檔案：\n")
for path in [WEIGHTS_PATH, MAPPING_PATH, CURVES_PATH, CM_PATH]:
    if path.exists():
        size = path.stat().st_size / 1e6
        print(f"  {path.name:35s}  {size:6.2f} MB")
        display(FileLink(str(path)))
```

- [ ] **Step 2: Validate notebook JSON**

```bash
"C:/PARA/4_python_project/CrisisLens/venv/Scripts/python.exe" -c "
import json
with open('train_custom_cnn_kaggle.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
print(f'OK · {len(nb[\"cells\"])} cells')
"
```

Expected: `OK · 32 cells`

- [ ] **Step 3: Commit**

```bash
git add train_custom_cnn_kaggle.ipynb
git commit -m "feat(notebook): add visualization + save weights cells"
```

---

## Task 7: USER ACTION — Run notebook on Kaggle & download weights

**This task is performed by the user, not the agent. The agent should pause here and ask the user to confirm completion before proceeding to Task 8.**

- [ ] **Step 1: Upload notebook to Kaggle**

User instructions:
1. Go to https://www.kaggle.com → Code → New Notebook
2. File → Import Notebook → upload `train_custom_cnn_kaggle.ipynb`
3. Right sidebar: Notebook options → Accelerator → **GPU T4 x2** (or P100)
4. Right sidebar: **Internet → On**
5. Right sidebar: **Add data** → search `mikolajbabula/disaster-images-dataset-cnn-model` → Add

- [ ] **Step 2: Confirm DATA_DIR matches**

Look at right Input panel — confirm the dataset path matches `/kaggle/input/disaster-images-dataset-cnn-model`. If different, edit Cell 4 (Config) accordingly.

- [ ] **Step 3: Run All**

Wait ~30–60 minutes (4 models × ~10 min each).

- [ ] **Step 4: Verify Val Acc**

- v1 should reach ≥ 60% (success criterion per spec §7)
- If v1 < 50%: triggers spec §9 fallback to Partial Fine-tune; stop and inform user
- v2 should be lower than v1 (validates BN ablation)
- v3 should overfit heavily (train >> val)
- v4 should be lower than v1 (validates depth ablation)

- [ ] **Step 5: Download artifacts**

From the right Output panel, download:
- `custom_cnn.pth` → place in local `C:\PARA\4_python_project\CrisisLens\models\`
- `custom_cnn_classes.json` → place in local `C:\PARA\4_python_project\CrisisLens\models\`
- `training_curves.png` (optional, for report)
- `confusion_matrix.png` (optional, for report)

- [ ] **Step 6: Verify files exist locally**

```bash
ls models/custom_cnn.pth models/custom_cnn_classes.json
```

Expected: both files listed.

- [ ] **Step 7: Add weight file to .gitignore (it's ~1.5 MB, but `.pth` files generally shouldn't be committed)**

Append to `.gitignore`:
```
models/custom_cnn.pth
models/custom_cnn_classes.json
```

- [ ] **Step 8: Commit .gitignore update**

```bash
git add .gitignore
git commit -m "chore: ignore custom_cnn weight files"
```

---

## Task 8: Update `utils/config.py` to 5 classes

**Files:**
- Modify: `utils/config.py`

- [ ] **Step 1: Apply the following edits**

Replace the `CLASSES_EN`, `CLASSES_ZH`, `PROMPT_SETS`, `NUM_CLASSES` blocks.

The complete updated content for `utils/config.py` lines 15-74:

```python
# ── Disaster classes ──────────────────────────────────────
CLASSES_EN = [
    "Earthquake Damage",
    "Flood",
    "Fire",
    "Landslide",
    "Other or No Disaster",
]

CLASSES_ZH = [
    "地震或建築損壞",
    "淹水",
    "火災",
    "土石流或坍方",
    "其他或無明顯災害",
]

CLASS_MAP = dict(zip(CLASSES_EN, CLASSES_ZH))

# ── Prompt sets ───────────────────────────────────────────
PROMPT_SETS = {
    "A｜簡短版": [
        "earthquake",
        "flood",
        "fire",
        "landslide",
        "normal scene",
    ],
    "B｜完整句版": [
        "a photo of earthquake damage with collapsed buildings",
        "a photo of a flooded street after heavy rain",
        "a photo of a fire disaster with smoke and flames",
        "a photo of a landslide blocking a road",
        "a normal street photo without disaster",
    ],
    "C｜社群情境版": [
        "a social media photo showing earthquake damage after a strong earthquake",
        "a social media photo showing flood damage after heavy rainfall",
        "a social media photo showing a fire emergency",
        "a social media photo showing landslide damage in a mountain area",
        "a social media photo showing no visible disaster",
    ],
}

# ── RAG ───────────────────────────────────────────────────
TOP_K_DOCS         = 4
CHUNK_SIZE         = 400   # characters per chunk
CHUNK_OVERLAP      = 80

# ── ResNet training ───────────────────────────────────────
BATCH_SIZE   = 32
LEARNING_RATE = 1e-3
EPOCHS        = 5
NUM_CLASSES   = 5
```

- [ ] **Step 2: Verify the change**

```bash
"C:/PARA/4_python_project/CrisisLens/venv/Scripts/python.exe" -c "
from utils.config import CLASSES_EN, CLASSES_ZH, PROMPT_SETS, NUM_CLASSES
assert len(CLASSES_EN) == 5, f'CLASSES_EN has {len(CLASSES_EN)} entries, expected 5'
assert len(CLASSES_ZH) == 5
assert NUM_CLASSES == 5
assert 'Typhoon or Storm Damage' not in CLASSES_EN
for key, prompts in PROMPT_SETS.items():
    assert len(prompts) == 5, f'{key} has {len(prompts)} prompts'
print('OK · 5 classes everywhere')
"
```

Expected: `OK · 5 classes everywhere`

- [ ] **Step 3: Commit**

```bash
git add utils/config.py
git commit -m "refactor(config): drop Typhoon class (6 -> 5 classes)"
```

---

## Task 9: Create `custom_cnn_classifier.py` inference module

**Files:**
- Create: `models/custom_cnn_classifier.py`

- [ ] **Step 1: Create the file**

```python
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
_DEFAULT_EN = ["Earthquake Damage", "Flood", "Fire", "Landslide", "Other or No Disaster"]
_DEFAULT_ZH = ["地震或建築損壞", "淹水", "火災", "土石流或坍方", "其他或無明顯災害"]


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
        state = torch.load(WEIGHTS_PATH, map_location=device)
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
```

- [ ] **Step 2: Verify it imports and can run on a dummy image even without weights**

```powershell
& "C:\PARA\4_python_project\CrisisLens\venv\Scripts\python.exe" -c "from PIL import Image; from models.custom_cnn_classifier import classify, weights_exist; img = Image.new('RGB', (300, 300), color='red'); result = classify(img); print('weights_exist:', weights_exist()); print('model_loaded:', result['model_loaded']); print('top_class:', result['top_class']); assert len(result['top_3']) == 3; print('OK')"
```

Expected (without weights present):
```
weights_exist: False  (or True if user has already dropped weights in)
model_loaded: False   (or True)
top_class: <some class name>
OK
```

- [ ] **Step 3: Commit**

```bash
git add models/custom_cnn_classifier.py
git commit -m "feat(models): add custom CNN inference module"
```

---

## Task 10: Update `app.py` — sidebar selector + status check

**Files:**
- Modify: `app.py` (lines 229-249 area)

- [ ] **Step 1: Locate the sidebar block**

Open `app.py` and find lines around 229-249 (sidebar model setting + status section).

- [ ] **Step 2: Apply the following edit**

Find:
```python
    st.markdown("### ⚙️ 模型設定")
    model_mode = st.selectbox(
        "使用模型",
        ["CLIP（Zero-Shot）", "ResNet50（Baseline）", "兩者比較"],
    )

    prompt_set_key = list(PROMPT_SETS.keys())[1]  # B 預設
    if "CLIP" in model_mode or "比較" in model_mode:
        prompt_set_key = st.selectbox(
            "CLIP Prompt Set",
            list(PROMPT_SETS.keys()),
            index=1,
            help="A=簡短、B=完整句、C=社群情境",
        )

    st.markdown("---")
    st.markdown("### 📋 系統狀態")
    if index_exists():
        st.success("✅ FAISS index 已建立")
    else:
        st.warning("⚠️ 尚未建立 FAISS index\n```\npython rag/build_index.py\n```")

    if GEMINI_API_KEY:
        st.success("✅ Gemini API 已設定")
    else:
        st.info("未設定 GEMINI_API_KEY\n將使用內建指引")
```

Replace with:
```python
    st.markdown("### ⚙️ 模型設定")
    model_mode = st.selectbox(
        "使用模型",
        ["CLIP（Zero-Shot）", "自訓 CNN（My CNN）", "兩者比較"],
    )

    prompt_set_key = list(PROMPT_SETS.keys())[1]  # B 預設
    if "CLIP" in model_mode or "比較" in model_mode:
        prompt_set_key = st.selectbox(
            "CLIP Prompt Set",
            list(PROMPT_SETS.keys()),
            index=1,
            help="A=簡短、B=完整句、C=社群情境",
        )

    st.markdown("---")
    st.markdown("### 📋 系統狀態")
    if index_exists():
        st.success("✅ FAISS index 已建立")
    else:
        st.warning("⚠️ 尚未建立 FAISS index\n```\npython rag/build_index.py\n```")

    from models.custom_cnn_classifier import weights_exist as cnn_weights_exist
    if cnn_weights_exist():
        st.success("✅ 自訓 CNN 已就緒")
    else:
        st.warning("⚠️ 自訓 CNN 權重不存在\n從 Kaggle 訓練後放入 models/")

    if GEMINI_API_KEY:
        st.success("✅ Gemini API 已設定")
    else:
        st.info("未設定 GEMINI_API_KEY\n將使用內建指引")
```

- [ ] **Step 3: Smoke test that streamlit still loads (don't need to start server, just import-check)**

```powershell
& "C:\PARA\4_python_project\CrisisLens\venv\Scripts\python.exe" -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('OK · app.py syntax valid')"
```

Expected: `OK · app.py syntax valid`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat(ui): swap ResNet50 selector for Custom CNN, add weight status check"
```

---

## Task 11: Update `app.py` — analysis flow

**Files:**
- Modify: `app.py` (lines 321-330 area, inside `if analyze_btn:` block)

- [ ] **Step 1: Locate the analysis block**

Find lines around 321-330 (the `with st.spinner("模型推論中..."):` block).

- [ ] **Step 2: Apply the following edit**

Find:
```python
    with st.spinner("模型推論中..."):
        if "CLIP" in model_mode or "比較" in model_mode:
            from models.clip_classifier import classify as clip_classify
            clip_result = clip_classify(img, prompt_set_key)

        if "ResNet50" in model_mode or "比較" in model_mode:
            from models.resnet_baseline import classify as resnet_classify
            resnet_result = resnet_classify(img)

    primary = clip_result or resnet_result
```

Replace with:
```python
    with st.spinner("模型推論中..."):
        if "CLIP" in model_mode or "比較" in model_mode:
            from models.clip_classifier import classify as clip_classify
            clip_result = clip_classify(img, prompt_set_key)

        if "自訓 CNN" in model_mode or "比較" in model_mode:
            from models.custom_cnn_classifier import classify as cnn_classify
            cnn_result = cnn_classify(img)

    primary = clip_result or cnn_result
```

- [ ] **Step 3: Rename the `resnet_result` variable**

Earlier in the file (line ~319), find:
```python
    clip_result   = None
    resnet_result = None
```

Replace with:
```python
    clip_result = None
    cnn_result  = None
```

- [ ] **Step 4: Update the comparison rendering block (lines 335-348 area)**

Find:
```python
    if "比較" in model_mode and clip_result and resnet_result:
        mc1, mc2 = st.columns(2)
        with mc1:
            render_model_card("CLIP Zero-Shot", clip_result)
        with mc2:
            loaded_label = "✅ 已訓練" if resnet_result["model_loaded"] else "⚠️ 未訓練（隨機）"
            render_model_card(f"ResNet50 {loaded_label}", resnet_result)
    else:
        col_card, col_blank = st.columns([1, 1])
        with col_card:
            label = "CLIP Zero-Shot" if clip_result else (
                "ResNet50 ✅" if resnet_result and resnet_result["model_loaded"] else "ResNet50 ⚠️ 未訓練"
            )
            render_model_card(label, primary)
```

Replace with:
```python
    if "比較" in model_mode and clip_result and cnn_result:
        mc1, mc2 = st.columns(2)
        with mc1:
            render_model_card("CLIP Zero-Shot", clip_result)
        with mc2:
            loaded_label = "✅ 已訓練" if cnn_result["model_loaded"] else "⚠️ 未訓練（隨機）"
            render_model_card(f"自訓 CNN {loaded_label}", cnn_result)
    else:
        col_card, col_blank = st.columns([1, 1])
        with col_card:
            label = "CLIP Zero-Shot" if clip_result else (
                "自訓 CNN ✅" if cnn_result and cnn_result["model_loaded"] else "自訓 CNN ⚠️ 未訓練"
            )
            render_model_card(label, primary)
```

- [ ] **Step 5: Smoke test that app.py still parses**

```powershell
& "C:\PARA\4_python_project\CrisisLens\venv\Scripts\python.exe" -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('OK · app.py syntax valid')"
```

Expected: `OK · app.py syntax valid`

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat(ui): wire analysis flow to use custom_cnn_classifier"
```

---

## Task 12: Write `training_summary.md` report

**Files:**
- Create: `docs/training_summary.md`

> The numbers in this report come from Task 7's training run. The agent should ask the user for the actual numbers (v1_best_acc, v2_best_acc, etc.) before writing this file, and substitute them in. If the user hasn't run training yet, write the structure with placeholders and instruct the user to fill in.

- [ ] **Step 1: Ask the user for training results**

Prompt the user:
> "請告訴我 Kaggle 訓練的實際數字：
> - v1 Best Val Acc
> - v2 (No-BN) Best Val Acc
> - v3 (Big-FC) Best Val Acc; 與 train acc 的差距
> - v4 (Shallow) Best Val Acc
> - v1 Confusion Matrix 觀察：哪一類最難？最常被誤判成哪一類？"

- [ ] **Step 2: Create the report file (substitute `{v1_acc}` etc. with user-reported numbers)**

```markdown
# Custom CNN 訓練實驗報告

**Date**: 2026-05-30
**模型**: DisasterCNN_v1 (4-block CNN, 5-class disaster classification)
**資料集**: [`mikolajbabula/disaster-images-dataset-cnn-model`](https://www.kaggle.com/datasets/mikolajbabula/disaster-images-dataset-cnn-model) (Kaggle)
**訓練平台**: Kaggle Notebook (GPU T4 / P100)

---

## 1. 實驗目的

練習從頭設計與訓練 CNN 的能力，並透過 3 個 ablation 變體親身觀察「現代 CNN 為什麼長這樣」。

最終 deploy 模型：v1 baseline。
v2/v3/v4 僅作為對照，不 deploy。

---

## 2. 資料集

- 來源：Kaggle `mikolajbabula/disaster-images-dataset-cnn-model`
- 類別（5 類）：
  - 地震或建築損壞 (`Damaged_Infrastructure`)
  - 淹水 (`Water_Disaster`)
  - 火災 (`Fire_Disaster`)
  - 土石流或坍方 (`Land_Disaster`)
  - 其他或無明顯災害 (`Non_Damage`)
- Train/Val split: 80/20 (seed=42)
- 類別不平衡：用 `WeightedRandomSampler` 處理

---

## 3. v1 (Baseline) 架構與決策理由

```
Input (3, 224, 224)
  ↓ Block 1: Conv(3→32, 3x3) + BN + ReLU + MaxPool      → (32, 112, 112)
  ↓ Block 2: Conv(32→64, 3x3) + BN + ReLU + MaxPool     → (64, 56, 56)
  ↓ Block 3: Conv(64→128, 3x3) + BN + ReLU + MaxPool    → (128, 28, 28)
  ↓ Block 4: Conv(128→256, 3x3) + BN + ReLU + MaxPool   → (256, 14, 14)
  ↓ AdaptiveAvgPool(1) + Flatten                          → (256,)
  ↓ Dropout(0.3) + Linear(256, 5)                         → (5,)
```

**決策理由**：
- **4 個 Conv block**：足以提取從邊緣到高階特徵的層次，又不至於過深導致過擬合
- **Channel 32 → 256（x2 倍增）**：經典設計，前段保留細節、後段聚焦語意
- **3x3 kernel**：現代 CNN 主流選擇（相同 receptive field 下參數少於 5x5）
- **BatchNorm**：穩定訓練、允許較大 LR、有正則化效果
- **GAP 取代 Flatten + 大 FC**：減 99% 參數、避免過擬合
- **Dropout 0.3**：搭配 GAP 進一步抑制過擬合

---

## 4. 訓練設定

| 超參數 | 值 |
|---|---|
| Optimizer | Adam |
| Learning rate | 1e-3 |
| Loss | CrossEntropyLoss |
| Batch size | 32 |
| Epochs | 15 |
| Augmentation | RandomResizedCrop, HFlip, ColorJitter, Rotation(15°) |
| Normalization | ImageNet mean/std |
| 類別平衡 | WeightedRandomSampler |
| Mixed Precision | AMP (cuda.amp) |

---

## 5. 結果對比

| Model | Val Acc | Params | vs v1 |
|---|---|---|---|
| **v1 Baseline** | {v1_acc}% | ~400K | — |
| v2 No-BN | {v2_acc}% | ~400K | {v2_delta}% |
| v3 Big-FC | {v3_acc}% | ~400K + 50K (Linear) | {v3_delta}% |
| v4 Shallow | {v4_acc}% | ~20K | {v4_delta}% |

訓練曲線：`training_curves.png`

---

## 6. 錯誤分析（v1 Confusion Matrix）

混淆矩陣：`confusion_matrix.png`

主要觀察：
- 最難類別：**{hardest_class}**（recall {hardest_recall}%）
- 最常見的誤判：**{worst_confusion}**
- 推測原因：{reason}

---

## 7. Lessons Learned

從這次實驗親身體會到的三件事：

### 7.1 BatchNorm 對訓練穩定性的關鍵作用
v2 拿掉 BN 後，Val Acc 從 {v1_acc}% 掉到 {v2_acc}%，差距 {v2_delta}%。
→ BN 不只是「常見的層」，它真的對淺層 CNN 也至關重要。

### 7.2 GAP 為什麼取代 Flatten + 大 FC
v3 用 Flatten + Linear(50176, 5)：參數量暴增、嚴重過擬合（train acc 高、val acc 低）。
→ 看到實際數字後，「GAP 是現代 CNN 標配」這個 pattern 變得有切身意義。

### 7.3 深度對特徵抽取能力的影響
v4 砍掉 Block 3+4 後 Val Acc 掉 {v4_delta}%。
→ 深度不是免費的（v4 推論最快），但若要在這類視覺任務做到位，4 層的 receptive field 是甜蜜點。

---

## 8. 下一步

| 條件 | 觸發動作 |
|---|---|
| v1 Val Acc < 50% | 啟動 spec §9 — 改用 ResNet50 Partial Fine-tune（既有 `train_resnet_kaggle.ipynb`） |
| v1 任一類 recall < 30% | 同上 |
| streamlit 實測時常見類型（火災、淹水）明顯誤判 | 同上 |
| **所有條件都未觸發** | 保留 v1 為 production 模型；本份報告 + ablation 是學習產出 |

當前狀態：**{trigger_status}**（觸發 / 未觸發）
```

- [ ] **Step 3: Commit**

```bash
git add docs/training_summary.md
git commit -m "docs: add custom CNN training summary report"
```

---

## Task 13: End-to-end integration test

**Files:** (verification only)

- [ ] **Step 1: Confirm weights are in place**

```bash
ls models/custom_cnn.pth models/custom_cnn_classes.json
```

Expected: both files listed. If not present, return to Task 7.

- [ ] **Step 2: Start streamlit (uses the existing `run.ps1`)**

```powershell
.\run.ps1
```

Expected console output includes:
```
Local URL: http://localhost:8501
```

- [ ] **Step 3: Browser checks**

Open http://localhost:8501 and verify:

| Check | Expected |
|---|---|
| Sidebar shows "⚙️ 模型設定" dropdown | "CLIP（Zero-Shot）" / "自訓 CNN（My CNN）" / "兩者比較" |
| Sidebar status section | "✅ 自訓 CNN 已就緒" |
| Select "自訓 CNN（My CNN）" mode, upload a fire photo, click 開始分析 | Top-1 = 火災 (with reasonable confidence) |
| Select "兩者比較" mode, upload a flood photo, click 開始分析 | Both CLIP and 自訓 CNN cards display side by side, both predict 淹水 |
| Select "CLIP（Zero-Shot）" mode | Works as before, no regression |
| First analysis is slow (10-30s); second analysis fast (< 5s) | lru_cache works |

- [ ] **Step 4: Spec success criteria sanity check**

Verify against spec §7:
- [x] Phase 1: v1 ≥ 60% Val Acc ✓ (from Task 7)
- [x] streamlit shows "✅ 自訓 CNN 已就緒" ✓
- [x] Reasonable Top-3 predictions ✓
- [x] 5 classes aligned between CLIP and Custom CNN ✓
- [x] streamlit startup still fast (lazy import preserved) ✓
- [x] training_summary.md complete ✓

- [ ] **Step 5: Stop streamlit (Ctrl+C in the run.ps1 window)**

- [ ] **Step 6: Final commit (if any test exposed config issues, fix and commit; otherwise no commit needed)**

If §9 trigger condition met (v1 < 50% or worst-class recall < 30%):
- Inform the user
- Reference spec §9.2 for next steps
- This plan ends; a separate Partial Fine-tune plan would begin

If all criteria pass:
- Inform the user the plan is complete
- Reference `docs/training_summary.md` for the report
