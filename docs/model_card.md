# Model Card — CrisisLens Disaster Classification Models

> **Format**: Hugging Face / Google Model Cards / MLSecOps Workshop 1  
> **Last Updated**: 2026-06-13  
> **Platform Version**: CrisisLens v3.0  
> **SDG Alignment**: SDG 11, SDG 13

---

# Model 1 — CLIP ViT-L/14（雙主投票：第一主）

## 1.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | CLIP ViT-L/14 |
| **Version (CrisisLens)** | `clip-vitl14-v1` |
| **Base Model** | `openai/clip-vit-large-patch14` |
| **Architecture** | Vision Transformer (ViT-L/14) |
| **Parameters** | 307M (visual) + 124M (text) |
| **Input** | RGB image 224×224 + text prompts |
| **Output** | Softmax probability over **5 disaster classes** |
| **Inference Method** | Linear-probe 優先；載入失敗自動退回 zero-shot 多 prompt 平均 |
| **Prompt Version（zero-shot 路徑）** | `multi-prompt-avg-5class-v2` |
| **Probe Version（linear-probe 路徑）** | `linear-probe-medic-6to5-v1` |
| **License** | MIT |
| **Paper** | Radford et al., *Learning Transferable Visual Models From Natural Language Supervision*, OpenAI (2021) |

---

## 1.2 Intended Use

| Use Case | Supported |
|----------|-----------|
| Intended | Classify disaster type from citizen-submitted photos（5 類） |
| Intended | Generate Top-3 probability distribution for human review |
| Intended | Flag uncertain predictions for admin review |
| Not intended | Medical image analysis |
| Not intended | Legal or official disaster determination |
| Not intended | Real-time video stream classification |

---

## 1.3 兩條推論路徑

### 路徑 A：Linear-Probe（優先）

`models/clip_linear_head.pth` 存放在 6 類 MEDIC 資料集上訓練的 linear head，啟動時依類別名稱從 6 類 weight/bias 中切片出 5 類（`_slice_head_to_current_classes`），再以 temperature **0.3814** 做溫度校準 softmax：

```
image → CLIP ViT-L/14 (frozen) → L2-normalised feature (768-dim)
       → Linear head (sliced 6→5) → logits / temperature(0.3814) → softmax(5)
```

- 切片邏輯（`models/clip_classifier.py`）：依 `CLASSES_EN` 名稱對齊舊 weight 行順序，任一類別缺失則回傳 `None` 並退回 zero-shot。
- 版本：`CLIP_PROBE_VERSION = "linear-probe-medic-6to5-v1"`（`utils/versions.py`）。

### 路徑 B：Zero-Shot 多 Prompt 平均（退路）

linear-probe 檔案缺失、維度不符或推論出錯時自動啟用：

```
For each class c (5 classes):
    prompts_c = [描述 c 的多條英文 prompt]
    mean_sim_c = average(cosine_similarity(image_feat, prompt_feat_i)
                         for prompt_i in prompts_c)

P(class) = softmax(100 × [mean_sim_c for c in classes])
```

**各類別 prompt 數量（5 類）：**

| Class | Number of Prompts |
|-------|------------------|
| Earthquake Damage | 7 |
| Flood | 4 |
| Fire | 4 |
| Typhoon or Storm Damage | 4 |
| Landslide | 5 |

> 乘以 100 後再做 softmax 以拉開分佈；原始餘弦相似度差距 ~0.02 → softmax 否則近均等。

### 統一入口

`classify_clip(image, prefer_probe=True)` 是雙主投票呼叫的唯一入口，結果含 `method` 欄位（`"linear_probe"` 或 `"zero_shot"`）與 `prompt_source`；`clip_prompt_version` 資料庫欄位依實際路徑記 probe 或 zero-shot 版本。

---

## 1.4 Decision Thresholds & Safety Flags

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Low confidence | `confidence < 0.50` | `need_review = 1` |
| Ambiguous Top-2 | `gap = score[1] − score[2] < 0.15` | `need_review = 1` |
| Model disagreement | `clip_class_zh ≠ effnet_class_zh` | `need_review = 1`, `model_agreement = 0` |

