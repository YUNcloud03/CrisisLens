# Model Card — CrisisLens Disaster Classification Models

> **Format**: Hugging Face / Google Model Cards / MLSecOps Workshop 1  
> **Last Updated**: 2026-06-08  
> **Platform Version**: CrisisLens v2.0  
> **SDG Alignment**: SDG 11, SDG 13

---

# Model 1 — CLIP ViT-L/14 (Primary Classifier)

## 1.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | CLIP ViT-L/14 |
| **Version (CrisisLens)** | `clip-vitl14-v1` |
| **Base Model** | `openai/clip-vit-large-patch14` |
| **Architecture** | Vision Transformer (ViT-L/14) |
| **Parameters** | 307M (visual) + 124M (text) |
| **Input** | RGB image 224×224 + text prompts |
| **Output** | Softmax probability over 6 disaster classes |
| **Inference Method** | Multi-prompt averaging (zero-shot) |
| **Prompt Version** | `multi-prompt-avg-v1` |
| **License** | MIT |
| **Paper** | Radford et al., *Learning Transferable Visual Models From Natural Language Supervision*, OpenAI (2021) |

---

## 1.2 Intended Use

| Use Case | Supported |
|----------|-----------|
| ✅ Intended | Classify disaster type from citizen-submitted photos |
| ✅ Intended | Generate Top-3 probability distribution for human review |
| ✅ Intended | Flag uncertain predictions for admin review |
| ❌ Not intended | Medical image analysis |
| ❌ Not intended | Legal or official disaster determination |
| ❌ Not intended | Real-time video stream classification |

---

## 1.3 Inference Method — Multi-Prompt Averaging

Instead of a single prompt per class, CrisisLens uses **multiple descriptive prompts per disaster type** and averages the cosine similarity scores:

```
For each class c:
    prompts_c = ["a photo of a flooded street", "floodwater covering roads", ...]
    mean_sim_c = average(cosine_similarity(image, prompt_i) for prompt_i in prompts_c)

P(class) = softmax(100 × [mean_sim_c for c in classes])
```

**Prompt counts per class:**

| Class | Number of Prompts |
|-------|------------------|
| Earthquake Damage | 7 |
| Flood | 4 |
| Fire | 4 |
| Typhoon or Storm Damage | 4 |
| Landslide | 5 |
| Other or No Disaster | 4 |

> Temperature scaling (×100) is applied before softmax to produce peaked distributions. Without scaling, raw cosine similarities (~0.2) yield near-uniform distributions (~16.7% per class).

---

## 1.4 Decision Thresholds & Safety Flags

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Low confidence | `confidence < 0.50` | `need_review = 1` |
| Ambiguous Top-2 | `gap = score[1] − score[2] < 0.15` | `need_review = 1` |
| Model disagreement | `clip_class_zh ≠ cnn_class_zh` | `need_review = 1`, `model_agreement = 0` |

---

## 1.5 Performance Characteristics

> Note: CLIP ViT-L/14 is used **zero-shot** — no fine-tuning on MEDIC. Performance estimates are based on qualitative testing on Taiwan disaster images.

| Class | Qualitative Performance | Notes |
|-------|------------------------|-------|
| Earthquake Damage | High | Clear visual features (collapsed structures) |
| Flood | High | Water coverage is visually distinctive |
| Fire | High | Flames/smoke are distinctive |
| Typhoon or Storm Damage | **Medium** | Overlaps with general wind/storm damage |
| Landslide | Medium | Confused with earthquake debris |
| Other or No Disaster | Medium | Default class when no clear disaster |

**Observed Weaknesses:**
- Typhoon images with debris but no flooding → sometimes classified as Earthquake
- Indoor fire photos without visible flames → may classify as Other
- Overcast/rainy urban scenes → may confuse Flood and Typhoon

---

## 1.6 Limitations

| Limitation | Description |
|-----------|-------------|
| Zero-shot gap | No Taiwan-specific fine-tuning; CLIP's training data is largely Western |
| Language-vision alignment | English prompts may not capture Taiwan-specific disaster vocabulary |
| Confidence calibration | Softmax scores are not calibrated probabilities |
| Adversarial vulnerability | CLIP is susceptible to adversarial image perturbations |
| Hallucination risk | High-confidence wrong predictions possible for out-of-distribution images |

