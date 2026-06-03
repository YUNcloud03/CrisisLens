# CrisisLens Data Card（資料卡）

**Version**: v1.1
**Date**: 2026-06-01
**Maintainer**: CrisisLens 專案
**對應模型**: DisasterCNN_v1（4-block CNN, 4-class）+ CLIP ViT-B/32（zero-shot 對照）
**相關文件**: [training_summary.md](training_summary.md)

> 本 Data Card 依 MLSecOps 課程提供的 `data_card` 通用模板撰寫。模板原以「貸款評分（表格資料 + 公平性）」為例，本專案為**災害影像分類**，因此部分屬性的語意已依專案性質改寫，差異見 §10。

---

## 1. Dataset Summary（資料集摘要）

| 欄位 | 內容 |
|---|---|
| `dataset_name` | Kaggle Disaster Images Dataset（4-class subset） |
| 來源 | [`mikolajbabula/disaster-images-dataset-cnn-model`](https://www.kaggle.com/datasets/mikolajbabula/disaster-images-dataset-cnn-model)（公開） |
| `purpose` | 訓練自建 CNN 對災害影像做 4 分類，輔助 CrisisLens 系統的災情判讀與應變分流 |
| `created_at` | 2026-06-01（資料卡建立時間） |
| 資料型態 | RGB 影像（JPG / PNG），標準化至 224×224 |
| `rows`（影像張數） | ~2,000 張（train/val 80/20 split, seed=42） |

> **語意差異**：模板的 `rows` 指表格列數，本專案改指**影像張數**。

---

## 2. Labels & Target（標籤與目標）

- `target`: **`disaster_type`**（4 類，非貸款模板的二元 `approved`）
- 標籤方式：ImageFolder 依資料夾命名，字母排序自動對應 index

| 類別 | 含義 |
|---|---|
| `Cyclone` | 颱風或強風災損 |
| `Earthquake` | 地震或建築損壞 |
| `Flood` | 淹水 |
| `Wildfire` | 火災 |

- 類別不平衡 → 訓練時使用 `WeightedRandomSampler`
- ⚠️ **無 `Non_Damage`（無災害）類別**：任何非災害照片都會被強制分到上述 4 類之一。

---

## 3. Data Characteristics（資料特徵）

| 項目 | 設定 |
|---|---|
| 影像格式 | RGB JPG / PNG |
| 尺寸 | 224×224（ImageNet normalization） |
| Train augmentation | RandomResizedCrop(224), HFlip, ColorJitter(0.3), Rotation(±15°) |
| Val transform | Resize(256) → CenterCrop(224) |
| Split | 80% train / 20% val（seed=42） |

---

## 4. Protected Attributes（受保護屬性）

- `protected_attributes`: **`[]`（空）**

**說明**：影像資料**不含結構化的人口屬性欄位**（不像貸款資料有 `gender` 欄位可供公平性稽核）。因此本專案無法以「欄位」形式列出受保護屬性，相關的公平性風險改以**隱含偏差**形式記錄於 §6（known_risks）：

- 資料集**地理來源不明** → 可能對特定地區/國家的災情判讀偏差
- 災情照片若含人物，可能無意間帶入人口統計層面的隱性偏見（未做 intersectionality 分析）

---

## 5. PII Policy（個資政策）

`pii_policy`：

- 災情照片**可能包含人臉、車牌、證件等個資**（因為來源為真實災情回報）。
- GPS 座標在儲存前已 bucketed 進 **H3 網格（res 9 ≈ 174m）**，並以 `grid_id` 取代精確座標，達到部分去識別化。
- UI（`pages/1_Submit_Report.py`）有資訊透明聲明：座標僅用於災情定位，不傳送至第三方。
- ⚠️ **尚未實作人臉去識別化**；上傳照片存於 `uploads/reports/`（未加密、未匿名）。

> **語意差異**：本屬性在影像專案中**比貸款模板更關鍵**——表格資料移除直接識別碼即可，影像則需處理像素層級的人臉/證件。

**建議補強**：加入人臉偵測自動模糊（MTCNN / MediaPipe）、上傳目錄存取控管、明確 Privacy Policy。

---

## 6. Known Risks（已知風險）

`known_risks`：

1. **Flood ↔ Earthquake 高混淆（~26.5%）**：淹水後的「損壞建築 + 泥沙 + 鋼筋」與地震瓦礫視覺高度相似（詳見 [training_summary.md §6](training_summary.md)）。
2. **缺 `Non_Damage` 類別**：非災害照片會被強制分類，UI 需注意此限制。
3. **資料集地理來源未知** → 可能存在區域偏差。
4. **誤判的生命安全影響**：災害應變情境下，分類錯誤可能延誤救援。
5. **視覺捷徑（shortcut）洩漏**：模型可能學到浮水印、背景等非本質特徵；ColorJitter 也可能削弱「水」的色彩線索，使 Flood 辨識變差。

> **語意差異**：模板用特徵-target 相關性（`corr()`）檢測表格 leakage；影像版的對應風險是上述「視覺捷徑洩漏」。

---

## 7. Required Controls（必要控制措施）

`required_controls`：

| 控制 | 現況 | 對應實作 |
|---|---|---|
| 低信心度人工審核 | ✅ 已實作 | 信心度 < 0.5 標記 `need_review = 1` |
| 雙模型交叉印證 | ✅ 已實作 | CLIP（zero-shot）+ 自建 CNN 並列比對 |
| 人工修正留痕 | ✅ 已實作 | `admin_corrections` 表（可回饋 retraining） |
| 模型/版本追蹤 | ✅ 已實作 | `utils/versions.py`、`model_runs` 表 |
| AI Safety 免責聲明 | ✅ 已實作 | README + UI：非官方災害判定，緊急請撥 119/110 |
| 公平性 / 偏差監控 | ⚠️ 待補 | 尚無 per-region / demographic 分層監控 |
| Per-class 性能退化監控 | ⚠️ 待補 | 特別關注 Flood（recall 僅 67.2%） |

---

## 8. Provenance & Versioning（來源與版本）

| 項目 | 值 |
|---|---|
| 資料集來源 | Kaggle `mikolajbabula/disaster-images-dataset-cnn-model` |
| 訓練日期 | 2026-05-31 |
| Production 模型 | DisasterCNN_v1（Val Acc 90.51%, 390,404 params） |
| 權重檔 | `models/custom_cnn.pth` |
| 類別/中繼資料 | `models/custom_cnn_classes.json` |
| 版本記錄 | `utils/versions.py`、`model_runs` 表 |

---

## 9. Usage Constraints（使用限制）

- **用途**：災害資訊整理與應變**輔助**參考，**不代表官方災害判定**。
- **不得用於**：正式法律/保險/官方災損認定。
- **授權**：資料集依 Kaggle 原始授權；本專案為教學與內部使用。

---

## 10. 與課程模板的對照（Mapping）

| 模板屬性 | 本專案使用方式 |
|---|---|
| `dataset_name` | ✅ 直接使用 |
| `purpose` | ✅ 直接使用 |
| `created_at` | ✅ 直接使用 |
| `rows` | ✅ 改語意：表格列數 → **影像張數** |
| `target` | ✅ 改值：`approved` → **`disaster_type`（4 類）** |
| `protected_attributes` | ⚠️ 改寫：影像無結構化人口欄位 → 設為空，偏差改記於 `known_risks` |
| `pii_policy` | ✅ 使用，且**比表格模板更關鍵**（人臉/證件） |
| `known_risks` | ✅ 改內容為影像專案風險 |
| `required_controls` | ✅ 使用，對應實際機制 |
| 模板的 `corr()` leakage 檢查 | ⚠️ 不適用表格欄位 → 改為**視覺捷徑洩漏**的討論 |

---

## 附：可執行的 data_card dict（對齊課程模板格式）

```python
data_card = {
    'dataset_name': 'Kaggle Disaster Images Dataset (4-class subset)',
    'purpose': 'Training a custom CNN to classify disaster imagery '
               '(cyclone/earthquake/flood/wildfire) to assist crisis response triage',
    'created_at': datetime.utcnow().isoformat() + 'Z',
    'rows': int(num_images),          # 影像張數 (~2000, 80/20 split)，非表格列數
    'target': 'disaster_type',        # 4 classes，非二元 approved
    'protected_attributes': [],       # 影像無結構化人口欄位；偏差改述於 known_risks
    'pii_policy': 'Disaster photos may contain faces/plates/IDs. '
                  'GPS is bucketed into H3 grid (~174m) before storage. '
                  'Face de-identification not yet implemented (planned).',
    'known_risks': [
        'High Flood<->Earthquake confusion (~26.5%) due to visual similarity',
        'No "Non-Damage" class: non-disaster images are force-classified',
        'Dataset geographic source unknown -> possible regional bias',
        'Misclassification in crisis response carries life-safety impact',
        'Visual shortcuts (watermarks/background) may leak instead of true features',
    ],
    'required_controls': [
        'Confidence < 0.5 flagged for human review (need_review)',
        'Admin correction log retained for retraining audit',
        'Model/version tracking (utils/versions.py, model_runs table)',
        'AI-safety disclaimer: not an official disaster determination',
        'Monitoring for per-class accuracy degradation (esp. Flood)',
    ],
}
```