---

## 1.5 Performance Characteristics

> CLIP ViT-L/14 linear-probe：6 類 MEDIC head 切片至 5 類，溫度為 6 類校準值，套至 5 類為近似。Zero-shot 路徑之性能估計基於台灣災害圖像質性測試。

| Class | Qualitative Performance | Notes |
|-------|------------------------|-------|
| Earthquake Damage | High | Clear visual features (collapsed structures) |
| Flood | High | Water coverage is visually distinctive |
| Fire | High | Flames/smoke are distinctive |
| Typhoon or Storm Damage | **Medium** | Overlaps with general wind/storm damage |
| Landslide | Medium | Confused with earthquake debris |

**Observed Weaknesses:**
- Typhoon images with debris but no flooding → sometimes classified as Earthquake
- Indoor fire photos without visible flames → may classify as other disaster
- Overcast/rainy urban scenes → may confuse Flood and Typhoon

---

## 1.6 Limitations

| Limitation | Description |
|-----------|-------------|
| Temperature calibration mismatch | Linear-probe temperature (0.3814) 為 6 類資料集校準；切片至 5 類為近似，非精確校準 |
| Zero-shot gap | 無台灣特定 fine-tuning；CLIP 訓練資料以西方場景為主 |
| Reduced complementarity | Linear-probe 取代 zero-shot 後，兩條路徑互補性降低（同底座特徵） |
| No new 5-class validation data | 目前無獨立 5 類 held-out 集評估 linear-probe 切片後性能 |
| Confidence calibration | Softmax 分數非校準機率 |
| Adversarial vulnerability | CLIP 對 adversarial image perturbation 有一定脆弱性 |

---

## 1.7 Ethical Considerations

- CLIP 訓練資料為網路爬取，可能含地域偏差
- 絕不應作為緊急資源調配的唯一依據
- 所有高風險決策需人工驗證（`need_review` pipeline）

---

---

# Model 2 — EfficientNet-B0（雙主投票：第二主）

## 2.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | EfficientNet-B0（5 類 v2 微調） |
| **Version (CrisisLens)** | `efficientnet-b0-medic-5class-v2` |
| **Base Architecture** | EfficientNet-B0（`torchvision.models.efficientnet_b0`） |
| **Classifier Head** | `efficientnet_b0(weights=None)` + `nn.Linear(in_features, 5)`（取代原 `classifier[1]`） |
| **Parameters** | ~5.3M（backbone + 5 類分類頭） |
| **Input** | RGB image；Resize(288) → CenterCrop(256) → ImageNet-normalize |
| **Output** | Softmax probability over 5 disaster classes |
| **Training Dataset** | QCRI/MEDIC（disaster_types，5 類） |
| **Weights File** | `models/efficientnet_b0_5class_v2.pth` |
| **Mapping File** | `models/classes_5class_v2.json` |
| **License** | MIT (project code); MEDIC data under QCRI terms |

---

## 2.2 Architecture（來源 models/efficientnet_classifier.py:46-51）

```python
model = tvm.efficientnet_b0(weights=None)
in_features = model.classifier[1].in_features   # 1280
model.classifier[1] = nn.Linear(in_features, 5) # 5 類輸出
```

前處理（PIL，不依賴 NumPy）：

```
Resize(288) → CenterCrop(256) → frombuffer float32 tensor → ImageNet normalize
```

---

## 2.3 Class Mapping

| Index | English Label | Chinese Label |
|-------|--------------|---------------|
| 0 | Earthquake Damage | 地震或建築損壞 |
| 1 | Flood | 淹水 |
| 2 | Fire | 火災 |
| 3 | Typhoon or Storm Damage | 颱風或強風災損 |
| 4 | Landslide | 土石流或坍方 |

> EfficientNet-B0 v2 具備完整 5 類（含颱風），與 CLIP 5 類空間一致，消除了舊 ResNet50 的類別空間不對齊問題。

---

## 2.4 Evaluation Results（來源 docs/phase_b_state.md）

| Metric | Value |
|--------|-------|
| **Test Macro-F1** | **0.8375** |

