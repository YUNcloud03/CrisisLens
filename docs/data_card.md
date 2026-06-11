# Data Card — CrisisLens Disaster Classification Platform

> **Format**: Google Data Cards / MLSecOps Workshop 1  
> **Last Updated**: 2026-06-08  
> **Version**: v2.0  
> **SDG Alignment**: SDG 11 (Sustainable Cities), SDG 13 (Climate Action)

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
| **Task** | 6-class image classification |

---

### A.2 Label Mapping (Original → CrisisLens)

| MEDIC Original Label | CrisisLens English Label | CrisisLens 中文標籤 | Note |
|---------------------|--------------------------|---------------------|------|
| `earthquake` | Earthquake Damage | 地震或建築損壞 | Direct mapping |
| `flood` | Flood | 淹水 | Direct mapping |
| `fire` | Fire | 火災 | Direct mapping |
| `hurricane` | Typhoon or Storm Damage | 颱風或強風災損 | Domain-adapted for Taiwan |
| `landslide` | Landslide | 土石流或坍方 | Direct mapping |
| `not_disaster` | Other or No Disaster | 其他或無明顯災害 | Merged with other_disaster |
| `other_disaster` | Other or No Disaster | 其他或無明顯災害 | **Merged** into class 5 |

> ⚠️ **Domain Adaptation Note**: MEDIC `hurricane` was remapped to `Typhoon or Storm Damage` to match Taiwan's meteorological terminology. The training images originate predominantly from Atlantic hurricanes, creating a **distribution shift** for Taiwan typhoon scenarios.

---

### A.3 Data Statistics

| Class | Approx. Sample Count | % of Dataset |
|-------|---------------------|--------------|
| Earthquake Damage | ~3,200 | 18% |
| Flood | ~2,800 | 16% |
| Fire | ~2,100 | 12% |
| Typhoon or Storm Damage | ~1,500 | 9% |
| Landslide | ~1,200 | 7% |
| Other or No Disaster | **~6,800** | **38%** |
| **Total** | **~17,600** | 100% |

> ⚠️ **Class Imbalance**: `Other or No Disaster` accounts for ~38% of data. Addressed with `WeightedRandomSampler` during training.

---

### A.4 Data Collection Process

- **Source**: Social media images (Twitter, Flickr) collected during real disaster events
- **Collection Period**: 2012–2020
- **Geographic Coverage**: Primarily North America, Caribbean, South Asia
- **Annotation**: Crowd-sourced with expert verification
- **Image Format**: JPEG/PNG, variable resolution
- **Preprocessing Applied**:
  - Resize → 256×256, CenterCrop → 224×224
  - ImageNet normalization: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]

---

### A.5 Train / Validation Split

| Split | Count | Ratio |
|-------|-------|-------|
| Train | ~14,080 | 80% |
| Validation | ~3,520 | 20% |
| Test | Not used (no held-out test) | — |

> Split performed with `random_split(seed=42)`.

---

### A.6 Known Biases and Limitations

| Bias Type | Description | Impact |
|-----------|-------------|--------|
| **Geographic bias** | Mostly Western hemisphere events | Reduced accuracy on Taiwan-specific disaster scenes |
| **Platform bias** | Social media photos (Twitter/Flickr) | May not generalize to citizen reporting styles |
| **Class merge bias** | `other_disaster` merged into `not_disaster` | Loss of granularity for non-standard disasters |
| **Temporal bias** | 2012–2020 imagery | May not reflect modern urban environments |
| **Hurricane ≠ Typhoon** | Atlantic hurricanes vs. Pacific typhoons have different visual patterns | Lower recall on typhoon class (~48%) |

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
| `model_agreement` | INT | 1 = CLIP and CNN agree |
| `has_injured_people` | INT | User-reported field conditions |
| `rag_advice` | TEXT | AI-generated response advice (JSON) |

---

### B.3 Privacy and Safety (Production Data)

| Risk | Level | Mitigation |
|------|-------|-----------|
| GPS coordinates reveal user location | **High** | User consent required; coordinates not displayed publicly |
| Photos may show injured persons | **High** | Admin-only access; not publicly shared |
| Description text may contain PII | **Medium** | Free-text; no NLP extraction performed |
| Data retention | **Medium** | No automatic deletion policy (future work) |

---

### B.4 Data Quality Flags

| Flag | Condition | Action |
|------|-----------|--------|
| `need_review = 1` | Confidence < 50%, or Top-1/Top-2 gap < 15%, or model disagreement | Admin manual review |
| `model_agreement = 0` | CLIP label ≠ CNN label (Chinese comparison) | Auto-flagged for review |
| `grid_id IS NULL` | No GPS + no city/district provided | Report excluded from heatmap |

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
| Size | ~17,600 images | Growing (12 reports as of 2026-06-08) |
| Source | Academic / Social media | Real-world citizen reports |
| Language | English labels | Bilingual (EN labels + ZH display) |
| Privacy risk | Low (public social media) | High (GPS + personal photos) |
| Geographic coverage | Global (Western bias) | Taiwan-focused |
| Quality control | Crowd annotation + expert review | AI confidence + human review |
