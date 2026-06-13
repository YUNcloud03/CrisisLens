# Phase B 執行狀態（接續用快照）

> 5 類災害升級的 Phase B 進度。對話上下文壓縮後，靠這份檔案接續。
> 完整計畫見 [upgrade_to_5class_plan.md](upgrade_to_5class_plan.md)。

**分支**: `feature/5class-disaster`　**狀態**: **B1–B4 完成，B5 程式面驗證通過；剩瀏覽器實圖 e2e（未 commit）**

## 已定決策
- 升級目標：6 類 → 純 5 類（拿掉「其他或無明顯災害」守門類）
- 整合方式：**雙主投票** = CLIP（5 類 zero-shot）+ **EfficientNet-B0**（v2 微調）
- 第二主選 EfficientNet-B0：v2 完勝自訓 CNN（test macro-F1 **0.8375** vs 0.7012）
- v2 各類 recall：地震 .862 / 淹水 .877 / 火災 .894 / **颱風 .783（最弱）** / 土石流 .843；Landslide precision 偏低 0.694
- （本次問答拍板）UI 選單全面換新（雙主預設 / CLIP / EfficientNet，移除 ResNet50 與舊 CNN）；DB **沿用 resnet_\* 欄位**存 EfficientNet 結果（免 migration）；event_matcher 舊 ResNet 命名**保留為歷史資料別名**，只刪守門類

## Phase B 完成內容
- **B1 ✓** 權重已放：`models/efficientnet_b0_5class_v2.pth` + `classes_5class_v2.json`
- **B2 ✓** 新增 `models/efficientnet_classifier.py`：efficientnet_b0 backbone（`classifier[1]=Linear(in,5)`）、Resize(288)+CenterCrop(256)、`_pil_to_tensor`（frombuffer 繞 NumPy），介面同 `custom_cnn_classifier.classify()`，有 `weights_exist()`
- **B3 ✓** `app.py` 雙主投票：
  - 選單 → `["雙主投票 (CLIP + EfficientNet-B0)", "CLIP ViT-L/14", "EfficientNet-B0"]`（雙主預設）
  - 旗標 `_USE_CLIP` / `_USE_EFFNET`（子字串判斷，雙主選項兩者皆中）
  - 投票：兩者皆有→比 `top_class_zh` 算 agreement，`primary = max(confidence)`；單模型→直接當 primary；兩者皆 None→`st.error`+stop
  - need_review 條件不變：conf<0.50 或 top2_gap<0.15 或 agreement==0
  - session_state 改存 `effnet_result`；結果顯示區雙欄條件改 `"雙主" in model_mode`，second_label="EfficientNet-B0"；agreement badge 需 clip+effnet 都有才顯示
  - DB：`resnet_model_version` ← `EFFNET_MODEL_VERSION`（versions.py 新常數 `efficientnet-b0-medic-5class-v2`）、`resnet_disaster_type/confidence` ← effnet 結果（欄位名沿用，已加註解）
- **B4 ✓** 清死碼：app.py 移除 ResNet/CNN 推論與 import；`event_matcher.py` 刪 TIME_WINDOWS/DISASTER_GROUPS 的 `other` 組與 `_TYPE_ZH` 的 Other/Non Damage 兩行（fallback 安全：`TIME_WINDOWS.get(g, 6.0)`、`_TYPE_ZH.get(t, t)`）；`scoring.py` 刪 `_GEO_RULES["Non Damage"]` 並**補上缺漏的 `"Flood"`**（沿用 Water Disaster 數值）；`pages/6_MLOps.py` 標籤改「第二主模型版本」
- **B5（程式面）✓** 煙霧測試全過：py_compile、EfficientNet 權重載入無 size mismatch、5 類輸出、dict 介面正確、聚合 fallback 不炸
- **熱修 ✓** 實測踩到 `rag/generator.py:96` KeyError（fallback 預設鍵指向已刪的「其他或無明顯災害」，即計畫 A3 ⚠ 漏項）→ `prompts.py` 新增 `GENERIC_FALLBACK_ADVICE` 通用建議，generator 改 `.get(zh, GENERIC_FALLBACK_ADVICE)`，已驗證 5 類 + 未知類型都安全

## 待辦（剩餘）
- **B5（人工）**：`streamlit run app.py` 登入後實圖 e2e — 各類災害圖 + 一張非災害圖，確認雙主投票 UI、need_review badge、DB 寫入（resnet_* 欄位有 effnet 值）、RAG 建議
- **B7（可選）**：DB 既有舊類別資料（「其他或無明顯災害」/ 舊 ResNet 命名）保留或清理 — 目前選保留（別名仍可分組顯示）
- commit 本批變更

## 技術參考
- 改動檔案：`app.py`、`models/efficientnet_classifier.py`（新）、`utils/versions.py`、`aggregation/event_matcher.py`、`aggregation/scoring.py`、`pages/6_MLOps.py`
- 舊 `custom_cnn_classifier.py` / `resnet_baseline.py` 檔案保留未刪（已無人引用）
- venv：`venv\Scripts\python.exe`（系統 python 無 torch）
