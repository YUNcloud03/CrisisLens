# Data Card — CrisisLens Disaster Classification Platform

> **Format**: Google Data Cards / MLSecOps Workshop 1  
> **Last Updated**: 2026-06-13  
> **Version**: v3.0  
> **SDG Alignment**: SDG 11 (Sustainable Cities), SDG 13 (Climate Action)

> 本資料卡已對齊純 5 類 v2 與雙主投票（CLIP + EfficientNet-B0）架構。

---

## Part A — Training Dataset: QCRI/MEDIC

### A.1 Dataset Overview

| Field | Value |
|-------|-------|
| **Name** | QCRI Multimedia Event Dataset for Disaster Informatics (MEDIC) |
| **Version used** | disaster_types split |
| **Source** | Qatar Computing Research Institute (QCRI) |
| **License** | Research / Academic use (non-commercial) |
| **Paper** | Alam et al., *MEDIC: A Multi-Task Learning Dataset for Disaster Image Classification* (ACL 2021 Workshop) |
| **Download** | https://crisisnlp.qcit.edu.qa/medic/index.html |
| **Task** | **5-class** image classification（純 5 類，已移除 not_disaster / other_disaster） |

---

### A.2 Label Mapping (Original → CrisisLens)

| MEDIC Original Label | CrisisLens English Label | CrisisLens 中文標籤 | idx | Note |
|---------------------|--------------------------|---------------------|-----|------|
| `earthquake` | Earthquake Damage | 地震或建築損壞 | 0 | Direct mapping |
| `flood` | Flood | 淹水 | 1 | Direct mapping |
| `fire` | Fire | 火災 | 2 | Direct mapping |
| `hurricane` | Typhoon or Storm Damage | 颱風或強風災損 | 3 | Domain-adapted for Taiwan |
| `landslide` | Landslide | 土石流或坍方 | 4 | Direct mapping |
| `not_disaster` | *(已移除)* | — | — | **v2 升級移除**，不再納入訓練 |
| `other_disaster` | *(已移除)* | — | — | **v2 升級移除**，不再納入訓練 |

> **Domain Adaptation Note**: MEDIC `hurricane` 重映射至 `Typhoon or Storm Damage`，以符合台灣氣象用語。訓練影像主要源自大西洋颶風，對台灣颱風場景存在 **distribution shift**。

> **v2 升級說明**: 相較於舊版 6 類架構，v2 完整移除「其他或無明顯災害」守門類，改為純 5 類真實災害分類，並以雙主投票（CLIP + EfficientNet-B0）取代單一模型架構。

---

### A.3 Data Statistics

#### A.3.1 類別分布（來源：docs/eda_5class_phase1_analysis.md）

| Class | Train | Val | Test | Train 占比 |
|-------|------:|----:|-----:|----------:|
| Earthquake Damage | 12,296 | 1,004 | 1,795 | 53.3% |
| Typhoon or Storm Damage（原 hurricane） | 4,517 | 651 | 1,518 | 19.6% |
| Flood | 3,401 | 587 | 1,315 | 14.7% |
| Fire | 1,796 | 262 | 690 | 7.8% |
| Landslide | 1,065 | 168 | 331 | 4.6% |
| **Total** | **23,075** | **2,672** | **5,649** | 100% |

> **Class Imbalance**: Train 最大 / 最小類別比 = **11.55x**（Earthquake vs Landslide）。以 `WeightedRandomSampler`（sqrt-inverse 權重）緩解；模型選擇以 `val_macro_f1` 為指標。

#### A.3.2 資料清理摘要（來源：models/classes_5class_v2.json）

| 清理項目 | 數量 | 說明 |
|---------|-----:|------|
| dHash 去重移除（train） | **3,616 張**（占 train 15.7%） | 視覺近似重複，移除以防記憶化 |
| Test 洩漏排除 | **60 張**（占 test 1.06%） | train 與 test 間交叉重複，已排除 |

---

### A.4 Data Collection Process

- **Source**: Social media images (Twitter, Flickr) collected during real disaster events
- **Collection Period**: 2012–2020
- **Geographic Coverage**: Primarily North America, Caribbean, South Asia
- **Annotation**: Crowd-sourced with expert verification
- **Image Format**: JPEG/PNG, variable resolution
- **Preprocessing Applied（來源：models/efficientnet_classifier.py:72-76）**:
  - `Resize(288)` → `CenterCrop(256)`（輸入解析度 256px）
  - ImageNet normalization: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
- **Augmentation（v2 訓練規格）**:
  - `RandomResizedCrop(256, scale=[0.5, 1.0])`（保守裁切，保住語意）
  - `ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1)`（輕度色彩增強）
- **Model Selection Metric**: `val_macro_f1`（非 overall accuracy，避免偏向多數類）

---

### A.5 Train / Validation / Test Split

| Split | Count | Note |
|-------|------:|------|
| Train | 23,075 | dHash 去重後；含 WeightedRandomSampler |
| Validation | 2,672 | 用於 best model 選擇（val_macro_f1） |
| Test | **5,649**（held-out） | 已排除 60 張洩漏圖；EfficientNet-B0 test macro-F1 = **0.8375** |

> Split 依 MEDIC 原始切分使用，非隨機重切。

---

### A.6 Known Biases and Limitations

