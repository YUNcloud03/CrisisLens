# 自訓 CNN 升級 6 類（MEDIC）並合併 Huang 分支 — 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 `feature/custom-cnn`（4 類 CNN）與 `Huang`（6 類 CLIP）合併為統一的 6 類體系，並把自訓 CNN 的 Kaggle 訓練 notebook 改寫成以 MEDIC 資料集訓練 6 類。

**Architecture:** 採 Huang 6 類 config 為準；自訓 CNN 與 CLIP（A/B/C/D/E）兩條分類路線在 app 中並存。訓練 notebook 用 HuggingFace `QCRI/MEDIC`（非串流下載）→ map-style `torch Dataset`（套 7→6 類 `MEDIC_MAP`）→ `WeightedRandomSampler` 處理不平衡 → v1～v4 ablation。

**Tech Stack:** Python、PyTorch、torchvision、HuggingFace `datasets`、Streamlit、CLIP（ViT-L/14）、Kaggle GPU（單顆 T4 + AMP）。

**對應設計文件：** [docs/superpowers/specs/2026-06-03-custom-cnn-6class-medic-design.md](../specs/2026-06-03-custom-cnn-6class-medic-design.md)

---

## 驗證策略說明（重要）

本專案是 Streamlit app + Kaggle notebook，**無既有單元測試框架**，且實際訓練在 Kaggle GPU 上由使用者執行。因此本計畫的「驗證」採務實做法，而非傳統 TDD：

- **Phase 1（合併）**：以 git 狀態檢查、Python import smoke test、`streamlit` 啟動檢查驗證。
- **Phase 2（notebook 改寫）**：以 notebook JSON 合法性 + Python 語法檢查（`python -m py_compile` 抽出的 cell 程式）驗證；完整執行由使用者在 Kaggle 進行。
- **Phase 3（整合）**：使用者訓練產出權重後，本地以 5 條推論路徑 smoke test 驗證。

每個 Task 的「Verify」步驟都會給出明確指令與預期輸出。

## 6 類正準順序（全計畫共用，禁止改動）

| index | CLASSES_EN | CLASSES_ZH | ← MEDIC `disaster_types` |
|---|---|---|---|
| 0 | Earthquake Damage | 地震或建築損壞 | `earthquake` |
| 1 | Flood | 淹水 | `flood` |
| 2 | Fire | 火災 | `fire` |
| 3 | Typhoon or Storm Damage | 颱風或強風災損 | `hurricane` |
| 4 | Landslide | 土石流或坍方 | `landslide` |
| 5 | Other or No Disaster | 其他或無明顯災害 | `not_disaster` + `other_disaster` |

## File Structure

| 檔案 | 動作 | 責任 |
|---|---|---|
| `utils/config.py` | 取代為 Huang 版 + 移除 `RESNET_WEIGHTS` | 6 類體系唯一事實來源 |
| `README.md` | 解 add/add 衝突（融合） | 專案說明，對齊 6 類 + ViT-L/14 |
| `app.py` | 採 merge 結果 + 複查 | CNN/CLIP 雙路線 UI 並存 |
| `models/custom_cnn_model.py` | 修改（預設 6、docstring） | 部署 CNN 架構唯一來源 |
| `models/custom_cnn_classifier.py` | 不改碼 | 讀 json 動態決定類別數；同時供分析頁主分類與通報頁輔助交叉驗證 |
| `pages/1_Submit_Report.py` | 輔助模型 ResNet→Custom CNN | CLIP 主判斷 + CNN 第二意見交叉驗證 |
| `utils/versions.py` | `RESNET_ENABLED/RESNET_MODEL_VERSION`→`CNN_AUX_ENABLED/CNN_MODEL_VERSION`；修正 `CLIP_MODEL_VERSION` | MLOps 版本旗標 |
| `models/resnet_baseline.py` / `models/train_resnet.py` | 刪除 | ResNet 推論/訓練（已由 CNN 取代） |
| `train_custom_cnn_kaggle.ipynb` | 原地改寫成 MEDIC 6 類 | Kaggle 訓練 notebook |
| `train_resnet_kaggle.ipynb` | 刪除 | （ResNet 已不用） |
| DB `resnet_*` 欄位 / `seed.py` | **保留不動** | 沿用儲存 CNN 輔助結果（零 schema 變動） |
| `models/custom_cnn.pth` | Phase 3 由使用者回放 | 6 類 v1 權重 |
| `models/custom_cnn_classes.json` | Phase 3 由使用者回放 | 6 類對照 |

---

# Phase 1 — 程式合併（本地，無需 GPU）

### Task 1: 開合併分支並執行 merge

**Files:**
- 無檔案編輯（git 操作）

- [ ] **Step 1: 確認工作區乾淨、在 feature/custom-cnn**

Run: `git status --short && git rev-parse --abbrev-ref HEAD`
Expected: 無輸出（乾淨）+ `feature/custom-cnn`

- [ ] **Step 2: 從 feature/custom-cnn 開合併分支**

```bash
git checkout -b merge/huang-6class
```
Expected: `Switched to a new branch 'merge/huang-6class'`

- [ ] **Step 3: 執行 merge（預期 README 衝突）**

```bash
git merge --no-commit --no-ff Huang
```
Expected: 出現 `CONFLICT (add/add): Merge conflict in README.md`，其餘檔案 auto-merged。`config.py` 不報衝突但內容是錯的（Phase 1 Task 2 處理）。

- [ ] **Step 4: 確認衝突範圍符合預期**