---

## 1.7 Ethical Considerations

- CLIP was trained on internet-scraped data that may contain biases
- Should **never** be used as the sole basis for emergency resource allocation
- All high-stakes decisions require human verification (`need_review` pipeline)

---

---

# Model 2 — ResNet50 Linear Probe (Secondary Classifier)

## 2.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | ResNet50 Linear Probe |
| **Version (CrisisLens)** | `resnet50-linear-probe-medic-5class-v1` |
| **Base Architecture** | ResNet50 (ImageNet backbone, frozen) |
| **Classifier Head** | Single Linear layer replacing `fc` |
| **Parameters** | ~25M (backbone, frozen) + ~10K (linear head) |
| **Input** | RGB image 224×224 (ImageNet-normalized) |
| **Output** | Softmax probability over 5 disaster classes |
| **Training Dataset** | QCRI/MEDIC (disaster_types, 7→5 classes) |
| **Weights File** | `models/resnet50_linear.pth` (90 MB) |
| **Training Script** | `models/train_resnet.py` |
| **License** | MIT (project code); MEDIC data under QCRI terms |

---

## 2.2 Class Mapping

| Index | English Label | Chinese Label | MEDIC Source |
|-------|--------------|---------------|-------------|
| 0 | Damaged_Infrastructure | 地震或建築損壞 | `earthquake` |
| 1 | Fire_Disaster | 火災 | `fire` |
| 2 | Land_Disaster | 土石流或坍方 | `landslide` |
| 3 | Non_Damage | 其他或無明顯災害 | `not_disaster` + `other_disaster` |
| 4 | Water_Disaster | 淹水 | `flood` + `hurricane` merged |

> ⚠️ **ResNet50 has only 5 classes** — `颱風或強風災損` is **not** a separate class. Typhoon images are typically mapped to `Water_Disaster` (淹水). This creates intentional `model_agreement = 0` when CLIP classifies an image as typhoon but ResNet50 classifies it as water disaster.

---

## 2.3 Training Configuration

| Hyperparameter | Value |
|---------------|-------|
| Backbone | ResNet50 (pretrained on ImageNet, all layers **frozen**) |
| Classifier | `nn.Linear(2048, 5)` replacing original `fc` |
| Optimizer | Adam |
| Learning Rate | 1e-3 |
| Batch Size | 32 |
| Epochs | 10 |
| Train / Val Split | 80 / 20 (seed=42) |
| Class Balancing | WeightedRandomSampler |
| Preprocessing | Resize(256) → CenterCrop(224) → ToTensor → ImageNet Normalize |

---

## 2.4 Evaluation Results

| Metric | Value |
|--------|-------|
| **Validation Accuracy** | **~82–85%** (5-class task) |
| Backbone | Frozen ImageNet features |

**Per-Class Performance (estimated):**

| Class | Precision | Recall | Notes |
|-------|-----------|--------|-------|
| Damaged_Infrastructure | ~0.83 | ~0.82 | Strong — ResNet ImageNet features robust for structural damage |
| Fire_Disaster | ~0.87 | ~0.85 | Strong — flame/smoke features well-separated |
| Land_Disaster | ~0.78 | ~0.76 | Good — mudslide visual texture distinct |
| Non_Damage | ~0.88 | ~0.90 | Very good — largest class, high confidence |
| Water_Disaster | ~0.80 | ~0.78 | Good — includes typhoon water scenes |

> Note: 5-class formulation achieves higher per-class accuracy than 6-class CNN because typhoon is merged into water disaster, removing a low-recall class.

---

## 2.5 Role in CrisisLens Pipeline

ResNet50 is the **secondary classifier** used in "兩者比較 (CLIP + ResNet50)" mode:

```
CLIP ViT-L/14  →  Primary classification (top_class_zh)
       │
       ↓ compare Chinese labels
ResNet50 LP    →  Secondary validation (top_class_zh)
       │
       ├── AGREE  → model_agreement = 1
       └── DISAGREE → model_agreement = 0, need_review = 1
```

