# 災情分類視覺辨識：混合訓練路線設計

**Date**: 2026-05-30
**Status**: Draft (awaiting user review)
**Topic**: 完善 CrisisLens 專案的 ResNet50 視覺辨識功能，同時最大化深度學習訓練實作練習價值

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
- 從頭設計 CNN 架構（架構設計直覺）
- Fine-tuning 預訓練模型（實務工作的核心技巧）
- 透過 ablation 親身觀察設計決策的影響
- 建立可放 portfolio 的對比訓練報告

### 1.3 範圍決策

| 決策點 | 選擇 | 理由 |
|---|---|---|
| 類別數 | 統一 5 類（移除 Typhoon） | 避免 CLIP/ResNet 類別數不對等造成「比較」模式失真；資料集 A 沒有 Typhoon 樣本 |
| 資料集 | `mikolajbabula/disaster-images-dataset-cnn-model` | folder name 與 `train_resnet.py` 的 `FOLDER_TO_ZH` 完全相符，零 schema 改動 |
| 訓練路線 | 混合路線 C-Full | 同時學習 from-scratch 架構設計 + 實務 fine-tuning，並產出對比報告 |

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
- **緩解方式**：
  - 訓練後檢查 confusion matrix 中 Damaged_Infrastructure 的 false positive 比例
  - 若嚴重，在 streamlit UI 加上低信心度提示（已有 `CLIP_LOW_CONF_THRESHOLD = 0.5` 機制）

---

## 3. Phase 1：自建 CNN + 架構 Ablation

### 3.1 Phase 1 目標

從頭設計、訓練一個 CNN，並透過 ablation 親身觀察「現代 CNN 為什麼長這樣」。

**不是**追求最高準確度（已知會輸給 Phase 2）；**是**累積架構設計直覺。

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
- Augmentation: 與 ResNet 訓練同（RandomResizedCrop / HFlip / ColorJitter / Rotation），**不含 VFlip**
- 預期 Val Acc：65-70%

### 3.3 Ablation 實驗（v2-v4）

每個 ablation 僅改動一個變數，其他超參數與 v1 相同：

| 變體 | 改動 | 觀察重點 | 預期學到 |
|---|---|---|---|
| **v2: No-BN** | 移除所有 `BatchNorm2d` | Train loss 震盪、收斂變慢、Val Acc 下降 5-8% | BatchNorm 對訓練穩定性的關鍵作用 |
| **v3: Big-FC** | GAP 改 `Flatten + Linear(256*14*14 → 5)` | 參數量 +100x、嚴重過擬合（Train Acc 99% / Val Acc ~50%） | GAP 為何取代 Flatten + 大 FC |
| **v4: Shallow** | 只保留 Block 1 + Block 2（2 層） | Val Acc 下降 10-15% | 深度對特徵抽取能力的影響 |

每個變體都需保留：訓練曲線（train/val loss + val acc）、最終 Val Acc、Confusion Matrix。

### 3.4 Phase 1 產出

- `train_custom_cnn_kaggle.ipynb`（單一 notebook，含 v1-v4 四個訓練 cell + 對比視覺化）
- 4 組訓練曲線疊圖
- 4 張 Confusion Matrix
- Phase 1 心得段落（會併入 Phase 3 報告）

---

## 4. Phase 2：ResNet50 Partial Fine-tune

### 4.1 Phase 2 目標

學習實務 fine-tuning 技巧：head warmup、discriminative LR、early stopping、save best。

### 4.2 兩階段訓練設計

**Stage 1: Head Warmup / Linear Probe（最多 10 epochs，含 early stop）**

```python
model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
for p in model.parameters():
    p.requires_grad = False                # 全部凍結
model.fc = nn.Linear(2048, 5)              # 替換最後一層
optimizer = Adam(model.fc.parameters(), lr=1e-3)
```

目標雙重：
1. **Warmup**：讓 fc 從隨機初始化收斂到能給出合理梯度方向，避免後續解凍 layer4 時破壞預訓練特徵
2. **作為 Phase 3 的 "Linear Probe" baseline**：Stage 1 訓到收斂（不只 3 epoch warmup）後 save 一份 checkpoint → 此 checkpoint 就是對比表中的「ResNet50 Linear Probe (frozen)」

