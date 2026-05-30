# 災情分類視覺辨識：自建 CNN 訓練設計

**Date**: 2026-05-30
**Status**: Draft (awaiting user review)
**Topic**: 完善 CrisisLens 專案的視覺辨識功能，透過自建 CNN 從頭訓練累積深度學習實作經驗

---

## 1. 背景與目標

### 1.1 專案現況

CrisisLens 是災情圖文分類系統，視覺辨識部分目前有兩個模型：

| 模型 | 訓練狀態 | 實際訓練的參數 |
|---|---|---|
| CLIP ViT-B/32 (zero-shot) | **完全未訓練** | 0（純 prompt engineering） |
| ResNet50 Linear Probe | **架構就緒、無權重** | 約 10K（僅最後 fc 層，佔總參數 0.04%） |

`models/resnet50_linear.pth` 不存在 → 即使選擇 ResNet50 模式，fc 是隨機初始化、輸出等同亂猜。

### 1.2 學習目標

使用者已具備：訓練過 MNIST/CIFAR 等典型範例的經驗。

使用者欲練習的領域：
- **從頭設計 CNN 架構**（架構設計直覺、超參數選擇）
- **透過 ablation 親身觀察設計決策的影響**（BatchNorm、GAP、深度…）
- **完整訓練一個自己定義的模型**（不是 fine-tune 別人的權重）

### 1.3 範圍決策

| 決策點 | 選擇 | 理由 |
|---|---|---|
| 類別數 | 統一 5 類（移除 Typhoon） | 避免類別不對等；資料集 A 沒有 Typhoon 樣本 |
| 資料集 | `mikolajbabula/disaster-images-dataset-cnn-model` | folder name 與專案原 `FOLDER_TO_ZH` 完全相符 |
| 訓練路線 | **自建 CNN from scratch + ablation** | 專案本質是練習訓練模型，自建是最純粹的學習 |
| ResNet50 Partial Fine-tune | **移出本次範圍** | 改列為「未來增強」（觸發條件見 §9） |

### 1.4 與原 C-Full 路線的差異

- ❌ 不做 Phase 2 (Partial Fine-tune)
- ❌ 不做三模型對比報告
- ✅ 保留 Phase 1 (自建 CNN + ablation) 的完整學習內容
- ✅ 直接整合自建 CNN 進 streamlit 作為 ResNet 選項的替代
- ✅ 設定明確的「重訪 Fine-tune」觸發條件

---

## 2. 類別結構調整

### 2.1 目標 5 類

| 英文 | 中文 | 對應資料集資料夾 |
|---|---|---|
| Earthquake Damage | 地震或建築損壞 | `Damaged_Infrastructure/` |
| Flood | 淹水 | `Water_Disaster/` |
| Fire | 火災 | `Fire_Disaster/` |
| Landslide | 土石流或坍方 | `Land_Disaster/` |
| Other or No Disaster | 其他或無明顯災害 | `Non_Damage/` |

### 2.2 `utils/config.py` 修改

- `CLASSES_EN`：刪除 `"Typhoon or Storm Damage"`（原 index 3）
- `CLASSES_ZH`：刪除 `"颱風或強風災損"`（原 index 3）
- `NUM_CLASSES`：6 → 5
- `PROMPT_SETS` 三組（A/B/C）各自移除 typhoon 那一行

### 2.3 潛在風險與緩解

- `Damaged_Infrastructure` 涵蓋廣義建築損壞（不限地震因素）→ 模型可能對「老舊建築 / 廢墟 / 一般髒亂街景」誤判為「地震」
- **緩解方式**：訓練後檢查 confusion matrix 中 Damaged_Infrastructure 的 false positive 比例；若嚴重，UI 已有 `CLIP_LOW_CONF_THRESHOLD = 0.5` 低信心度機制可沿用

---

## 3. Phase 1：自建 CNN + 架構 Ablation

### 3.1 Phase 1 目標

從頭設計、訓練一個 CNN，並透過 ablation 親身觀察「現代 CNN 為什麼長這樣」。

**追求的不是最高準確度**（已知會輸給 fine-tune ResNet）；**追求的是**：
- 一個完全由自己決定每個設計選擇的模型
- 對架構決策影響的直觀理解
- 一份可以放 portfolio 的訓練實驗紀錄

### 3.2 Baseline 架構（v1）

