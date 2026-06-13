# CrisisLens 5 類災害升級計畫

**Date**: 2026-06-11
**分支**: `feature/5class-disaster`(基於 `master` @ d54bdf1,已確認乾淨)
**EDA 依據**: [eda_5class_phase1_analysis.md](eda_5class_phase1_analysis.md)
**訓練 notebook**: [train_5class_disaster_kaggle_v2.ipynb](../train_5class_disaster_kaggle_v2.ipynb)(待 Kaggle 跑完取得權重)

---

## 0. 目標與已定決策

把現行 **6 類**(地震/淹水/火災/颱風/土石流 + 守門類「其他或無明顯災害」)升級為 **純 5 類**。

| 決策項 | 結論 |
|---|---|
| **非災害守門** | **直接改純 5 類**——拿掉「其他或無明顯災害」,假設輸入皆為災害照 |
| **模型角色** | **雙主投票**——CLIP(5 類 zero-shot)+ 訓練好的 5 類模型(v2 的 EfficientNet-B0 或自訓 CNN,取 macro-F1 高者)都當主;一致→高信心,不一致→`need_review` |
| **分支基底** | `master`(CrisisLens v2.0 完整版,含 safety/auth/MLOps) |

### 5 類定義(對齊 v2 notebook 與現有 config 前 5 項)

```
EN: Earthquake Damage / Flood / Fire / Typhoon or Storm Damage / Landslide
ZH: 地震或建築損壞 / 淹水 / 火災 / 颱風或強風災損 / 土石流或坍方
```

### EDA 重點(摘自 phase1 分析,影響本計畫)

- **颱風(Hurricane)是瓶頸**:44% 影像幾乎無災損(衛星圖/氣象圖/meme),kNN 免訓練 recall 僅 0.40。
- **免訓練下限 acc = 0.659**(ImageNet 特徵 + kNN):微調模型 macro-F1 沒明顯超過 ~0.75 代表訓練流程有問題。
- v2 notebook 已落實:train 去重、val macro-F1 選模、增強修正、輸入 256、去洩漏評估。

---

## Phase A — 不依賴權重(現在即可做)

> 這些改動**不碰** `custom_cnn.pth` / `custom_cnn_classes.json`,因此 CNN 仍讀自己的 6 類權重、CLIP 變 5 類,兩者並存**不會 crash**(只是過渡期 CNN 會多輸出「其他」、雙模型常不一致)。

| # | 檔案:行 | 現況 | 改成 |
|---|---|---|---|
| A1 | `utils/config.py:18-25` | CLASSES_EN 6 類 | 去掉第 6 項 "Other or No Disaster" |
| A1 | `utils/config.py:27-34` | CLASSES_ZH 6 類 | 去掉第 6 項「其他或無明顯災害」 |
| A1 | `utils/config.py:39-64` | PROMPT_SETS 三組各 6 條 | 各刪最後一條(normal/no disaster) |
| A1 | `utils/config.py:67-108` | MULTI_PROMPT_SETS 含 "Other or No Disaster" 整塊 | 刪該鍵 4 條 prompt |
| A1 | `utils/config.py:115` | `NUM_CLASSES = 6` | `= 5` |
| A2 | `utils/versions.py:9` | `CLIP_PROMPT_VERSION = "multi-prompt-avg-v1"` | `"multi-prompt-avg-5class-v2"` |
| A2 | `utils/versions.py:11` | `CNN_MODEL_VERSION = "custom-cnn-medic-6class-v1"` | `"custom-cnn-medic-5class-v2"`(或 efficientnet) |
| A3 | `rag/prompts.py:25-67` | FALLBACK_ADVICE 含「其他或無明顯災害」 | 刪該鍵整塊 |
| A3 ⚠ | `rag/generator.py:96` | `FALLBACK_ADVICE.get(t, FALLBACK_ADVICE["其他或無明顯災害"])` | **改 fallback key**(指向已刪鍵會 KeyError)→ 用 `.get(t, [])` 或新增通用建議 |
| A4 | `aggregation/event_matcher.py:37-50` | DISASTER_GROUPS 有 "other" 組 | 刪 "other" 組 |
| A4 | `aggregation/event_matcher.py:30-35` | `TIME_WINDOWS["other"]` | 刪 |
| A4 | `aggregation/event_matcher.py:300-312` | `_TYPE_ZH` 含 Other/Non Damage | 刪該兩行 |
| A5 | `aggregation/scoring.py:11-16` | `_HIGH_RISK` 含 Other 變體 | 移除 Other/Non Damage |
| A5 | `aggregation/scoring.py:167-177` | `_GEO_RULES` 含 Non Damage | 移除該規則 |
| A6 | `pages/2_Event_Dashboard.py:27` | filter_type 用**第三套舊命名**(Damaged Infrastructure/Fire Disaster/...) | 統一成新 5 類(修既有不一致) |
| A7 | `pages/3_Event_Detail.py:206-211` | 管理員修正下拉 6 類 | 改 5 類 |
| A8（可選） | `seed.py` / `pages/4_H3_Heatmap.py` | 測試/demo 資料含舊類別 | 視需要清理 |