Run: `git diff --name-only --diff-filter=U`
Expected: 只有 `README.md`
若出現其他衝突檔，停下來人工檢視再繼續。

---

### Task 2: 解決 config.py（採 Huang 6 類 + 移除 RESNET_WEIGHTS）

**Files:**
- Modify: `utils/config.py`

- [ ] **Step 1: 用 Huang 版覆蓋 config.py**

```bash
git checkout Huang -- utils/config.py
```
Expected: 無輸出（成功）

- [ ] **Step 2: 確認 6 類定義正確**

Run: `git show Huang:utils/config.py | grep -nE "NUM_CLASSES|CLIP_MODEL_NAME"`
Expected: `CLIP_MODEL_NAME = "ViT-L/14"`、`NUM_CLASSES = 6`

- [ ] **Step 3: 檢查 RESNET_WEIGHTS 是否仍被引用**

Run: `grep -rn "RESNET_WEIGHTS" --include=*.py .`
Expected: 列出所有引用處。

- [ ] **Step 4: 移除 RESNET_WEIGHTS（僅當只剩 config.py 定義它）**

若 Step 3 只在 `utils/config.py` 出現，用 Edit 刪除該行：
```
RESNET_WEIGHTS    = "models/resnet50_linear.pth"
```
若 app.py 或其他檔仍 import 它，**先不要刪**，改在 Task 5 一併清理 ResNet 殘留後再回來刪。

- [ ] **Step 5: 加入暫存**

```bash
git add utils/config.py
```

---

### Task 3: 解決 README.md 衝突（以目前分支版為骨架融合）

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 採目前分支（591 行完整版）為基底**

```bash
git checkout --ours README.md
git add README.md
```
Expected: 衝突標記消除，README 變回 feature/custom-cnn 的完整版。

- [ ] **Step 2: 讀 README 找出需更正的事實**

Run: `grep -nE "ViT-B/32|ViT-B|4 類|四類|ResNet|Cyclone|Wildfire|custom_cnn" README.md`
逐處檢視。

- [ ] **Step 3: 做以下具體事實更正（用 Edit）**

- 模型名稱：所有 `ViT-B/32` → `ViT-L/14`
- 類別描述：所有「4 類 / 四類（Cyclone/Earthquake/Flood/Wildfire）」→「6 類（地震/淹水/火災/颱風/土石流/其他或無災害）」
- 移除或改寫 ResNet50 baseline 相關段落（app 已不用）

- [ ] **Step 4: 補入 Huang 版獨有段落**