```python
class DisasterCNN_v1(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1: 224 -> 112
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            # Block 2: 112 -> 56
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            # Block 3: 56 -> 28
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
            # Block 4: 28 -> 14
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(), nn.MaxPool2d(2),
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

**訓練設定**：
- Optimizer: Adam, lr=1e-3
- Loss: CrossEntropyLoss
- Batch size: 32
- Epochs: 15
- Augmentation: RandomResizedCrop / HFlip / ColorJitter / Rotation（**不含 VFlip**）
- 預期 Val Acc：65-70%

### 3.3 Ablation 實驗（v2-v4）

每個 ablation 僅改動一個變數，其他超參數與 v1 相同：

| 變體 | 改動 | 觀察重點 | 預期學到 |
|---|---|---|---|
| **v2: No-BN** | 移除所有 `BatchNorm2d` | Train loss 震盪、收斂變慢、Val Acc 下降 5-8% | BatchNorm 對訓練穩定性的關鍵作用 |
| **v3: Big-FC** | GAP 改 `Flatten + Linear(256*14*14 → 5)` | 參數量 +100x、嚴重過擬合（Train Acc 99% / Val Acc ~50%） | GAP 為何取代 Flatten + 大 FC |
| **v4: Shallow** | 只保留 Block 1 + Block 2（2 層） | Val Acc 下降 10-15% | 深度對特徵抽取能力的影響 |

每個變體都需保留：訓練曲線（train/val loss + val acc）、最終 Val Acc、Confusion Matrix。

### 3.4 挑選 final 版本

跑完 v1-v4 後選一個作為 **deploy 版本**：
- 通常會是 v1（baseline，因為 v2/v3/v4 是故意做壞的 ablation）
- 但若 v1 訓練不順、某個 ablation 意外勝出，採用該變體並記錄原因

### 3.5 Phase 1 產出

| 產出 | 用途 |
|---|---|
| `train_custom_cnn_kaggle.ipynb` | Phase 1 主 notebook（含 v1-v4 訓練與視覺化） |
| `models/custom_cnn.pth` | Final 版本的權重（**會進 streamlit**） |
| `models/custom_cnn_classes.json` | 類別對照表 |
| 4 組訓練曲線疊圖 + 4 張 Confusion Matrix | 評估與報告素材 |

---

## 4. Phase 2：評估 + 整合進 streamlit

### 4.1 自建 CNN 的推論模組

新增 `models/custom_cnn_classifier.py`，與 `models/clip_classifier.py` 的介面對齊：

```python
def classify(image: Image.Image) -> dict:
    """
    Returns
    -------
    {
        "top_class":    "Flood",
        "top_class_zh": "淹水",
        "confidence":   0.74,
        "top_3":        [...],
        "model_loaded": True / False
    }
    """