**Per-Class Recall（test set）：**

| Class | Recall | Notes |
|-------|--------|-------|
| Earthquake Damage | 0.862 | |
| Flood | 0.877 | |
| Fire | 0.894 | |
| Typhoon or Storm Damage | **0.783** | **最弱類別** |
| Landslide | 0.843 | |

**額外注意：**

| Metric | Value | Notes |
|--------|-------|-------|
| Landslide Precision | **0.694** | 偏低，易與地震損壞混淆 |

---

## 2.5 Role in CrisisLens Pipeline（雙主投票）

```
CLIP ViT-L/14 (linear-probe / zero-shot fallback)
       │                    ↓ top_class_zh
       │         EfficientNet-B0 (5-class fine-tuned)
       │                    ↓ top_class_zh
       └── 比較 top_class_zh：
            ├── AGREE  → model_agreement = 1，primary = max(confidence)
            └── DISAGREE → model_agreement = 0, need_review = 1，primary = max(confidence)
```

- 兩者皆無結果 → `st.error` + stop。
- 單一模型可用 → 直接作為 primary。
- DB：`resnet_model_version` 欄位存 `EFFNET_MODEL_VERSION`（`efficientnet-b0-medic-5class-v2`）；`resnet_disaster_type / resnet_confidence` 欄位存 EfficientNet 結果（欄位名沿用以免 migration）。

---

## 2.6 MLOps Integration

| MLOps Element | Implementation |
|---------------|---------------|
| Version tracking | `EFFNET_MODEL_VERSION = "efficientnet-b0-medic-5class-v2"` in `utils/versions.py` |
| Inference logging | 每次預測記錄至 `model_runs`，含 `inference_latency_ms` 欄位 |
| Retraining data | Admin corrections（`used_for_retraining = 1`）可供 EfficientNet 再訓練 |
| Drift signal | model_agreement rate 於 MLOps dashboard 追蹤（`pages/6_MLOps.py`） |

**Retraining Trigger Criteria：**
- `need_review` 率 > 30%（連續 100 筆）
- model agreement rate < 60%（持續 7 天）

---

## 2.7 Limitations

| Limitation | Description |
|-----------|-------------|
| Typhoon recall lowest | Test recall 0.783；MEDIC `hurricane` 場景與台灣颱風有視覺差異 |
| Landslide precision low | Precision 0.694；易與地震損壞場景混淆 |
| No multi-label | 無法處理複合災害場景 |
| Domain gap | MEDIC 以西方圖像為主；台灣特有場景可能有差距 |

---

---

# Model 3 — DisasterCNN_v1（Legacy，已淘汰）

## 3.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | DisasterCNN_v1 |
| **Version (CrisisLens)** | `custom-cnn-medic-5class-v2`（legacy） |
| **Architecture** | 4-block CNN with BatchNorm + AdaptiveAvgPool |
| **Parameters** | ~400K |
| **Input** | RGB image 224×224 (ImageNet-normalized) |
| **Output** | Softmax probability over 5 disaster classes |
| **Training Dataset** | QCRI/MEDIC（disaster_types） |
| **Weights File** | `models/custom_cnn.pth`（保留未刪，已無人引用） |
| **License** | MIT (project code); MEDIC data under QCRI terms |

> **淘汰說明**：DisasterCNN_v1 自 CrisisLens v3.0 起已從雙主投票移除，不再參與推論。EfficientNet-B0 test macro-F1 **0.8375** 遠優於 CNN 的 **0.7012**，因此改以 EfficientNet-B0 為第二主。`custom_cnn_classifier.py` 與 `resnet_baseline.py` 檔案保留作為歷史存檔，已無 app 引用。

---

## 3.2 Architecture

```
Input: (B, 3, 224, 224)
│
├── Block 1: Conv2d(3→32, k=3, p=1) → BN → ReLU → MaxPool(2)   [112×112]
├── Block 2: Conv2d(32→64, k=3, p=1) → BN → ReLU → MaxPool(2)  [56×56]
├── Block 3: Conv2d(64→128, k=3, p=1) → BN → ReLU → MaxPool(2) [28×28]
├── Block 4: Conv2d(128→256, k=3, p=1) → BN → ReLU → MaxPool(2)[14×14]
│
└── Classifier: AdaptiveAvgPool2d(1) → Flatten → Dropout(0.3) → Linear(256→5)

Output: (B, 5) logits → softmax → probability distribution
```