在「模型 / 使用說明」相關章節後，新增以下段落（Huang README 的精華）：
```markdown
## CLIP Prompt Set 選項（A～E）

分析頁第二層下拉可選擇 CLIP 的分類策略：
- **A 簡短版 / B 詳細版 / C 情境版**：以不同 prompt 文字做 zero-shot 比對。
- **D 多描述投票**：每類用多句描述取平均相似度後投票（`MULTI_PROMPT_SETS`）。
- **E Linear Probe**：載入 `models/clip_linear_head.pth`（在 MEDIC 6 類上訓練的線性分類頭，輸入 768 維 CLIP 特徵），準確率最高。

### 權重與特徵檔取得
- `models/clip_linear_head.pth`：CLIP Linear Probe 權重（隨 repo 提供 / 或由 `notebooks/clip_linear_probe_medic.ipynb` 重訓）。
- `features/*.npz`：CLIP 特徵快取，已列入 `.gitignore`，需自行用 notebook 產生。
- ViT-L/14 首次使用會自動下載（較大），請確認環境資源。
```

- [ ] **Step 5: 加入暫存**

```bash
git add README.md
```

---

### Task 4: ResNet→Custom CNN 輔助模型替換 + 完整移除 ResNet 程式

**決策：** ResNet 權重不存在、輸出無人讀取、不決定分類；以 6 類 Custom CNN 取代它作為 Submit_Report 的「第二意見」交叉驗證模型。CLIP 仍是主判斷。**DB `resnet_*` 欄位沿用儲存 CNN 值（零 schema 變動）**。

**Files:**
- Modify: `pages/1_Submit_Report.py`、`utils/versions.py`、`utils/config.py`
- Delete: `train_resnet_kaggle.ipynb`、`models/resnet_baseline.py`、`models/train_resnet.py`
- **保留不動**：DB schema 的 `resnet_*` 欄位、`db/queries.py` 的 INSERT、`seed.py` 的 `resnet_*` key

- [ ] **Step 1: 刪除 ResNet 訓練 notebook 與推論/訓練程式**

```bash
git rm train_resnet_kaggle.ipynb models/resnet_baseline.py models/train_resnet.py
```
Expected: 三個檔被刪除。

- [ ] **Step 2: Submit_Report 改用 CNN 作輔助模型（用 Edit 逐處替換）**

a) import 行（約第 18、20 行）：`RESNET_MODEL_VERSION` → `CNN_MODEL_VERSION`、`RESNET_ENABLED` → `CNN_AUX_ENABLED`。

b) 輔助模型區塊（約第 188-199 行）整段換成：
```python
        # ── 輔助模型：自訓 CNN（第二意見交叉驗證，若權重存在）──────────
        cnn_type = cnn_zh = cnn_conf = cnn_ver = None
        if CNN_AUX_ENABLED:
            try:
                from models.custom_cnn_classifier import classify as cnn_classify, weights_exist
                if weights_exist():
                    c = cnn_classify(img)
                    cnn_type = c.get("top_class")
                    cnn_zh   = c.get("top_class_zh")   # 用中文標籤做比對
                    cnn_conf = c.get("confidence")
                    cnn_ver  = CNN_MODEL_VERSION
            except Exception:
                pass  # CNN 未訓練或出錯，靜默略過
```

c) 不一致判斷（約第 223-229 行）整段換成：
```python
        if cnn_zh and cnn_zh != clip_res["top_class_zh"]:
            model_agreement  = 0
            need_review_flag = 1
            review_reasons.append(
                f"兩模型結果不一致：CLIP＝**{clip_res['top_class_zh']}** vs "
                f"自訓 CNN＝**{cnn_zh or cnn_type}**"
            )
```

d) `insert_model_run` 的 dict（約第 270 行）：`"resnet_model_version": resnet_ver,` → `"resnet_model_version": cnn_ver,`（**保留 DB key 名，值改 cnn**）。

e) `full_report` 的 ResNet 區塊（約第 303-306 行）換成：
```python
            # 輔助模型：自訓 CNN（沿用 resnet_* 欄位儲存）
            "resnet_model_version":      cnn_ver,
            "resnet_disaster_type":      cnn_type,
            "resnet_confidence":         cnn_conf,
```

f) 結果顯示區塊（約第 343-351 行）換成：
```python
    # 自訓 CNN 輔助結果（若有）—— 全部顯示中文標籤
    if cnn_zh or cnn_type:
        agree_icon = "✅ 一致" if model_agreement else "⚠️ 不一致"
        cnn_display = cnn_zh or cnn_type
        st.info(
            f"**模型比對 {agree_icon}** ── "
            f"CLIP: **{clip_res['top_class_zh']}**（{clip_res['confidence']:.1%}）　"
            f"自訓 CNN: **{cnn_display}**（{cnn_conf:.1%}）"
        )
```

- [ ] **Step 3: utils/versions.py 改名旗標 + 修正 CLIP 版號（用 Edit）**

- `RESNET_MODEL_VERSION = "resnet50-linear-probe-v1"` → `CNN_MODEL_VERSION = "custom-cnn-medic-6class-v1"`
- `RESNET_ENABLED = True   # 是否啟用 ResNet50 輔助判斷` → `CNN_AUX_ENABLED = True   # 是否啟用自訓 CNN 輔助交叉驗證`
- `CLIP_MODEL_VERSION` 由 `"clip-vitb32-v1"` 改 `"clip-vitl14-v1"`

- [ ] **Step 4: utils/config.py 移除 RESNET_WEIGHTS**

確認沒有 .py 再引用後（resnet_baseline.py/train_resnet.py 已刪），用 Edit 刪除 `RESNET_WEIGHTS = "models/resnet50_linear.pth"` 行與其上方「# ── ResNet training ──」註解段（若該段已無內容）。

- [ ] **Step 5: 驗證 ResNet 已清除、CNN 已接上、語法 OK**

Run: `grep -rn "resnet\|RESNET\|ResNet" --include=*.py . | grep -v "db/\|seed.py"`
Expected: 只剩 `pages/1_Submit_Report.py` 內以 `resnet_*` 為 **DB dict key** 的那幾行（值來自 cnn）；不應再有 `import.*resnet_baseline`、`RESNET_ENABLED`、`RESNET_WEIGHTS`、`RESNET_MODEL_VERSION`。

Run: `python -c "import ast; ast.parse(open('pages/1_Submit_Report.py',encoding='utf-8').read()); ast.parse(open('utils/versions.py',encoding='utf-8').read()); print('語法 OK')"`
Expected: `語法 OK`

Run: `python -c "from utils.versions import CNN_AUX_ENABLED, CNN_MODEL_VERSION, CLIP_MODEL_VERSION; print(CNN_AUX_ENABLED, CNN_MODEL_VERSION, CLIP_MODEL_VERSION)"`
Expected: `True custom-cnn-medic-6class-v1 clip-vitl14-v1`

- [ ] **Step 6: README 調整（ResNet→CNN 輔助說明）**

把 README 中先前寫「移除 ResNet」或殘留的 ResNet 段落，改寫成「通報頁以自訓 CNN 作 CLIP 的第二意見交叉驗證（不一致則標記需人工審核）」。

- [ ] **Step 7: 加入暫存**

```bash
git add -A
```

---

### Task 5: app.py 複查 + 啟動 smoke test

**Files:**
- Verify: `app.py`

- [ ] **Step 1: 確認 CNN 與 CLIP 兩條分支都在**

Run: `grep -nE "cnn_classify|custom_cnn_classifier|classify_multi_prompt|classify_linear_probe|自訓 CNN" app.py`
Expected: 同時看到自訓 CNN 分支（`cnn_classify`）與 CLIP D/E 分支（`classify_multi_prompt`/`classify_linear_probe`），證明並存。

- [ ] **Step 2: Python import smoke test（不啟動 UI）**

Run: `python -c "import ast; ast.parse(open('app.py',encoding='utf-8').read()); print('app.py 語法 OK')"`
Expected: `app.py 語法 OK`

- [ ] **Step 3: config import 驗證 6 類**

Run: `python -c "from utils.config import CLASSES_EN, NUM_CLASSES, CLIP_MODEL_NAME; print(NUM_CLASSES, CLIP_MODEL_NAME); assert NUM_CLASSES==6 and len(CLASSES_EN)==6; print('OK')"`
Expected: `6 ViT-L/14` + `OK`

- [ ] **Step 4:（可選）啟動 streamlit 確認無 import 錯**

Run: `streamlit run app.py --server.headless true` 啟動數秒後 Ctrl+C
Expected: 啟動日誌無 traceback；CNN 因 6 類權重未生成顯示「未訓練（隨機）」屬正常。

---

### Task 6: 完成 Phase 1 合併 commit

- [ ] **Step 1: 檢視所有變更**

Run: `git status && git diff --cached --stat`
Expected: config.py、README.md、app.py（如有改）、刪除 train_resnet_kaggle.ipynb，以及 Huang 帶入的新增檔。

- [ ] **Step 2: 完成 merge commit**

```bash
git commit -m "merge: 合併 Huang 分支，統一 6 類體系並移除 ResNet

- config 採 Huang 6 類（ViT-L/14）
- README 融合：更正為 6 類 + 補 CLIP A-E 說明
- 移除 train_resnet_kaggle.ipynb 與 ResNet 殘留
- app: 自訓 CNN 與 CLIP A-E 並存

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: commit 成功。

---

# Phase 2 — 重構訓練 notebook（本地編輯 .ipynb）

> 編輯 notebook 用 **NotebookEdit** 工具（指定 cell index 與新 source）。cell index 依設計文件對照的現有 notebook（共 32 cell）。

### Task 7: 更新 models/custom_cnn_model.py（預設 6 類 + docstring）

**Files:**
- Modify: `models/custom_cnn_model.py`

- [ ] **Step 1: 改 docstring 與預設類別數**

用 Edit 將 class docstring 與 `__init__` 預設值改為 6 類：
- `"""4-block CNN baseline for 5-class disaster classification.` → `...for 6-class disaster classification.`
- `def __init__(self, num_classes: int = 5):` → `def __init__(self, num_classes: int = 6):`

（卷積層結構**不變**；`Linear(256, num_classes)` 的 num_classes 由載入時傳入決定，層名不變，舊 4 類權重本就不相容、會由新訓練的 6 類權重取代。）

- [ ] **Step 2: 語法驗證**

Run: `python -m py_compile models/custom_cnn_model.py && echo OK`
Expected: `OK`

- [ ] **Step 3: 暫存**

```bash
git add models/custom_cnn_model.py
```

---

### Task 8: notebook Config cell（cell 3）改寫為 MEDIC 6 類

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 3）

- [ ] **Step 1: 用 NotebookEdit 取代 cell 3 source**

```python
from pathlib import Path

# ── 資料來源：HuggingFace QCRI/MEDIC（Kaggle 需開 internet）────
HF_DATASET = "QCRI/MEDIC"

# ── 輸出路徑（Kaggle working dir，跑完從右側 Output 下載）─────
OUT_DIR      = Path("/kaggle/working")
WEIGHTS_PATH = OUT_DIR / "custom_cnn.pth"
MAPPING_PATH = OUT_DIR / "custom_cnn_classes.json"
CURVES_PATH  = OUT_DIR / "training_curves.png"
CM_PATH      = OUT_DIR / "confusion_matrix.png"

# ── 訓練超參數 ─────────────────────────────────────────────
BATCH_SIZE    = 64
LEARNING_RATE = 1e-3
EPOCHS        = 30
NUM_WORKERS   = 4          # Kaggle 約 4 核，吃滿加速資料載入
SEED          = 42
USE_DATA_PARALLEL = False  # True 則用 nn.DataParallel 吃滿 T4×2（可選加速）
MAX_SAMPLES_PER_CLASS = None  # train 每類抽樣上限（控訓練時間）；None = 全量
MAX_EVAL_PER_CLASS    = None  # val/test 每類抽樣上限（試跑可設小如 200 加速）；None = 全量
CACHE_IN_MEMORY       = True   # 影像解碼一次存記憶體（提高 GPU 使用率）；全量資料若 RAM 不足設 False

# ── 6 類正準順序（對齊 utils/config.py，index 不可改）──────────
CLASSES_EN = [
    "Earthquake Damage", "Flood", "Fire",
    "Typhoon or Storm Damage", "Landslide", "Other or No Disaster",
]
CLASSES_ZH = [
    "地震或建築損壞", "淹水", "火災",
    "颱風或強風災損", "土石流或坍方", "其他或無明顯災害",
]
NUM_CLASSES = len(CLASSES_EN)  # 6

# ── MEDIC disaster_types 原始標籤 → 6 類 index（7→6，合併 not/other）──
MEDIC_MAP = {
    "earthquake":     0,
    "flood":          1,
    "fire":           2,
    "hurricane":      3,
    "landslide":      4,
    "not_disaster":   5,
    "other_disaster": 5,
}

print(f"HF_DATASET: {HF_DATASET}")
print(f"NUM_CLASSES: {NUM_CLASSES}  -> {CLASSES_EN}")
```

- [ ] **Step 2: 語法驗證（抽出 cell 程式檢查）**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); src=''.join(nb['cells'][3]['source']); compile(src,'<cell3>','exec'); print('cell3 OK')"`
Expected: `cell3 OK`

---

### Task 9: notebook imports cell（cell 5）加入 datasets

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 5）

- [ ] **Step 1: 用 NotebookEdit 取代 cell 5 source**

```python
import os, json, time, copy
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler, Dataset
from torchvision import transforms
from datasets import load_dataset
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

torch.manual_seed(SEED)
np.random.seed(SEED)
```

- [ ] **Step 2: 在 cell 1（環境檢查）加裝 datasets**

用 NotebookEdit 在 cell index 1 的 source 開頭加入：
```python
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "datasets"], check=True)
```
（其餘環境檢查內容保留。）

- [ ] **Step 3: 語法驗證**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); compile(''.join(nb['cells'][5]['source']),'<c5>','exec'); print('cell5 OK')"`
Expected: `cell5 OK`

---

### Task 10: notebook 取代 find_data_root cell（cell 7）→ 載入 MEDIC

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 7）

- [ ] **Step 1: 用 NotebookEdit 取代 cell 7 source**

```python
# 載入 MEDIC（非串流，完整下載+快取，支援多 epoch 隨機抽樣）
raw = load_dataset(HF_DATASET)
print(raw)

# 取得 disaster_types 的整數 label → 原始字串名
SPLIT_TRAIN = "train"
SPLIT_DEV   = "validation" if "validation" in raw else ("dev" if "dev" in raw else None)
SPLIT_TEST  = "test" if "test" in raw else None
assert SPLIT_DEV is not None and SPLIT_TEST is not None, f"找不到 dev/test split：{list(raw.keys())}"

DT_NAMES = raw[SPLIT_TRAIN].features["disaster_types"].names
print("MEDIC disaster_types 原始類別：", DT_NAMES)

# 確認 MEDIC_MAP 覆蓋所有原始標籤（避免漏映射）
missing = [n for n in DT_NAMES if n not in MEDIC_MAP]
assert not missing, f"MEDIC_MAP 未覆蓋：{missing}"

# 檢視一筆樣本結構
ex = raw[SPLIT_TRAIN][0]
print("樣本欄位：", list(ex.keys()))
print("image 型別：", type(ex["image"]))
```

- [ ] **Step 2: 語法驗證**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); compile(''.join(nb['cells'][7]['source']),'<c7>','exec'); print('cell7 OK')"`
Expected: `cell7 OK`

> 註：實際 split 名稱（dev vs validation）在 Kaggle 執行 Step 1 印出 `raw` 後確認；程式已自動偵測。

---

### Task 11: notebook transforms cell（cell 9）— 確認沿用

**Files:**
- Verify: `train_custom_cnn_kaggle.ipynb`（cell index 9）

- [ ] **Step 1: 確認 cell 9 維持原 train_tf/val_tf（224 + ImageNet normalize）**

不需修改（設計指定沿用 ImageNet normalize、224）。確認內容為：
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

---

### Task 12: notebook 取代 dataset/DataLoader cell（cell 11）→ MedicDataset

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 11）

- [ ] **Step 1: 用 NotebookEdit 取代 cell 11 source**

```python
class MedicDataset(Dataset):
    """把 MEDIC HF split 包成 (image_tensor, label6)；套 MEDIC_MAP（7→6）。

    每個 split 各自持有獨立 transform —— 不共享底層 dataset，
    因此不會有舊版「val transform 覆蓋 train augmentation」的副作用。
    cache=True 時於 __init__ 將影像解碼並縮到 <=256 存記憶體，
    之後每 epoch 只做 augmentation，免重複 JPEG 解碼（提高 GPU 使用率）。
    """
    def __init__(self, hf_split, transform, max_per_class=None, cache=False):
        self.hf_split  = hf_split
        self.transform = transform
        self.samples   = []                 # list of (hf_index, label6)
        self.counts    = [0] * NUM_CLASSES
        names = hf_split.features["disaster_types"].names
        for i, dt in enumerate(hf_split["disaster_types"]):
            label6 = MEDIC_MAP.get(names[dt])
            if label6 is None:
                continue
            # 注意：max_per_class 取每類在原始 dataset 的「前 N 筆」（未洗牌），純為控訓練時間；若在意分布偏差可改先洗牌再截取。
            if max_per_class is not None and self.counts[label6] >= max_per_class:
                continue
            self.counts[label6] += 1
            self.samples.append((i, label6))

        # 可選：解碼一次存記憶體（搭配 num_workers=0，避免多進程複製快取）
        self.images = None
        if cache:
            self.images = []
            for hf_i, _ in self.samples:
                im = self.hf_split[hf_i]["image"].convert("RGB")
                im.thumbnail((256, 256))   # 等比縮到 <=256 邊長，省記憶體
                self.images.append(im.copy())
            mb = sum(im.size[0] * im.size[1] * 3 for im in self.images) / 1e6
            print(f"  已快取 {len(self.images)} 張影像於記憶體（約 {mb:.0f} MB）")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        if self.images is not None:
            img = self.images[idx]
        else:
            hf_i, _ = self.samples[idx]
            img = self.hf_split[hf_i]["image"].convert("RGB")
        return self.transform(img), self.samples[idx][1]


train_ds = MedicDataset(raw[SPLIT_TRAIN], train_tf, max_per_class=MAX_SAMPLES_PER_CLASS, cache=CACHE_IN_MEMORY)
val_ds   = MedicDataset(raw[SPLIT_DEV],   val_tf,  max_per_class=MAX_EVAL_PER_CLASS, cache=CACHE_IN_MEMORY)
test_ds  = MedicDataset(raw[SPLIT_TEST],  val_tf,  max_per_class=MAX_EVAL_PER_CLASS, cache=CACHE_IN_MEMORY)

print("Train 類別分布：")
for i, (en, n) in enumerate(zip(CLASSES_EN, train_ds.counts)):
    print(f"  [{i}] {en:25s} {n:6d}")
print(f"Train: {len(train_ds)}  Dev: {len(val_ds)}  Test: {len(test_ds)}")

# sqrt-inverse 類別權重 → WeightedRandomSampler（處理嚴重不平衡）
counts   = np.array(train_ds.counts, dtype=float)
class_w  = 1.0 / np.sqrt(np.maximum(counts, 1.0))
sample_w = [class_w[label] for _, label in train_ds.samples]
sampler  = WeightedRandomSampler(sample_w, num_samples=len(sample_w), replacement=True)

# 快取在記憶體時用單進程（避免每個 worker 複製整份快取）；否則開多 worker 平行解碼
if CACHE_IN_MEMORY:
    _loader_kw = dict(num_workers=0, pin_memory=True)
else:
    _loader_kw = dict(num_workers=NUM_WORKERS, pin_memory=True)
    if NUM_WORKERS > 0:
        _loader_kw.update(persistent_workers=True, prefetch_factor=4)

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, **_loader_kw)
val_loader   = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, **_loader_kw)
test_loader  = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, **_loader_kw)
```

- [ ] **Step 2: 語法驗證**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); compile(''.join(nb['cells'][11]['source']),'<c11>','exec'); print('cell11 OK')"`
Expected: `cell11 OK`

---

### Task 13: notebook v1 定義（cell 13）+ train_one_model（cell 15）支援 6 類/DataParallel/test

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 13, 15）

- [ ] **Step 1: 用 NotebookEdit 取代 cell 13 source（v1，預設 6）**

```python
class DisasterCNN_v1(nn.Module):
    """4-block CNN baseline for 6-class disaster classification."""
    def __init__(self, num_classes: int = 6):
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

- [ ] **Step 2: 用 NotebookEdit 取代 cell 15 source（train_one_model + evaluate + 訓練 v1）**

```python
def train_one_model(model_class, model_name: str, epochs: int = EPOCHS):
    """通用訓練函式 — 回傳 (history, best_val_acc, best_state)。best_state 已去除 DataParallel 包裝。"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model     = model_class(NUM_CLASSES).to(device)
    if USE_DATA_PARALLEL and torch.cuda.device_count() > 1:
        model = nn.DataParallel(model)
    loss_fn   = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler    = torch.amp.GradScaler("cuda") if device == "cuda" else None

    history      = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_acc = 0.0
    best_state   = None

    core = model.module if isinstance(model, nn.DataParallel) else model
    n_params = sum(p.numel() for p in core.parameters() if p.requires_grad)
    print(f"\n=== {model_name} ===  可訓練參數: {n_params:,}")

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        for imgs, labels in train_loader:
            imgs   = imgs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad()
            if scaler is not None:
                with torch.amp.autocast("cuda"):
                    loss = loss_fn(model(imgs), labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss = loss_fn(model(imgs), labels)
                loss.backward()
                optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        model.eval()
        val_loss = correct = total_n = 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs   = imgs.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)
                logits = model(imgs)
                val_loss += loss_fn(logits, labels).item()
                correct += (logits.argmax(1) == labels).sum().item()
                total_n += labels.size(0)
        val_loss /= len(val_loader)
        val_acc   = correct / total_n

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            core = model.module if isinstance(model, nn.DataParallel) else model
            best_state = copy.deepcopy(core.state_dict())

        print(f"  Epoch {epoch:2d}/{epochs}  Train Loss: {train_loss:.4f}  "
              f"Val Loss: {val_loss:.4f}  Val Acc: {val_acc:.4f}  ({time.time()-t0:.1f}s)")
        scheduler.step()

    print(f"  → Best Val Acc: {best_val_acc:.4f}")
    return history, best_val_acc, best_state


@torch.no_grad()
def evaluate(model_class, state, loader):
    """用 best_state 在指定 loader 上評估，回傳 (preds, trues)。"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model_class(NUM_CLASSES).to(device)
    model.load_state_dict(state)
    model.eval()
    preds, trues = [], []
    for imgs, labels in loader:
        imgs = imgs.to(device, non_blocking=True)
        preds.extend(model(imgs).argmax(1).cpu().tolist())
        trues.extend(labels.tolist())
    return preds, trues


# 訓練 v1
v1_history, v1_best_acc, v1_best_state = train_one_model(DisasterCNN_v1, "v1 Baseline")
```

- [ ] **Step 3: 語法驗證 cell 13、15**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); [compile(''.join(nb['cells'][i]['source']),f'<c{i}>','exec') for i in (13,15)]; print('cell13/15 OK')"`
Expected: `cell13/15 OK`

---

### Task 14: notebook v2/v3/v4（cell 17/19/21）改 6 類

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 17, 19, 21）

- [ ] **Step 1: NotebookEdit 取代 cell 17（v2 No-BN）**

```python
class DisasterCNN_v2_NoBN(nn.Module):
    """v1 - all BatchNorm layers"""
    def __init__(self, num_classes: int = 6):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Dropout(0.3), nn.Linear(256, num_classes),
        )
    def forward(self, x):
        return self.classifier(self.features(x))

v2_history, v2_best_acc, v2_best_state = train_one_model(DisasterCNN_v2_NoBN, "v2 No-BN")
```

- [ ] **Step 2: NotebookEdit 取代 cell 19（v3 Big-FC）**

```python
class DisasterCNN_v3_BigFC(nn.Module):
    """v1 with GAP replaced by Flatten + Linear(256*14*14, num_classes)"""
    def __init__(self, num_classes: int = 6):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Dropout(0.3), nn.Linear(256 * 14 * 14, num_classes),  # 50176 -> 6
        )
    def forward(self, x):
        return self.classifier(self.features(x))

v3_history, v3_best_acc, v3_best_state = train_one_model(DisasterCNN_v3_BigFC, "v3 Big-FC")
```

- [ ] **Step 3: NotebookEdit 取代 cell 21（v4 Shallow）**

```python
class DisasterCNN_v4_Shallow(nn.Module):
    """v1 with only Block 1 + Block 2 (drop Block 3 + Block 4)"""
    def __init__(self, num_classes: int = 6):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Dropout(0.3), nn.Linear(64, num_classes),
        )
    def forward(self, x):
        return self.classifier(self.features(x))

v4_history, v4_best_acc, v4_best_state = train_one_model(DisasterCNN_v4_Shallow, "v4 Shallow")
```

- [ ] **Step 4: 語法驗證 cell 17/19/21**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); [compile(''.join(nb['cells'][i]['source']),f'<c{i}>','exec') for i in (17,19,21)]; print('v2/v3/v4 OK')"`
Expected: `v2/v3/v4 OK`

---

### Task 15: notebook 對比/曲線/混淆矩陣（cell 23/25/27）改用 test

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 23, 27）

- [ ] **Step 1: NotebookEdit 取代 cell 23（對比表，移除 v1_pred 依賴，加 test acc）**

```python
import pandas as pd

# 在 test 上評估 v1（部署版）以取得最終成績與混淆矩陣資料
v1_test_pred, v1_test_true = evaluate(DisasterCNN_v1, v1_best_state, test_loader)
v1_test_acc = np.mean(np.array(v1_test_pred) == np.array(v1_test_true))

results = pd.DataFrame([
    {"model": "v1 Baseline", "best_dev_acc": v1_best_acc, "params": sum(p.numel() for p in DisasterCNN_v1(NUM_CLASSES).parameters())},
    {"model": "v2 No-BN",    "best_dev_acc": v2_best_acc, "params": sum(p.numel() for p in DisasterCNN_v2_NoBN(NUM_CLASSES).parameters())},
    {"model": "v3 Big-FC",   "best_dev_acc": v3_best_acc, "params": sum(p.numel() for p in DisasterCNN_v3_BigFC(NUM_CLASSES).parameters())},
    {"model": "v4 Shallow",  "best_dev_acc": v4_best_acc, "params": sum(p.numel() for p in DisasterCNN_v4_Shallow(NUM_CLASSES).parameters())},
])
print(results.to_string(index=False))
print(f"\nv1 部署版 Test Acc: {v1_test_acc:.4f}")
```

- [ ] **Step 2: NotebookEdit 取代 cell 27（v1 在 test 的混淆矩陣 + 報告）**

```python
print("=== v1 (deploy) Classification Report — TEST split ===")
print(classification_report(v1_test_true, v1_test_pred, target_names=CLASSES_EN, digits=4))

cm = confusion_matrix(v1_test_true, v1_test_pred, labels=list(range(NUM_CLASSES)))
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=CLASSES_EN, yticklabels=CLASSES_EN)
plt.xlabel("Predicted"); plt.ylabel("True")
plt.title("v1 Confusion Matrix (MEDIC test, 6-class)")
plt.xticks(rotation=45, ha="right"); plt.yticks(rotation=0)
plt.tight_layout(); plt.savefig(CM_PATH, dpi=120); plt.show()
print("⚠️ 重點檢視：地震(0)↔土石流(4) 混淆、以及『其他/無災害(5)』是否主導預測")
```

- [ ] **Step 3: 確認 cell 25（訓練曲線）相容**

cell 25 用 `v1_history` 等 history dict（key 不變），無需改。若它引用 `v1_pred`（已移除）才需調整——檢查後處理。

- [ ] **Step 4: 語法驗證 cell 23/27**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); [compile(''.join(nb['cells'][i]['source']),f'<c{i}>','exec') for i in (23,27)]; print('cell23/27 OK')"`
Expected: `cell23/27 OK`

---

### Task 16: notebook 存檔 cell（cell 29）寫 6 類 json + medic_map

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（cell index 29）

- [ ] **Step 1: NotebookEdit 取代 cell 29 source**

```python
torch.save(v1_best_state, WEIGHTS_PATH)
print(f"✅ 權重已存: {WEIGHTS_PATH}  ({WEIGHTS_PATH.stat().st_size / 1e6:.2f} MB)")

mapping = {
    "classes":      CLASSES_EN,
    "zh_labels":    CLASSES_ZH,
    "class_to_idx": {c: i for i, c in enumerate(CLASSES_EN)},
    "num_classes":  NUM_CLASSES,
    "architecture": "DisasterCNN_v1",
    "val_acc":      float(v1_best_acc),
    "test_acc":     float(v1_test_acc),
    "dataset":      "QCRI/MEDIC (disaster_types, 7->6)",
    "medic_map":    MEDIC_MAP,
}
with open(MAPPING_PATH, "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)
print(f"✅ 類別對照已存: {MAPPING_PATH}")
print(json.dumps(mapping, ensure_ascii=False, indent=2))
```

- [ ] **Step 2: 語法驗證**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); compile(''.join(nb['cells'][29]['source']),'<c29>','exec'); print('cell29 OK')"`
Expected: `cell29 OK`

---

### Task 17: notebook markdown 文字更新（4 類/varpit94 → 6 類/MEDIC）

**Files:**
- Modify: `train_custom_cnn_kaggle.ipynb`（markdown cells）

- [ ] **Step 1: 找出含舊敘述的 markdown cell**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); [print(i, repr(''.join(c['source'])[:80])) for i,c in enumerate(nb['cells']) if c['cell_type']=='markdown']"`
逐一檢視含「4 類 / varpit94 / 5-class / disaster-images-dataset」字樣者。

- [ ] **Step 2: NotebookEdit 更新標題與章節敘述**

- cell 0 標題副述：改為「6 類災情分類，資料集：MEDIC (QCRI)」
- cell 6 章節「## 3. 確認資料夾結構」→「## 3. 載入 MEDIC 並檢視類別分布」
- 其餘提及 4 類/varpit94 處，改為 6 類/MEDIC。

- [ ] **Step 3: 驗證整本 notebook JSON 合法**

Run: `python -c "import json; json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); print('notebook JSON valid')"`
Expected: `notebook JSON valid`

---

### Task 18: 完成 Phase 2 commit

- [ ] **Step 1: 全 notebook cell 語法總檢**

Run: `python -c "import json; nb=json.load(open('train_custom_cnn_kaggle.ipynb',encoding='utf-8')); [compile(''.join(c['source']),f'<c{i}>','exec') for i,c in enumerate(nb['cells']) if c['cell_type']=='code']; print('所有 code cell 語法 OK')"`
Expected: `所有 code cell 語法 OK`

- [ ] **Step 2: 暫存並 commit**

```bash
git add train_custom_cnn_kaggle.ipynb models/custom_cnn_model.py
git commit -m "feat(notebook): 改寫 Custom CNN 訓練為 MEDIC 6 類

- 資料源改 HuggingFace QCRI/MEDIC，MEDIC_MAP 7->6
- map-style MedicDataset（修掉舊版共享 transform bug）
- 用 MEDIC train/dev/test 原生切分，test 出混淆矩陣
- v1~v4 全部改 num_classes=6；train_one_model 支援 DataParallel 安全存權重
- custom_cnn_model.py 預設改 6 類

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

# Phase 3 — 訓練與整合驗證

### Task 19:（手動 handoff）Kaggle 訓練並回放權重

**Files:**
- 由使用者於 Kaggle 執行後產生：`models/custom_cnn.pth`、`models/custom_cnn_classes.json`

- [ ] **Step 1:（使用者）上傳 notebook 到 Kaggle，開啟 GPU T4×2 + internet，Run All**
先以 `MAX_SAMPLES_PER_CLASS = 500`（或小值）跑一輪確認整條管線通，再設 `None` 全量正式訓練。

- [ ] **Step 2:（使用者）下載 `custom_cnn.pth` 與 `custom_cnn_classes.json`，放到本地 `models/`**

- [ ] **Step 3: 驗證權重可被 classifier 載入為 6 類**

Run: `python -c "from models.custom_cnn_classifier import weights_exist, classify; from PIL import Image; print('weights_exist:', weights_exist()); import json; m=json.load(open('models/custom_cnn_classes.json',encoding='utf-8')); print('num_classes:', m['num_classes']); assert m['num_classes']==6; print('OK')"`
Expected: `weights_exist: True`、`num_classes: 6`、`OK`

---

### Task 20: 整合驗證（5 條推論路徑）+ 合回

**Files:**
- Verify: `app.py`（執行期）

- [ ] **Step 1: 啟動 app 並逐一測 5 條推論路徑**

```bash
streamlit run app.py
```
手動於分析頁測試並確認**不丟例外、中文標籤與信心正常**：
1. 自訓 CNN（6 類）
2. CLIP A / B / C
3. CLIP D 多描述投票
4. CLIP E Linear Probe（需 ViT-L/14 已下載）
5. 「比較」模式（CLIP + CNN 並排）

- [ ] **Step 2: 確認 H3 聚合與 RAG 以 top_class_zh 串接正常**
上傳一張測試圖，確認地圖聚合與 RAG 回應無 KeyError。

- [ ] **Step 3: 合回 feature/custom-cnn（或發 PR）**

```bash
git checkout feature/custom-cnn
git merge --no-ff merge/huang-6class
```
或：`git push -u origin merge/huang-6class` 後在 GitHub 開 PR。

- [ ] **Step 4: 最終確認**

Run: `git log --oneline -8 && git status`
Expected: 合併歷史完整、工作區乾淨。

---

## Self-Review 對照（spec 覆蓋檢查）

- spec §2 類別映射 → Task 8（MEDIC_MAP）、Task 10（覆蓋檢查）✅
- spec §5 notebook 各 cell → Task 8–17 ✅
- spec §6 config/app/classifier/README → Task 2、3、5、7 ✅
- spec §6 ResNet→CNN 輔助模型替換（Submit_Report + versions + 移除 ResNet 程式，DB 欄位沿用）→ Task 4 ✅
- spec §7 三階段順序 → Phase 1/2/3 ✅
- spec §8 風險（不平衡/normalize/截斷圖/session 時限/順序）→ Task 12（sqrt-inverse sampler）、Task 11（ImageNet norm）、Task 9（LOAD_TRUNCATED）、Task 8（MAX_SAMPLES_PER_CLASS）、Task 10（顯式 index）✅
- spec §9 驗證 5 路徑 → Task 20 ✅
- spec custom_cnn_classifier 零改碼 → 計畫未編輯該檔，Task 19 Step 3 驗證其讀 6 類 json ✅
