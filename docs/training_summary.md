# Custom CNN 訓練實驗報告

**Date**: 2026-05-31
**模型**: DisasterCNN_v1 (4-block CNN, 4-class disaster classification)
**資料集**: [`mikolajbabula/disaster-images-dataset-cnn-model`](https://www.kaggle.com/datasets/mikolajbabula/disaster-images-dataset-cnn-model)（Kaggle）
**訓練平台**: Kaggle Notebook (GPU T4 / P100)

---

## 1. 實驗目的

練習從頭設計與訓練 CNN 的能力，並透過 3 個 ablation 變體親身觀察「現代 CNN 為什麼長這樣」。

- 最終 deploy 模型：**v1 baseline**（Val Acc 90.51%）
- v2/v3/v4 僅作為對照，不 deploy
- 此設定來自 spec [2026-05-30-disaster-classifier-hybrid-training-design.md](superpowers/specs/2026-05-30-disaster-classifier-hybrid-training-design.md)

---

## 2. 資料集

- 來源：Kaggle `mikolajbabula/disaster-images-dataset-cnn-model`（flat 版本 `Cyclone_Wildfire_Flood_Earthquake_Dataset/`）
- 4 類，ImageFolder 自動依字母排序：
  - `Cyclone/` → 颱風或強風災損
  - `Earthquake/` → 地震或建築損壞
  - `Flood/` → 淹水
  - `Wildfire/` → 火災
- Train/Val split: 80/20（seed=42）
- 類別不平衡 → `WeightedRandomSampler` 處理

> **注意**：本資料集**沒有** "Non_Damage"（無災害）類別。任何非災害的測試照片都會被強制分到 4 個災害類別之一 — UI 上需注意這個限制。

---

## 3. v1 (Baseline) 架構與決策理由

```
Input (3, 224, 224)
  ↓ Block 1: Conv(3→32, 3x3) + BN + ReLU + MaxPool      → (32, 112, 112)
  ↓ Block 2: Conv(32→64, 3x3) + BN + ReLU + MaxPool     → (64, 56, 56)
  ↓ Block 3: Conv(64→128, 3x3) + BN + ReLU + MaxPool    → (128, 28, 28)
  ↓ Block 4: Conv(128→256, 3x3) + BN + ReLU + MaxPool   → (256, 14, 14)
  ↓ AdaptiveAvgPool(1) + Flatten                          → (256,)
  ↓ Dropout(0.3) + Linear(256, 4)                         → (4,)
```

實際參數：**390,404**

**決策理由**：

| 設計 | 為什麼 |
|---|---|
| 4 個 Conv block | 深淺平衡：足以提取從邊緣到高階特徵的層次，又不至於過深導致過擬合 |
| Channel 32→64→128→256（×2 倍增） | 經典 VGG 風格漸進。前段保留細節、後段聚焦語意 |
| 3×3 kernel | 現代 CNN 主流；相同 receptive field 下參數遠少於 5×5 |
| BatchNorm 在每個 Conv 後 | 穩定訓練、允許較大 LR、有正則化效果 |
| GAP 取代 Flatten + 大 FC | 減 99% 參數、嚴控過擬合風險 |
| Dropout 0.3 在 fc 前 | 搭配 GAP 進一步抑制過擬合 |

---

## 4. 訓練設定

| 超參數 | 值 |
|---|---|
| Optimizer | Adam |
| Learning rate | 1e-3 |
| Loss | CrossEntropyLoss |
| Batch size | 32（首次）→ 64（後續加速優化） |
| Epochs | 15 |
| Augmentation (train_tf) | RandomResizedCrop(224), HFlip, ColorJitter(0.3), Rotation(±15°) |
| Augmentation (val_tf) | Resize(256) → CenterCrop(224) |
| Normalization | ImageNet mean/std |
| 類別平衡 | WeightedRandomSampler |
| Mixed Precision | AMP (cuda.amp) |
| 設備 | Kaggle T4 GPU |

---

## 5. 結果對比

### 5.1 量化結果

| Model | Val Acc | Params | vs v1 |
|---|---|---|---|
| **v1 Baseline** | **0.9051** | 390,404 | — |
| v2 No-BN | 0.8960 | 389,444 | −0.90% |
| v3 Big-FC | 0.8791 | 590,084 | −2.60% |
| v4 Shallow | 0.8373 | 19,844 | −6.78% |

訓練曲線：`training_curves.png`（Kaggle output）

### 5.2 預測 vs 實際的差距

| 變體 | 我訓練前預測 | 實際 | 解讀 |
|---|---|---|---|
| v2 No-BN | −5 ~ −8% | **−0.90%** | BN 的影響比預期小；dataset 較容易、不需要 BN 的穩定化也能收斂 |
| v3 Big-FC | 嚴重過擬合（Val < 70%） | −2.60% | 沒有顯著過擬合；資料量足夠，FC 多 200K 參數仍可學得起來 |
| v4 Shallow | −10 ~ −15% | **−6.78%** | 深度有用但邊際遞減；20K 參數的 2-block 也能到 83.7% |

→ **這個 dataset 比預期容易**。圖像區分性強，簡單模型也能做到 80+。

---

## 6. 錯誤分析（v1 Confusion Matrix）

混淆矩陣：`confusion_matrix.png`

### 6.1 Per-class Recall

| True Class | Recall | 觀察 |
|---|---|---|
| Cyclone | 91.6% (174/190) | ✅ 強 |
| Earthquake | 95.2% (238/250) | ✅ 最強 |
| **Flood** | **67.2%** (137/204) | ⚠️ **最弱** |
| Wildfire | 93.4% (225/241) | ✅ 強 |

### 6.2 主要誤判：Flood → Earthquake

```
True\Pred    Cyclone  Earthquake  Flood  Wildfire
Cyclone       174       11         1       4
Earthquake      1      238         8       3
Flood           3       54       137      10    ← 54 張被誤判為地震！
Wildfire        3        7         6     225
```

**Flood 類別有 26.5% 被誤判成 Earthquake（54 張）**。

#### 推測原因

| 因素 | 說明 |
|---|---|
| 視覺特徵重疊 | 洪水後場景常含「淹水的損壞建築 + 漂流泥沙 + 鋼筋裸露結構」 → 與地震照片的「倒塌建築 + 瓦礫 + 鋼筋」**視覺極為相似** |
| 模型學到了「損壞建築」這個共通 feature，沒抓到「有水 vs 無水」的關鍵判別 |
| 顏色線索可能被弱化 | Augmentation 的 ColorJitter(0.3) 對 brightness/contrast/saturation 都有抖動，**可能無意間削弱了「水」的色彩特徵**（藍綠調） |

#### 可能的後續改善方向（非本次範圍）

- 減少 ColorJitter 強度，或對 Flood 類別關閉色彩抖動
- 加 mixup / cutout 等正則化讓模型更不依賴單一視覺線索
- 提高 Flood 在 sampler 中的權重，讓更多 epoch 看到 Flood
- 換更深的 backbone（spec §9 觸發路線）— 但其他類別已 ≥ 91% recall，**沒有觸發 §9 的必要性**

---

## 7. Lessons Learned

從這次實驗親身體會到的 4 件事：

### 7.1 BatchNorm 影響「比想像中小」這件事本身就是 lesson

我訓練前假設 BN 拿掉會掉 5-8% — 實際只掉 0.90%。**不代表 BN 不重要**，但代表：
- 這個資料集規模/難度落在 BN 邊際效益較低的區間
- 在這之前我把「BN 必加」當教條，這次體驗讓我多了一個「在什麼情況下 BN 真正重要」的問題意識（提示：通常是更深的網路、更大 LR、batch size 較小時影響更明顯）

### 7.2 GAP vs Flatten 在「資料量夠時」差距收斂

v3（GAP→Flatten+大 FC）參數量從 390K 暴增到 590K，預期會嚴重過擬合。實際只掉 2.6%。
- 訓練集大概有 ~2000 張圖（×augmentation 等效更多），對於 200K 額外 FC 參數**仍綽綽有餘**
- GAP 仍是更好的選擇：參數少、推論快、過擬合風險低，但這次的「為什麼選 GAP」的論證強度從「絕對的工程必須」**降級為**「合理的工程偏好」

### 7.3 深度的邊際效益遞減

v4 只有 2 個 block、20K 參數，居然還能跑出 83.7%。深度從 2 到 4 帶來 6.78% 的提升，**不到絕對必要**。
- 對「淺 vs 深」這個決策，未來會多考慮**任務複雜度匹配**：簡單任務不需要深模型，硬塞深度只是浪費算力
- 推論時間也是考量：v4 推論最快、v1 中等、ResNet50 最慢，**要看 deploy 場景的延遲預算**

### 7.4 視覺類別的「特徵相似性」決定了哪一類最難

理論上 4 類都應該訓得起來；實際只有 Flood 卡在 67%。原因不是 model 不夠強，是 **Flood 與 Earthquake 在 RGB 平面的視覺特徵高度重疊**。
- 這個 lesson 改變了我看「classification problem」的方式：不是看 model，是看**類別之間的決策邊界容不容易畫**
- 在實務上，這個 finding 比「我的 model 跑到 90% Val Acc」更值錢 — 它告訴你**這個分類問題本質上的限制在哪裡**

---

## 8. 下一步

| 條件（spec §9.1） | 閾值 | 實際 | 觸發？ |
|---|---|---|---|
| v1 Val Acc < 50% | < 50% | **90.51%** | ❌ 未觸發 |
| 任一類 recall < 30% | < 30% | 最低 67.2% (Flood) | ❌ 未觸發 |
| streamlit 實測常見類型明顯誤判 | — | 待 Task 13 端到端驗證 | 待定 |

**目前狀態：所有觸發條件都未達到 → 保留 v1 作為 production 模型，不啟動 Partial Fine-tune 路線**。

如果未來在 streamlit 實測時觀察到 Top-1 經常誤判 Flood ↔ Earthquake，或想進一步壓榨表現，可考慮：
- 短期：在 UI 層加入「Top-2 含 Flood/Earthquake 時顯示警示」的微調
- 長期：觸發 spec §9，跑 `train_resnet_kaggle.ipynb` 的兩階段 Partial Fine-tune，看是否能改善 Flood 類別

---

## 9. 產出檔案清單

| 檔案 | 位置 | 用途 |
|---|---|---|
| `custom_cnn.pth` | `models/` | Production 用 v1 權重 |
| `custom_cnn_classes.json` | `models/` | 類別對照（包含 architecture、val_acc 等 metadata） |
| `train_custom_cnn_kaggle.ipynb` | 專案根目錄 | Kaggle 訓練 notebook（32 cells，含 v1-v4 + ablation 對比） |
| `training_curves.png` | Kaggle output（可選下載） | v1-v4 訓練 loss/acc 疊圖 |
| `confusion_matrix.png` | Kaggle output（可選下載） | v1 混淆矩陣 |
| `docs/training_summary.md` | 本檔 | 完整訓練實驗報告 |