---

## 3.3 Evaluation Results（Legacy 參考）

| Metric | Value |
|--------|-------|
| **Test Macro-F1** | **0.7012** |

> 相比 EfficientNet-B0 v2（macro-F1 0.8375）低約 13 個百分點，為淘汰的主因。

---

## 3.4 MLOps Integration（Legacy）

| MLOps Element | Implementation |
|---------------|---------------|
| Version tracking | `CNN_MODEL_VERSION = "custom-cnn-medic-5class-v2"` in `utils/versions.py` |
| Status | Legacy；`utils/versions.py` 保留版本常數以維持歷史 `model_runs` 可查詢性 |

---

---

# Model 4 — ResNet50 Baseline（Legacy，已淘汰）

## 4.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | ResNet50 Linear Probe |
| **Architecture** | ResNet50（ImageNet backbone, frozen）+ `nn.Linear(2048, 5)` |
| **Status** | **Legacy** — 已從 CrisisLens v3.0 雙主投票移除 |
| **Source File** | `models/resnet_baseline.py`（保留未刪，已無 app 引用） |

> ResNet50 原作為第二主，v3.0 升級後由 EfficientNet-B0 取代。舊 `resnet_*` 資料庫欄位名稱沿用，存放 EfficientNet-B0 結果（免 schema migration）；`event_matcher.py` 保留舊欄位命名為歷史資料別名。

---

---

# Model 5 — RAG System（Response Advisor）

## 5.1 System Overview

| Component | Value |
|-----------|-------|
| **Embedding Model** | `paraphrase-multilingual-MiniLM-L12-v2`（sentence-transformers） |
| **Index** | FAISS Flat L2，384-dimensional vectors |
| **Index Version** | `faiss-multilingual-minilm-v1` |
| **Generator** | Gemini **`gemini-2.5-flash`** |
| **RAG Prompt Version** | `gemini-flash-rag-v1` |
| **Retrieval** | Top-4 chunks by L2 similarity |
| **System Prompt** | 台灣災害應變專家身份；輸出 3–5 條具體建議 |
| **Fallback** | `FALLBACK_ADVICE`（per-class 靜態建議） + `GENERIC_FALLBACK_ADVICE`（未知類型通用建議） |

## 5.2 Knowledge Base Coverage

| Document | Disaster Type | Language |
|----------|--------------|----------|
| `earthquake_sop.md` | Earthquake | zh-TW |
| `flood_sop.md` | Flood | zh-TW |
| `fire_sop.md` | Fire | zh-TW |
| `typhoon_sop.md` | Typhoon | zh-TW |
| `landslide_sop.md` | Landslide | zh-TW |
| `emergency_guideline.md` | General emergency | zh-TW |

## 5.3 Safety Constraints

- RAG 輸出附明確免責聲明：*「本系統分類與建議僅供初步參考，不代表官方災害判定」*
- Gemini API 失敗時靜默切換至靜態 `FALLBACK_ADVICE`；5 類 + 未知類型均有安全 fallback（`rag/generator.py` 使用 `.get(zh, GENERIC_FALLBACK_ADVICE)`）
- RAG 建議每次重新生成，不持久儲存

---

---

# Cross-Model Summary