**Known intentional disagreement**: When CLIP classifies as `颱風或強風災損`, ResNet50 has no matching class and will classify as `淹水` → `model_agreement = 0`. This is expected and educationally demonstrates class-space mismatch between models.

---

## 2.6 MLOps Integration

| MLOps Element | Implementation |
|---------------|---------------|
| Version tracking | `RESNET_MODEL_VERSION = "resnet50-linear-probe-medic-5class-v1"` in `utils/versions.py` |
| Inference logging | Every ResNet50 prediction stored as `resnet_model_version` in `model_runs` records |
| Retraining data | Admin corrections with `used_for_retraining = 1` can feed ResNet50 fine-tuning |
| Drift signal | model_agreement rate tracked in MLOps dashboard |

---

## 2.7 Limitations

| Limitation | Description |
|-----------|-------------|
| Only 5 classes | No typhoon class — intentional design decision to align with MEDIC labels |
| Domain gap | ImageNet pretraining is Western-biased; Taiwan-specific scenes may differ |
| Frozen backbone | Linear probe limits adaptation to disaster-specific visual features |
| No multi-label | Cannot handle mixed disaster scenes |

---

---

# Model 3 — DisasterCNN_v1 (Auxiliary Validator)

## 3.1 Model Details

| Field | Value |
|-------|-------|
| **Name** | DisasterCNN_v1 |
| **Version (CrisisLens)** | `custom-cnn-medic-6class-v1` |
| **Architecture** | 4-block CNN with BatchNorm + AdaptiveAvgPool |
| **Parameters** | ~400K |
| **Input** | RGB image 224×224 (ImageNet-normalized) |
| **Output** | Softmax probability over 6 disaster classes |
| **Training Dataset** | QCRI/MEDIC (disaster_types, 7→6 classes) |
| **Weights File** | `models/custom_cnn.pth` (1.5 MB) |
| **License** | MIT (project code); MEDIC data under QCRI terms |

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
└── Classifier: AdaptiveAvgPool2d(1) → Flatten → Dropout(0.3) → Linear(256→6)

Output: (B, 6) logits → softmax → probability distribution
```

---

## 3.3 Training Configuration

| Hyperparameter | Value |
|---------------|-------|
| Optimizer | Adam |
| Learning Rate | 1e-3 |
| LR Scheduler | StepLR (step=2, γ=0.5) |
| Batch Size | 32 |
| Epochs | 5 |
| Train / Val Split | 80 / 20 (seed=42) |
| Class Balancing | WeightedRandomSampler |
| Backbone freezing | Backbone fully trained (no pretrained backbone) |

---

## 3.4 Evaluation Results

| Metric | Value |
|--------|-------|
| **Validation Accuracy** | **68.57%** |
| Training Loss (final epoch) | ~0.68 |

**Per-Class Performance (estimated from val set):**

| Class | Precision | Recall | Notes |
|-------|-----------|--------|-------|
| Earthquake Damage | ~0.72 | ~0.70 | Good — clear visual features |
| Flood | ~0.75 | ~0.72 | Good — water is distinctive |
| Fire | ~0.78 | ~0.76 | Good — flames/smoke |
| Typhoon or Storm Damage | ~0.55 | ~0.48 | **Weak** — visual overlap with other classes |
| Landslide | ~0.60 | ~0.58 | Medium — confused with earthquake |
| Other or No Disaster | ~0.71 | ~0.75 | Good — catches non-disaster |

> ⚠️ **Typhoon recall is only ~48%** — the model frequently misclassifies typhoon damage as "Other" because MEDIC's `hurricane` training examples are visually different from Taiwan typhoons.

---

## 3.5 Role in CrisisLens Pipeline

DisasterCNN_v1 is the **legacy auxiliary validator** (standalone "自訓練 CNN" mode):

```
CLIP ViT-L/14  →  Primary classification (top_class_zh)
       │
       ↓ compare Chinese labels
DisasterCNN_v1 →  Secondary validation (top_class_zh)
       │
       ├── AGREE  → model_agreement = 1
       └── DISAGREE → model_agreement = 0, need_review = 1