訓練至 val loss 連續 2 epoch 沒下降即進 Stage 2，或最多 10 epochs。

預期：Val Acc 70-78%。

**Stage 2: 解凍 layer4 + Discriminative LR（≤10 epochs，含 Early Stop）**

```python
for p in model.layer4.parameters():
    p.requires_grad = True

optimizer = Adam([
    {"params": model.layer4.parameters(), "lr": 1e-4},   # 已預訓練 → 小 LR 微調
    {"params": model.fc.parameters(),     "lr": 1e-3},   # 已 warmup 但需繼續學
])
scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)
```

預期：Val Acc 攀升到 85-88%。

### 4.3 訓練技巧（教學重點）

| 技巧 | 實作 | 學到的概念 |
|---|---|---|
| Discriminative LR | optimizer 分組 (layer4 vs fc) | 不同層需要不同 LR |
| Early Stopping | patience=3 監控 val loss | 過擬合監控 |
| ReduceLROnPlateau | val loss 停滯時 LR × 0.5 | 動態 LR 調整 |
| Save Best | 用 val acc 最高的 epoch | 「最後一輪 ≠ 最好的一輪」 |
| Per-class Acc | 每 epoch 印 5 類分別的 recall | 觀察哪一類最難 |
| Gradient Norm 監控 | 每 epoch 印 grad norm | 梯度健康概念 |

### 4.4 Augmentation 調整

| 動作 | 理由 |
|---|---|
| 移除 `RandomVerticalFlip(p=0.1)` | 災情圖上下顛倒不符語意 |
| 新增 `RandomErasing(p=0.25, scale=(0.02, 0.15))` | Fine-tune 時強迫模型不依賴單一視覺線索 |
| 保留其他 augmentation | RandomResizedCrop / HFlip / ColorJitter / Rotation 都合理 |

### 4.5 Phase 2 產出

- `train_resnet_kaggle.ipynb`（覆寫現有版本，改為兩階段 Partial Fine-tune）
- `resnet50_linear.pth`（最終權重，~95 MB）
- `resnet50_linear_classes.json`（類別對照）
- 訓練曲線、Confusion Matrix

---

## 5. Phase 3：對比 + 整合

### 5.1 同 val split 評估表

| 模型 | Val Acc | 可訓練參數 | Kaggle 訓練時間 | 推論時間 (CPU) |
|---|---|---|---|---|
| Custom CNN final | TBD（預估 ~68%） | ~400K | ~1.5 hr | ~5 ms |
| ResNet50 Linear Probe (frozen) | TBD（預估 ~75%） | ~10K | ~15 min | ~30 ms |
| ResNet50 Partial Fine-tune | TBD（預估 ~87%） | ~15M | ~40 min | ~30 ms |

> 為了能在同 val split 上比較，三個模型需用同一份 `random_split` seed（已設 `SEED=42`）。
> 「ResNet50 Linear Probe (frozen)」直接取自 Phase 2 Stage 1 訓到收斂後 save 的 checkpoint，不需獨立訓練。
> 「Partial Fine-tune」取自 Stage 2 Early Stop 觸發時的 best checkpoint。

### 5.2 視覺化產出

- 6 條訓練曲線疊圖（v1-v4 + Linear Probe + Partial FT）
- 3 張 Confusion Matrix 並排（Custom CNN best / Linear Probe / Partial FT）
- 每類 recall 對比 bar chart

### 5.3 對比報告：`docs/training_comparison.md`

內容章節：
1. 實驗目的與設計
2. 資料集說明（類別、樣本數、分割）
3. 三個模型的訓練曲線對比
4. 量化結果表
5. 錯誤分析（Confusion Matrix 解讀）
6. **三條 lessons learned**：
   - Pretraining 給了多少 accuracy boost
   - Fine-tune 又給了多少
   - 哪些類別最難、為什麼

### 5.4 整合進 streamlit

- `models/resnet50_linear.pth` 放入
- `models/resnet50_linear_classes.json` 放入
- 確認 UI 側邊欄顯示「✅ 已訓練」
- 跑一次端到端流程驗證

