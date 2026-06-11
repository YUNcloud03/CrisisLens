# 5 類災害影像 EDA — 第一階段分析報告

**Date**: 2026-06-11
**資料集**: HF [`QCRI/MEDIC`](https://huggingface.co/datasets/QCRI/MEDIC)（`disaster_types` 任務，保留 5 類真實災害，排除 `not_disaster` / `other_disaster`）
**EDA notebook**: [`eda_5class_disaster_kaggle.ipynb`](../eda_5class_disaster_kaggle.ipynb)（Kaggle GPU，Run All）
**對應訓練 notebook**: [`train_5class_disaster_kaggle.ipynb`](../train_5class_disaster_kaggle.ipynb)
**原始數據**: `eda_findings.json`（Kaggle 輸出，數字已謄入本文）

---

## 0. TL;DR

資料整體品質**可用**（解析度足夠、跨 split 洩漏僅 1%、0 張壞圖），但有三個會直接限制模型上限的問題：

1. **Hurricane 類內異質性極高**——44% 影像幾乎無災損畫面（衛星雲圖 / 氣象圖 / meme 圖），kNN baseline 下 recall 僅 0.40，是 5 類的瓶頸。
2. **Earthquake 獨大**（train 占比 53%）且 **train 內有 15.7% 近重複影像**，加劇不平衡與記憶化。
3. **增強配方過強**——`RandomResizedCrop` 預設 scale 會把語意裁掉、`ColorJitter(0.3)` 會抹掉顏色判別線索、rotation 在 crop 之後造成黑角。

免訓練 baseline（ImageNet ResNet18 特徵 + kNN）= **0.659**，微調模型 macro 表現低於 ~0.75 即代表訓練流程有問題。

---

## 1. 類別分布（eda_01）

### 1.1 數字

| 類別 | train | val | test | train 占比 | test 占比 |
|---|---:|---:|---:|---:|---:|
| Earthquake | 12,296 | 1,004 | 1,795 | **53.3%** | 31.8% |
| Hurricane | 4,517 | 651 | 1,518 | 19.6% | 26.9% |
| Flood | 3,401 | 587 | 1,315 | 14.7% | 23.3% |
| Fire | 1,796 | 262 | 690 | 7.8% | 12.2% |
| Landslide | 1,065 | 168 | 331 | 4.6% | 5.9% |
| **合計** | **23,075** | **2,672** | **5,649** | | |

- Train 不平衡比（最大/最小）= **11.55x**

### 1.2 發現

1. **Earthquake 一類占 train 一半以上**。訓練 notebook 的 sqrt-inverse `WeightedRandomSampler` 有緩解，但仍需搭配 macro 指標評估。
2. **train 與 val/test 的類別占比不一致**：Earthquake 53% → 32%、Flood 15% → 23%、Hurricane 20% → 27%。這代表 overall accuracy 在不同 split 上量的東西不一樣——**用 val overall acc 挑 best model（`train_model` 現行做法）會系統性偏向「把地震學好」的模型**。
3. **Landslide val 只有 168 張**：recall 估計的 95% CI 約 ±7pt，epoch 間的 landslide val 波動大半是抽樣噪音，不可過度解讀。

---

## 2. 多任務標籤交叉（eda_02）

MEDIC 為多任務資料集，同一張圖另有 `damage_severity` / `informative` / `humanitarian` 標籤。

### 2.1 damage_severity × 災害類（train, row share）

| 類別 | little_or_none | mild | severe |
|---|---:|---:|---:|
| Earthquake | 4.9% | 10.7% | **84.4%** |
| Flood | 17.1% | 19.4% | 63.5% |
| Fire | 15.6% | 13.2% | 71.2% |
| **Hurricane** | **44.1%** | 16.3% | 39.5% |
| Landslide | 19.3% | 15.8% | 64.9% |

### 2.2 發現

1. **Hurricane 有 44% 影像幾乎無災損**（衛星雲圖、氣象追蹤圖、暴風雨前天空、下雨街景）。humanitarian 同樣印證：Hurricane 31.8% not_humanitarian，遠高於其他類（Earthquake 僅 1.6%）。
2. **Hurricane 本質上是「事件標籤」而非「視覺類別」**——同一事件下混入衛星圖、氣象圖、災損照三種視覺上完全不同的內容。
3. `informative` 全類 ≥95.9% → **用 informative 過濾雜訊沒有空間**；MEDIC 的雜訊在 damage_severity 維度，不在 informative 維度。

---

## 3. 影像尺寸 / 格式（eda_03）

- 僅 **5.9%** 影像 min side < 224；各類中位數約 400–600px → **解析度不是瓶頸**，甚至有空間升輸入到 256/288。
- 長寬比集中在 1.3–1.8，無極端比例；**0 張無法讀取**。
- 注意點：Earthquake 中位數（~410px）明顯低於其他類（~580px），推測為 2015 尼泊爾地震舊圖畫質較低——存在輕微「畫質低 ↔ 地震」的混淆因子，無簡單修法，列為已知風險。

---

## 4. 樣本目視（eda_04）

從每類 8 張隨機樣本中直接觀察到的雜訊型態：

| 類別 | 觀察 |
|---|---|
| Earthquake | 高度同質（尼泊爾地震街景瓦礫為主）——這也是它 train 內近重複最多的原因 |
| Flood | 混入看似土石流清理現場的泥漿圖；Flood/Landslide 在「泥」特徵上天然重疊 |
| Fire | 「PRAY FOR OREGON」文字疊圖（meme）；多張為**燒毀後殘骸**（無火焰），視覺接近地震瓦礫 |
| Hurricane | 8 張中 3 張非實景：氣象追蹤圖（TROPICAL TRACKER）、衛星雲圖、政治 meme 配字圖 |
| Landslide | 大致一致（空拍坍方、落石路面、行車視角），少量日文浮水印圖 |

---

## 5. 像素統計（eda_05a / eda_05b）

- **RGB 簽名有判別力**：Fire 是唯一 R≫G≫B 暖色類；Hurricane 是唯一 R≈G≈B 中性灰類；Earthquake 偏棕（塵土）。**顏色本身攜帶類別資訊**。
- Fire 亮度有長暗尾（夜間火災）、飽和度有高尾（火焰）——分布最寬，但因紋理+顏色組合獨特，t-SNE 反而聚得最好。
- 抽樣通道 mean = **[0.451, 0.432, 0.407]** vs ImageNet [0.485, 0.456, 0.406] → 差距小，**Normalize 維持 ImageNet 參數即可**。

推論：`ColorJitter(0.3, 0.3, 0.3)` 偏強——把火災飽和度拉掉 30%、或把中性灰的颱風圖調暖，等於主動抹掉判別線索。

---

## 6. 重複影像與洩漏（eda_06）

| 檢查 | MD5（完全相同） | dHash（視覺近似） |
|---|---:|---:|
| within_train | 1,463 | **3,616（占 train 15.7%）** |
| within_val | 10 | 13 |
| within_test | 17 | 35 |
| val_in_train | 7 | 27 |
| test_in_train | 7 | **60（占 test 1.06%）** |

- Test 洩漏類別分布：Earthquake 40 / Hurricane 11 / Flood 5 / Fire 4。
- 並排對照確認 dHash 無誤判（甚至抓到同一張圖的彩色 vs 灰階版本）。

### 發現

1. **跨 split 洩漏僅 1.06%** → test 分數最多虛高 ~1pt，**整體可信**。
2. **真正的問題是 train 內部 15.7% 近重複**，危害有三：
   - 浪費 ~15% 訓練算力；
   - 重複圖在 WeightedRandomSampler 下被有效加權，加劇對特定場景（尼泊爾地震）的記憶化；
   - train acc 虛高，干擾過擬合判讀。
3. 去重後 train 約剩 19.5k 張。

---

## 7. 特徵空間可分性：t-SNE + kNN（eda_07 / eda_08）

特徵：未微調 ImageNet ResNet18（512 維），train 每類 300 張、test 每類 200 張均衡抽樣。

### 7.1 t-SNE

- **Fire**：右側清楚緊密簇——最好分的類。
- **Landslide**：右上自成一群，與 Earthquake 區域接壤（瓦礫 vs 土石紋理相似）。
- **Earthquake**：左上大片、內部密實（同質性高）。
- **Flood**:中下偏散，與 Hurricane 交織（下雨街景 vs 淹水街景）。
- **Hurricane**:**散落全場**；唯一緊密的紅色子簇在下方，研判為衛星雲圖子群——視覺化印證 §2 的結論。
- train（o）與 test（x）同色分布重疊良好 → **特徵層面無明顯 domain shift**。

### 7.2 kNN（k=5, cosine）— 免訓練 baseline

整體 acc = **0.659**（隨機 = 0.20）。Row-normalized recall：

| True \ Pred | Earthquake | Flood | Fire | Hurricane | Landslide |
|---|---:|---:|---:|---:|---:|
| Earthquake | **0.73** | 0.05 | 0.04 | 0.10 | 0.08 |
| Flood | 0.09 | **0.70** | 0.05 | 0.10 | 0.07 |
| Fire | 0.13 | 0.07 | **0.71** | 0.03 | 0.06 |
| Hurricane | 0.23 | 0.15 | 0.10 | **0.40** | 0.12 |
| Landslide | 0.15 | 0.03 | 0.04 | 0.04 | **0.74** |

### 發現

1. 四類 recall 都在 0.70–0.74，**只有 Hurricane 0.40**，且錯誤**均勻漏向所有類**——「類內異質」的典型特徵（不是和某一類混淆，而是沒有統一的視覺中心）。
2. **0.659 是微調模型的最低標**：微調 EfficientNet-B0 的 macro 表現若未明顯超過 ~0.75，問題在訓練流程而非資料。
3. 預測:微調後混淆矩陣最差的一列仍會是 Hurricane——架構救不了標籤層面的異質性。

---

## 8. 增強配方檢視（eda_09）

現行 train transform：`RandomResizedCrop(224)` → `RandomHorizontalFlip` → `ColorJitter(0.3, 0.3, 0.3)` → `RandomRotation(15)`。

從預覽圖觀察到兩個實際問題：

1. **`RandomResizedCrop` 預設 scale=(0.08, 1.0) 過於激進**：Flood 樣本（淹水高速公路+天際線）被裁到只剩綠色路牌，水完全消失——模型學到「路牌→Flood」的錯誤關聯;Hurricane 樣本有整張只剩霧的裁切。
2. **rotation 在 crop 之後 → 必然產生黑角**（每行預覽都可見）。rotation 移到 crop 之前即可讓黑角被裁掉。

---

## 9. 優化優先順序（第二階段行動清單）

| 優先級 | 行動 | 依據 | 預期效果 |
|---|---|---|---|
| **P1** | **train 去重**：至少刪 1,463 張 MD5 重複；建議連 dHash 近重複一起（共 ~3.6k） | §6 | 快 15%、降記憶化、train acc 誠實 |
| **P2** | **model selection 改用 val macro-F1**（取代 overall val acc） | §1 split 分布不一致 | 不再偏向 Earthquake |
| **P3** | **增強修正**：`RandomResizedCrop(224, scale=(0.5, 1.0))`；rotation 移到 crop 前；ColorJitter 降到 0.1–0.15（或拿掉 saturation） | §5、§8 | 保住語意與顏色線索，小類受益最大 |
| **P4** | **處理 Hurricane 異質性**（擇一實驗）：(a) damage_severity 多任務輔助頭（MEDIC 原生支援）；(b) 過濾 Hurricane 的 little_or_none 子集做對照組；(c) 接受現狀，視為類別定義問題 | §2、§7 | Hurricane 是 macro-F1 最大單一槓桿 |
| **P5** | 輸入解析度升到 256（`Resize(288)` + `CenterCrop(256)`） | §3 | 中位數 580px 還有細節可用 |
| **P6** | 評估時剔除 60 張洩漏 test 圖，主結果旁附「去洩漏版」數字 | §6 | 嚴謹性（差異預期 <1pt） |

### 明確不做的事

| 項目 | 原因 |
|---|---|
| 改 Normalize 參數 | 抽樣 mean 與 ImageNet 夠接近，且使用預訓練骨幹 |
| informative 過濾 | 全類 ≥96% informative，無過濾空間 |
| 長寬比特殊處理 | 分布正常（1.3–1.8），無極端值 |

### 第二階段判讀基準

微調完成後，拿 test 混淆矩陣對照 §7.2 的 kNN 矩陣：

- **Hurricane recall 仍卡 0.5–0.6、其他類都上 0.8** → 資料（標籤定義）天花板，走 P4；
- **所有類都只比 kNN 好一點** → 問題在訓練流程，回頭檢查 P1–P3 與超參數。