```

實作要點：
- `@functools.lru_cache(maxsize=1)` 包 `_load_model()` 函式以快取（與其他 classifier 一致）
- 同樣的 normalization (`[0.485,...], [0.229,...]`)、`Resize(256) → CenterCrop(224)`
- 從 `models/custom_cnn_classes.json` 讀類別對照
- 若 `.pth` 不存在則 `model_loaded=False`（沿用現有 fallback 設計）

### 4.2 `app.py` UI 更新

側邊欄三個選項從：
```
CLIP（Zero-Shot） / ResNet50（Baseline） / 兩者比較
```
改為：
```
CLIP（Zero-Shot） / 自訓 CNN（My CNN） / 兩者比較
```

對應的 `if "CLIP" in model_mode or "比較" in model_mode:` 邏輯改為呼叫 `custom_cnn_classifier.classify`。

`ResNet50` 模式暫時從 UI 拿掉但**程式碼保留**（`resnet_baseline.py` 不刪），方便未來 Partial Fine-tune 觸發時直接 plug back。

### 4.3 評估報告：`docs/training_summary.md`

不是三模型對比（沒有三個模型可比），而是**自建 CNN 的完整訓練紀錄**：

1. **實驗目的** — 學習目標與設計動機
2. **資料集** — 來源、類別、樣本數、train/val split
3. **v1 架構與決策理由** — 為什麼選 4 個 block、為什麼用 GAP…
4. **訓練曲線** — v1 的 loss / acc 曲線
5. **Ablation 對比** — v1-v4 並排，每個 ablation 學到什麼
6. **錯誤分析** — Final 版本的 Confusion Matrix 解讀；哪一類最難
7. **Lessons Learned** — 3-5 條從訓練曲線觀察到的事
8. **下一步** — 若 Val Acc 低於閾值，會考慮的 Partial Fine-tune（見 §9）

### 4.4 整合驗證

- 把 `custom_cnn.pth` + `custom_cnn_classes.json` 放入 `models/`
- 啟動 streamlit（`.\run.ps1`）
- 上傳測試圖片，確認：
  - 自訓 CNN 模式能跑、Top-3 顯示正常
  - 「兩者比較」模式 CLIP 與自訓 CNN 並列、類別名一致
  - 側邊欄顯示「✅ 自訓 CNN 已就緒」（取代原 ResNet 狀態列）

---

## 5. 改動清單

### 5.1 修改檔案

| 檔案 | 改動 |
|---|---|
| `utils/config.py` | 6 類 → 5 類，刪除 Typhoon entries |
| `app.py` | 側邊欄選項：ResNet50 → 自訓 CNN；分析邏輯對應更新 |

### 5.2 新增檔案

| 檔案 | 用途 |
|---|---|
| `train_custom_cnn_kaggle.ipynb` | Phase 1：v1-v4 訓練與 ablation |
| `models/custom_cnn_classifier.py` | 推論模組（介面對齊 clip_classifier） |
| `models/custom_cnn.pth` | Final 訓練權重（從 Kaggle 下載） |
| `models/custom_cnn_classes.json` | 類別對照 |
| `docs/training_summary.md` | Phase 2 評估報告 |

### 5.3 不動的檔案

- `models/resnet_baseline.py`、`models/train_resnet.py`：保留供未來 Partial Fine-tune 用
- `train_resnet_kaggle.ipynb`：保留（之前已建好），未來觸發 Fine-tune 時直接用
- `models/clip_classifier.py`：類別數從 config 動態讀取，無需改
- `rag/`、`aggregation/`、`db/`、`pages/`：與本次無關

---

## 6. 預期時程

| 階段 | 預估時間 | 備註 |
|---|---|---|
| Phase 1.1：v1 架構設計與訓練 | 1-2 hr | Kaggle GPU 訓練 ~30 min + 寫 notebook |
| Phase 1.2：3 個 ablation 訓練 | 1-2 hr | 每個 ~20 min 訓練 + 結果視覺化 |
| Phase 1.3：挑 final + 整理曲線/CM | 30 min | |
| Phase 2.1：寫 `custom_cnn_classifier.py` | 30 min | |
| Phase 2.2：改 `app.py` + `config.py` | 30 min | |
| Phase 2.3：寫 `training_summary.md` | 1 hr | |
| Phase 2.4：整合測試 | 30 min | |
| **總計** | **5-7 hr** | 建議分散 2-3 天 |

---

## 7. 成功標準

- [ ] Phase 1：v1 達 ≥ 60% Val Acc；3 個 ablation 訓練曲線清楚展示設計差異
- [ ] Phase 2：streamlit 側邊欄顯示「✅ 自訓 CNN 已就緒」
- [ ] Final CNN 能在 streamlit 中對測試圖片給出合理 Top-3 預測
- [ ] 5 類結構在 CLIP 與自訓 CNN 之間完全對齊
- [ ] 本地 streamlit 啟動仍維持秒級（lazy import 修復沿用）
- [ ] `training_summary.md` 含完整 ablation 對比與 Lessons Learned

---

## 8. 風險與緩解

| 風險 | 機率 | 緩解 |
|---|---|---|
| 資料集 A 圖片量比預期少（< 1000 張） | 中 | Notebook inspection cell 會先告知；若太少，改用 dataset C（9k+ 圖）+ 重 map folder name |
| Custom CNN v1 訓不到 60% | 中 | 不視為失敗，**這就是 ablation 報告的素材**；可調整 channel / 加深 / 加 augmentation 嘗試。仍低於 50% 才觸發 §9 Partial Fine-tune |
| Class imbalance 嚴重（Non_Damage 佔 50%+） | 中 | 用 `WeightedRandomSampler`；輔以 per-class metrics 監控 |
| Kaggle GPU 配額用盡 | 低 | 每週 30 hr，預估用 2-3 hr，餘裕大 |
| 自訓 CNN 整合到 streamlit 時介面不相容 | 低 | 嚴格對齊 `clip_classifier.classify()` 回傳格式即可 |

---

## 9. 未來增強：Partial Fine-tune（明確觸發條件）

### 9.1 何時觸發

跑完 Phase 1 後，若**任一條件**成立，重啟 Partial Fine-tune 工作：

- Val Acc < 50%（明顯不堪用）
- 任一類別的 recall < 30%（嚴重類別偏差）
- 在 streamlit 實測時，常見災情類型（火災、淹水）的 Top-1 預測明顯錯誤

### 9.2 觸發後該做的事

不需重新 brainstorm 設計，**直接執行**：

1. 用既有的 `train_resnet_kaggle.ipynb`（已建好，含完整兩階段設計）
2. 訓練 Stage 1（Linear Probe / Head Warmup，~10 epoch）+ Stage 2（解凍 layer4 + Discriminative LR）
3. 產出 `resnet50_linear.pth` + `resnet50_linear_classes.json`
4. 在 `app.py` 側邊欄選項把 ResNet50 模式加回來
5. 把它跟自訓 CNN 並列為「兩個自己處理過的模型」（CLIP 仍是 zero-shot 對照）

### 9.3 觸發後的對比報告

若觸發 §9，補一份簡短對比並回填 `training_summary.md` 的「下一步」章節：
- 自訓 CNN Val Acc vs Partial FT ResNet50 Val Acc
- 一句「為什麼預訓練 + fine-tune 在這個資料集上贏」的觀察

---

## 10. 不在範圍內

明確不做的事（避免 scope creep）：

- ❌ 為 Typhoon 類別找新資料集（已決定移除）
- ❌ 用其他預訓練 backbone（EfficientNet / ViT 等）
- ❌ CLIP fine-tune / LoRA
- ❌ 物件偵測、分割、深度估計等新任務
- ❌ 改 `aggregation/`、`rag/`、`db/`、`pages/` 模組
- ❌ 改 CLIP 的 `PROMPT_SETS` 學術內容（僅做類別數對齊）
- ⏸️ Partial Fine-tune（**移到 §9，依觸發條件再決定**）