| Aspect | CLIP ViT-L/14 | EfficientNet-B0 | DisasterCNN_v1 | ResNet50 | RAG System |
|--------|---------------|-----------------|----------------|----------|-----------|
| **Role** | 雙主投票：第一主 | 雙主投票：第二主 | Legacy（已淘汰） | Legacy（已淘汰） | Response advisor |
| **Training** | Pre-trained (OpenAI)；linear-probe 切片 6→5 | Fine-tuned on MEDIC（5-class v2） | Trained from scratch（MEDIC） | Linear probe on MEDIC（frozen backbone） | Static KB + Gemini 2.5 Flash |
| **Parameters** | 431M | ~5.3M | ~400K | ~25M (frozen) | N/A |
| **Classes** | 5 | 5 | 5 | 5 | N/A |
| **Key Metric** | 質性評估（linear-probe 無新 5 類驗證集） | Test Macro-F1: **0.8375** | Test Macro-F1: 0.7012（legacy） | Val Acc: ~82–85%（legacy） | N/A |
| **Failure mode** | Probe temperature 為 6 類近似校準；互補性下降 | Typhoon recall 最弱 (0.783)；Landslide precision 偏低 (0.694) | 已淘汰 | 已淘汰 | Gemini API unavailable |
| **Mitigation** | 信心閾值 + model_agreement | model_agreement=0 觸發 need_review | — | — | FALLBACK_ADVICE + GENERIC_FALLBACK_ADVICE |
| **MLOps** | `clip-vitl14-v1` / `linear-probe-medic-6to5-v1` / `multi-prompt-avg-5class-v2` | `efficientnet-b0-medic-5class-v2` | `custom-cnn-medic-5class-v2`（legacy） | 已移除 | `faiss-multilingual-minilm-v1` / `gemini-flash-rag-v1` |

---

# Appendix — Complete Version Constants

來源：`utils/versions.py`

| Constant | Value |
|----------|-------|
| `CLIP_MODEL_VERSION` | `clip-vitl14-v1` |
| `CLIP_PROMPT_VERSION` | `multi-prompt-avg-5class-v2` |
| `CLIP_PROBE_VERSION` | `linear-probe-medic-6to5-v1` |
| `EFFNET_MODEL_VERSION` | `efficientnet-b0-medic-5class-v2` |
| `CNN_MODEL_VERSION` | `custom-cnn-medic-5class-v2` (legacy) |
| `RAG_INDEX_VERSION` | `faiss-multilingual-minilm-v1` |
| `RAG_PROMPT_VERSION` | `gemini-flash-rag-v1` |
| `AGGREGATION_RULE_VERSION` | `disaster-group-distance-timewindow-v4` |
| `PRIORITY_RULE_VERSION` | `svcp-weighted-v2` |

---

# Appendix — MLOps Thresholds & Retraining Triggers

| Parameter | Value | Source |
|-----------|-------|--------|
| `CLIP_LOW_CONF_THRESHOLD` | 0.50 | `utils/versions.py` |
| `CLIP_TOP2_GAP_THRESHOLD` | 0.15 | `utils/versions.py` |
| `need_review` 觸發條件 | `confidence < 0.50` OR `top2_gap < 0.15` OR `model_agreement == 0` | `app.py` |
| Retraining trigger A | `need_review` 率 > 30%（連續 100 筆） | `docs/phase_b_state.md` / `docs/system_card.md` |
| Retraining trigger B | model agreement < 60%（持續 7 天） | `docs/phase_b_state.md` / `docs/system_card.md` |
| `inference_latency_ms` | 每次推論記錄至 `model_runs` 表 | `app.py` |

---

# Known Limitations & Future Work

## 已知限制

1. **Linear-probe temperature 近似**：`0.3814` 為 6 類資料集校準，切至 5 類後非精確校準。
2. **互補性下降**：CLIP linear-probe 取代 zero-shot 後，兩條路徑（CLIP + EfficientNet）同樣依賴 CLIP 底座特徵，互補性降低。
3. **無新 5 類驗證集**：linear-probe 切片後性能未有獨立 5 類 held-out 集量化評估。
4. **颱風場景弱點**：EfficientNet-B0 颱風 recall 0.783 為五類最低；MEDIC `hurricane` 場景與台灣颱風有視覺差異。
5. **Landslide precision 偏低**：0.694，易與地震損壞混淆。

## 未來工作

- 以純 5 類資料集重新訓練 CLIP linear-probe，取得精確溫度校準。
- 收集台灣颱風實拍圖像，補強 EfficientNet-B0 颱風類別。
- 建立 5 類獨立測試集，對 linear-probe 路徑做定量評估。
- 增加 Landslide 訓練資料或調整 class weight 以提升 precision。
