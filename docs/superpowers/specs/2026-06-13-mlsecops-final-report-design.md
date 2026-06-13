# CrisisLens MLSecOps 期末報告 — 設計 (Spec)

- 日期：2026-06-13
- 類型：文件交付物（非程式)
- 狀態：待使用者審查

## 目標

為 **MLSecOps 課程**產出一份完善的期末報告(單一 `REPORT.md`),把 CrisisLens 系統包裝成課程要求的「MLSecOps 證據包」,作為評分依據,並供後續構思簡報。

## 讀者與用途

- 讀者：授課教授 / 助教。
- 用途：展示學習成果、方法正確性、完整 ML 生命週期治理、資安與安全控制。
- 評分對照(課程 deck Slide 44）：技術建置 40% / 風險治理 30% / 紅隊驗證 20%。

## 格式決定

- **單一完整文件** `REPORT.md`(不拆獨立 card 檔)。
- **中文為主、中度深**：關鍵術語保留英文;包含關鍵程式碼片段、指標表格、`mermaid` 架構圖。
- 對應課程交付包清單：AI Use Case Canvas · Data Card · Model Card · Prompt Card · Threat Model · Test Report · Compliance Mapping。

## 課程框架對應(來源:三份教材)

- **Data Card 8 段模板**:1 Dataset identity、2 Provenance & licensing、3 Schema & labels、4 Protected attributes、5 Privacy controls、6 Quality & bias、7 Splits & lineage、8 Security controls。
- **Model Card 9 段模板**:Model identity、Intended use、Training data、Performance、Fairness & XAI、Security testing、Limitations & residual risk、Deployment & monitoring、Approval gate。
- **TEVV 六項可信度測試**:Performance、Fairness、Explainability、Robustness、Privacy、Security。
- **七層防禦**:Governance、Data、Model、Application、RAG、Agent、Supply Chain(每層:控制目標 + 稽核產出物)。
- **deployment gate**:deploy / improve / block,需效能+公平性+解釋+資安+監控擁有者皆備齊。
- **標準對應**:NIST AI RMF(Govern/Map/Measure/Manage)、ISO/IEC 42001+27001、ETSI EN 304 223、OWASP LLM Top 10 (2025)、MITRE ATLAS、EU AI Act。
- CrisisLens 對應課程 Workshop 2(隱私保護視覺安全偵測)+ Workshop 3(企業 RAG 助理)的混合。

## 報告大綱(9 章)

1. **系統概述 / AI Use Case Canvas** — CrisisLens 是什麼、使用情境、ML 生命週期(Plan→Data→Train→Validate→Deploy→Monitor→Retire)、風險分級、人類監督(admin 審核)、整體架構圖(mermaid)。
2. **Data Card** — MEDIC 5 類災害資料集,套用 8 段模板。重點:來源/授權、schema 與 5 類標籤、類別分布、清理(dHash 去重、測試集洩漏排除)、train/dev/test splits、資料面 security controls(來源驗證、poisoning 風險)。
3. **Model Card** — 雙主投票架構,套用 9 段模板。涵蓋 CLIP zero-shot(ViT-L/14 多 prompt)、CLIP linear-probe(舊 6 類切片成 5 類,temperature 0.38)、EfficientNet-B0(微調,test macro-F1 0.8375);版本號(`utils/versions.py`)、限制、retraining 觸發、approval gate。
4. **Prompt Card** — CLIP 多描述分類 prompts(含 Gemini 生成的 `prompts_generated.json`)+ Gemini RAG 應變建議 prompts;版本控管(`CLIP_PROMPT_VERSION`、`RAG_PROMPT_VERSION`)、prompt injection 風險面。
5. **可信度測試 (TEVV)** — Performance(雙模型指標)、Fairness(改為逐類/逐區 **slice 公平性**與誤報分析,非人口屬性,並說明此調整理由)、Explainability(CLIP 相似度可解釋性、Top-3、信心條;XAI 缺口與未來 SHAP/Grad-CAM)、Robustness(對抗/低光/OOD 思考)、Privacy(影像 PII、地理位置 H3 模糊化)。
6. **威脅模型與資安 (Threat Model)** — 七層防禦逐層對應 CrisisLens;攻擊面:data poisoning、prompt injection(RAG/Gemini)、對抗樣本影像、model extraction、供應鏈(`torch.load weights_only=True` 修補作為實例)、ShieldGemma 輸入/輸出安全;對應 MITRE ATLAS 與 OWASP LLM Top 10 條目。
7. **MLOps 監控與部署 Gate (Test Report)** — 監控:推論延遲、信心 drift、retraining 觸發條件;`model_runs` 版本欄位記錄;`need_review` 雙主投票邏輯與閾值;rollback;pytest 測試結果(8 passed)作為自動化驗證證據。
8. **合規對應 (Compliance Mapping)** — 表格:每個 CrisisLens 控制 → NIST AI RMF / ISO 42001 / ISO 27001 / ETSI EN 304 223 / OWASP LLM Top 10 / MITRE ATLAS 對應。
9. **殘餘風險與反思** — 已知限制(linear-probe temperature 為 6 類校準、無新 5 類驗證、need_review 信心壓低)、未來工作、學習反思。

## 三大分類(回應使用者組織問題)

- **資料**:§2 Data Card。
- **模型**:§3 Model Card(+ §4 Prompt Card 屬模型輸入側)。
- **資安**:§6 集中(威脅模型 + 安全控制 + 標準對應之資安部分)。
- 可信度(§5)、治理/監控/合規(§7–8)、反思(§9)各自獨立。

## 內容來源(供寫作時取材)

- 程式與設定:`models/clip_classifier.py`、`models/efficientnet_classifier.py`、`utils/versions.py`、`utils/config.py`、`app.py`、`safety/shieldgemma_guard.py`、`pages/6_MLOps.py`、`db/schema.sql`、`rag/`。
- 既有文件:`docs/eda_5class_phase1_analysis.md`、`docs/upgrade_to_5class_plan.md`、本專案 specs/plans、git log。
- 課程框架:三份教材(Workshop1 notebook、Fairness/XAI/Cards add-on、AI Security Teaching Deck)— 僅作為框架/模板來源,不納入 repo。
- 已知數據:EfficientNet test macro-F1 0.8375;CLIP ViT-L/14;linear-probe temperature 0.3814;5 類(地震/淹水/火災/颱風/土石流);pytest 8 passed。

## 不做 (YAGNI)

- 不拆成多個獨立 card 檔(維持單一報告)。
- 不重新訓練模型或補做 SHAP/對抗實驗(報告中列為未來工作;若時間允許再另議)。
- 不把課程教材檔複製進 repo。
- 不撰寫簡報(後續另行依此報告構思)。