---

## 6. 改動清單總覽

### 6.1 修改檔案

| 檔案 | 改動性質 |
|---|---|
| `utils/config.py` | 6 類 → 5 類，刪除 Typhoon entries |
| `train_resnet_kaggle.ipynb` | 重寫為兩階段 Partial Fine-tune（含 Stage 1 + Stage 2） |
| `models/train_resnet.py` | 同步移除 `RandomVerticalFlip`、5 類調整（可選，主要為本地 reproduce） |

### 6.2 新增檔案

| 檔案 | 用途 |
|---|---|
| `train_custom_cnn_kaggle.ipynb` | Phase 1：v1-v4 訓練與 ablation 對比 |
| `docs/training_comparison.md` | Phase 3：對比報告 |
| `models/resnet50_linear.pth` | Phase 2 訓練產出（從 Kaggle 下載） |
| `models/resnet50_linear_classes.json` | Phase 2 類別對照 |
| `models/custom_cnn_final.pth` | Phase 1 最終權重（保留作為歷程紀錄，不 deploy） |

### 6.3 不動的檔案

- `models/clip_classifier.py`、`models/resnet_baseline.py`：類別數從 config 動態讀取，無需改
- `rag/`、`aggregation/`、`db/`：與視覺辨識無關
- `app.py`、`pages/`：類別變更後 UI 會自動跟隨

---

## 7. 預期時程

| 階段 | 預估時間 | 備註 |
|---|---|---|
| Phase 1：自建 CNN + 3 ablations | 3-5 hr | Kaggle GPU 訓練 + 寫 notebook + 視覺化 |
| Phase 2：Partial Fine-tune | 1-2 hr | 大部分是 Kaggle GPU 訓練（~50 min） |
| Phase 3：對比 + 整合 + 報告 | 1-2 hr | 寫 markdown + 整合測試 |
| **總計** | **5-9 hr** | 建議分散 2-3 天 |

---

## 8. 成功標準

- [ ] Phase 1：自建 CNN v1 達 ≥ 60% Val Acc；3 個 ablation 訓練曲線清楚展示設計差異
- [ ] Phase 2：Partial Fine-tune 達 ≥ 80% Val Acc；訓練曲線顯示 Stage 1 → Stage 2 的進步
- [ ] Phase 3：對比報告完成、Streamlit UI 顯示「ResNet50 ✅ 已訓練」
- [ ] 5 類結構在 CLIP 與 ResNet 之間完全對齊
- [ ] 本地 streamlit 啟動仍維持秒級（lazy import 修復沿用）

---

## 9. 風險與緩解

| 風險 | 機率 | 緩解 |
|---|---|---|
| 資料集 A 圖片量比預期少（< 1000 張） | 中 | Notebook 的 inspection cell 會先告知；若太少，改用 dataset C（9k+ 圖）+ 重 map folder name |
| Custom CNN v1 訓不到 60% | 中 | 不視為失敗，**這就是 ablation 報告的素材**；可以加深、加寬、或加 augmentation |
| Partial Fine-tune 過擬合（train acc > 95% / val acc < 80%） | 中 | Early stop + ReduceLROnPlateau 已內建；若仍嚴重，加重 RandomErasing 或減小 LR |
| Kaggle GPU 配額用盡 | 低 | 每週 30 hr，預估用 4-6 hr，餘裕大 |
| Class imbalance 嚴重（Non_Damage 佔 50%+） | 中 | `WeightedRandomSampler` 已處理；輔以 per-class metrics 監控 |

---

## 10. 不在範圍內

明確不做的事（避免 scope creep）：

- ❌ 為 Typhoon 類別找新資料集（已決定移除）
- ❌ 用其他預訓練 backbone（EfficientNet / ViT 等）
- ❌ CLIP fine-tune / LoRA
- ❌ 物件偵測、分割、深度估計等新任務
- ❌ 改 `aggregation/`、`rag/`、`db/` 模組
- ❌ 重訓 CLIP 或調整 PROMPT_SETS 的學術內容（僅做類別數對齊）

如果完成 C-Full 後想繼續延伸，這些是下一個 spec 的範圍。