**完全動態、無需改**:`models/clip_classifier.py`(從 config 讀)、`pages/6_MLOps.py`(讀版本號)、`safety/policies.py`(自由文本規則)、`db/schema.sql`(TEXT 欄)。

---

## Phase B — 等 v2 權重(Kaggle notebook 跑完後)

| # | 動作 | 細節 |
|---|---|---|
| B1 | **放權重** | 把 Kaggle 下載的最佳模型(看 v2 的 `clean_macroF1`:`efficientnet_b0_5class_v2.pth` 或 `custom_cnn_5class_v2.pth`)+ `classes_5class_v2.json` 放 `models/`,改名對齊 classifier 期望路徑 |
| B2 | **classifier 對齊** | **若選自訓 CNN**:換 `custom_cnn.pth` + `custom_cnn_classes.json`(5 類);前處理對齊 v2 的 **256 輸入**(`custom_cnn_classifier.py` 的 `_PIL_TRANSFORMS` Resize256/Crop224 → Resize288/Crop256)。<br>**若選 EfficientNet-B0**:現有 classifier 寫死 `DisasterCNN_v1`,需新增 backbone 載入(`build_backbone`)+ 256 前處理 → 建議新增 `models/efficientnet_classifier.py`,或讓 `custom_cnn_classifier` 支援 `backbone` 欄位 |
| B3 | **app.py 雙主投票** | 改 `app.py:534-587` 分類編排:CLIP 與「訓練模型」並列雙主;一致→primary=該類、高信心;不一致→`need_review=1`、primary 取信心高者。更新 `model_agreement` / `need_review` / DB 寫入(`clip_disaster_type` / `cnn_disaster_type` / `disaster_type`)。`model_mode` 預設改「CLIP + 5 類模型雙主」 |
| B4 | **ResNet 處置** | 現有 ResNet 是**另一套舊 5 類**(Damaged Infrastructure 等,命名對不上),從投票淘汰(`_USE_RESNET` 預設關或從 `model_mode` 移除)。要保留當第三方參考須先重訓成新 5 類命名(非必要) |
| B5 | **custom_cnn_classes.json** | 同步改 5 類(`num_classes=5`、`class_to_idx` 重編 0–4)。⚠ **務必與 B1 權重同時改**——權重 6 類 FC 配 5 類 json 會 `load_state_dict` size mismatch |
| B6 | **端到端測試** | 跑 app,各類測試圖 + 一張非災害圖;確認 5 類輸出、雙主投票、`need_review`、DB 寫入、RAG 建議、無殘留「其他」KeyError |
| B7 | **DB 既有資料** | 舊 reports 的 `disaster_type` 可能有「其他或無明顯災害」或 ResNet 舊命名;TEXT 欄不報錯,但 dashboard 篩選/聚合會冒出舊類別。決定保留(歷史)或清理 |

---

## 過渡期與風險

- **過渡期安全**:Phase A 改完、Phase B 未完時,只要**不動** `custom_cnn_classes.json` / `custom_cnn.pth`,app 可正常跑(CLIP 5 類、CNN 6 類並存)。最乾淨的做法是 **Phase A + B 在本分支一次做完再合併 master,中途不合併**。
- **無守門的代價**:純 5 類沒有「其他」可退,雙主投票不一致送審是唯一品質防線。建議加「**兩模型信心都低 → need_review**」當補強。
- **EfficientNet vs CNN**:依 v2 的 `clean_macroF1` 擇優。EfficientNet 通常勝,但需改 classifier 載入(B2);自訓 CNN 改動最小,只換權重+json+前處理。
- **颱風瓶頸**:若上線後颱風 recall 仍卡 0.5–0.6,屬資料(標籤定義)天花板,需另開 P4(damage_severity 多任務頭或過濾 little_or_none),非本次升級範圍。

## 順手(可選)

- master 歷史含 2 個過時訓練計畫 docs(本地舊線 `8a7c329`/`6608149` 帶入):**無害**,**不建議**為它們改寫已推送的 master 歷史。若在意,可在本分支刪檔(不影響 master)。

---

## 執行順序建議

```
Phase A(現在):A1 config → A2 versions → A3 RAG(注意 generator fallback key)
              → A4/A5 聚合評分 → A6/A7 UI → (A8 可選)
              ↓ 此時 app 可跑(CLIP 已 5 類,CNN 暫留 6 類)
Phase B(權重到位):B1 放權重 → B5 改 json(與 B1 同時)→ B2 classifier 對齊
              → B3 雙主投票 → B4 ResNet 淘汰 → B6 測試 → B7 DB 清理
              ↓ 全部完成後再合併回 master
```