```

**CLIP takes precedence.** CNN only triggers review, never overrides CLIP's decision.

---

## 3.6 MLOps Integration

| MLOps Element | Implementation |
|---------------|---------------|
| Version tracking | `CNN_MODEL_VERSION = "custom-cnn-medic-6class-v1"` stored in every `model_runs` record |
| Retraining data | `admin_corrections` table collects human-corrected labels (`used_for_retraining = 1`) |
| Inference logging | Every prediction stored in `reports` table with confidence scores |
| Drift signal | `need_review` rate over time indicates model performance degradation |
| Human-in-the-loop | Admin reviews flagged reports; corrections form new training labels |

**Retraining Trigger Criteria (proposed):**
- `need_review` rate > 30% over 100 consecutive reports
- Model agreement rate < 60% for any 7-day window

---

## 3.7 Limitations

| Limitation | Description |
|-----------|-------------|
| Dataset domain gap | Trained on Western disaster images; Taiwan scenes may differ |
| Low typhoon accuracy | MEDIC `hurricane` ≠ Taiwan `typhoon` visually |
| Small model capacity | ~400K params may underfit complex scenes |
| No fine-grained localization | Classifies whole image; cannot locate damage region |
| Single-label assumption | Cannot handle multi-hazard scenes |

---

## 3.8 Safety Considerations

| Risk | Mitigation |
|------|-----------|
| False negative (miss a disaster) | Combined with CLIP; disagreement triggers review |
| Overconfident wrong prediction | Confidence threshold < 50% → `need_review` |
| Adversarial input | Low model complexity provides some robustness; not formally verified |
| Out-of-distribution input | Non-disaster images return high "Other" probability |

---

---

# Model 4 — RAG System (Response Advisor)

## 4.1 System Overview

| Component | Value |
|-----------|-------|
| **Embedding Model** | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| **Index** | FAISS Flat L2, 384-dimensional vectors |
| **Index Version** | `faiss-multilingual-minilm-v1` |
| **Generator** | Gemini 2.0 Flash (`gemini-flash-rag-v1`) |
| **Retrieval** | Top-4 chunks by L2 similarity |
| **Fallback** | Built-in static guidelines when API unavailable |

## 3.2 Knowledge Base Coverage

| Document | Disaster Type | Language |
|----------|--------------|----------|
| `earthquake_sop.md` | Earthquake | zh-TW |
| `flood_sop.md` | Flood | zh-TW |
| `fire_sop.md` | Fire | zh-TW |
| `typhoon_sop.md` | Typhoon | zh-TW |
| `landslide_sop.md` | Landslide | zh-TW |
| `emergency_guideline.md` | General emergency | zh-TW |

## 4.3 Safety Constraints

- RAG output is displayed with explicit disclaimer: *"本系統分類與建議僅供初步參考，不代表官方災害判定"*
- Gemini API failures fall back to static guidelines silently
- No hallucinated advice is stored permanently — RAG advice is regenerated on each submission

---

# Cross-Model Summary

| Aspect | CLIP ViT-L/14 | ResNet50 LP | DisasterCNN_v1 | RAG System |
|--------|---------------|-------------|----------------|-----------|
| Role | Primary classifier | Secondary classifier | Auxiliary (standalone) | Response advisor |
| Training | Pre-trained (OpenAI) | Fine-tuned on MEDIC (5-class) | Trained from scratch (6-class) | Static KB + LLM |
| Parameters | 431M | ~25M (frozen) | ~400K | N/A |
| Classes | 6 | 5 (no typhoon) | 6 | N/A |
| Accuracy | Qualitative: High | Val Acc: ~82–85% | Val Acc: 68.57% | N/A |
| Failure mode | Adversarial images | Typhoon → Water_Disaster (expected) | Typhoon misclassification | Gemini API unavailable |
| Mitigation | Confidence thresholds | model_agreement = 0 triggers review | CLIP takes precedence | Fallback guidelines |
| MLOps | Version tracked | Version tracked + retraining data | Version tracked + retraining data | Index version tracked |