| Bias Type | Description | Impact |
|-----------|-------------|--------|
| **Geographic bias** | Mostly Western hemisphere events | Reduced accuracy on Taiwan-specific disaster scenes |
| **Platform bias** | Social media photos (Twitter/Flickr) | May not generalize to citizen reporting styles |
| **Temporal bias** | 2012–2020 imagery | May not reflect modern urban environments |
| **Hurricane ≠ Typhoon** | Atlantic hurricanes vs. Pacific typhoons have different visual patterns | Typhoon recall = **0.783**（5 類中最低，颱風為主要弱點類） |
| **Typhoon 類內異質性** | 44% 颱風影像視覺幾乎無災損（衛星雲圖、氣象追蹤圖）| 本質為「事件標籤」而非純視覺類別，kNN baseline recall 僅 0.40 |
| **Earthquake 主導 train** | Earthquake 占 train 53.3%，且 train 內有 15.7% 視覺近重複 | 已透過去重與 WeightedRandomSampler + val_macro_f1 選模緩解 |

---

### A.7 Privacy Considerations

| Risk | Mitigation |
|------|-----------|
| Images may contain identifiable persons | No face recognition is performed; images used only for disaster-type classification |
| GPS metadata in EXIF | Not extracted or stored from MEDIC dataset |
| Original social media posts | Not re-published; only classification model trained |

---

## Part B — Production Dataset: CrisisLens User Reports

### B.1 Overview

User-submitted disaster photos collected in real-time through the CrisisLens web platform.

| Field | Value |
|-------|-------|
| **Collection Method** | Voluntary submission by registered users |
| **Storage** | Local server (`uploads/reports/`) or Azure Blob Storage |
| **Format** | JPEG (converted from any uploaded format) |
| **Linked Metadata** | GPS coordinates, city/district, event_time, description |

---

### B.2 Data Schema (per report)

| Column | Type | Description |
|--------|------|-------------|
| `image_path` | TEXT | Server-side file path |
| `latitude`, `longitude` | FLOAT | Optional GPS coordinates |
| `city`, `district` | TEXT | Administrative location |
| `disaster_type` | TEXT | CLIP-assigned label (English) |
| `clip_confidence` | FLOAT | Model confidence score (0–1) |
| `need_review` | INT | 1 = flagged for human review |
| `model_agreement` | INT | 1 = CLIP and EfficientNet-B0 agree |
| `has_injured_people` | INT | User-reported field conditions |
| `rag_advice` | TEXT | AI-generated response advice (JSON) |

---

### B.3 Privacy and Safety (Production Data)

| Risk | Level | Mitigation |
|------|-------|-----------|
| GPS coordinates reveal user location | **High** | User consent required；GPS 座標以 **H3 resolution 9（邊長約 174m）模糊化**後用於聚合（來源：aggregation/h3_utils.py），不對外顯示精確座標 |
| Photos may show injured persons | **High** | Admin-only access; not publicly shared |
| Description text may contain PII | **Medium** | Free-text; no NLP extraction performed |
| Data retention | **Medium** | No automatic deletion policy (future work) |

---

### B.4 Data Quality Flags

| Flag | Condition | Action |
|------|-----------|--------|
| `need_review = 1` | Confidence < 50%，或 Top-1/Top-2 gap < 15%，或 model_agreement == 0 | Admin manual review |
| `model_agreement = 0` | **CLIP** label ≠ **EfficientNet-B0** label（中文標籤比對） | Auto-flagged for review |
| `grid_id IS NULL` | No GPS + no city/district provided | Report excluded from heatmap |

> **注意**：`model_agreement` 自 v2 起改為 **CLIP vs EfficientNet-B0** 雙主投票一致性，非舊版 CNN 對比。

---

## Part C — RAG Knowledge Base

| Field | Value |
|-------|-------|
| **Documents** | 6 SOP files (earthquake, flood, fire, typhoon, landslide, emergency) |
| **Source** | Taiwan government disaster response guidelines (adapted) |
| **Chunk Size** | 400 characters with 80-char overlap |
| **Embedding Model** | `paraphrase-multilingual-MiniLM-L12-v2` |
| **Index Type** | FAISS Flat L2 |
| **Index Version** | `faiss-multilingual-minilm-v1` |
| **Language** | Traditional Chinese (zh-TW) |

---

## Summary

| Aspect | Training Data (MEDIC) | Production Data (CrisisLens) |
|--------|----------------------|------------------------------|
| Size | **31,396 images**（train 23,075 / val 2,672 / test 5,649） | Growing (real-world citizen reports) |
| Classes | **5 classes**（純 5 類 v2） | 5 classes（同訓練集定義） |
| Source | Academic / Social media | Real-world citizen reports |
| Language | English labels | Bilingual (EN labels + ZH display) |
| Privacy risk | Low (public social media) | High (GPS + personal photos) |
| Geographic coverage | Global (Western bias; hurricane→typhoon domain adaptation) | Taiwan-focused |
| Quality control | dHash 去重（-3,616 張）+ test 洩漏排除（-60 張）+ expert annotation | AI confidence（雙主投票）+ human review |
| Model | EfficientNet-B0（test macro-F1 0.8375）+ CLIP ViT-L/14 雙主投票 | 同左 |
