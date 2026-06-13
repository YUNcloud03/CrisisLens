# CrisisLens MLSecOps 期末報告 撰寫計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 產出單一 `docs/MLSecOps_Final_Report.md`(中文為主、中度深),把 CrisisLens 整合成 MLSecOps 課程要求的證據包(Use Case Canvas · Data Card · Model Card · Prompt Card · Threat Model · Test Report · Compliance Mapping)。

**Architecture:** 報告為單一 Markdown,分 9 章逐章撰寫(每章一個 task:先讀指定來源檔取真實事實 → 寫該章 → 核對數字與來源一致 → commit)。大量整合既有 `docs/*_card.md` 與 `docs/security_paper.docx`,並補齊課程要求但 repo 尚缺的部分(TEVV、正式 Threat Model、Compliance Mapping)。

**Tech Stack:** Markdown、mermaid 圖、表格。撰寫紀律取代 TDD:每章「事實核對步驟」確保不編造數據(所有關鍵數字須對得上來源 `檔案:行號`)。

**寫作規範(所有章節共通):**
- 中文敘述,關鍵術語 / card 欄位名 / 標準名保留英文。
- 每個關鍵數字後標來源,如「test macro-F1 0.8375(`docs/phase_b_state.md`)」。
- 禁止編造:查無的事實寫「目前未實作 / 列為未來工作」,不得杜撰。
- 程式片段精簡(≤15 行)、只放關鍵段落。
- 圖用 mermaid。

---

## File Structure

- Create: `docs/MLSecOps_Final_Report.md` — 唯一交付物,9 章逐步 append。
- 來源(只讀,不改):`docs/data_card.md`、`docs/model_card.md`、`docs/system_card.md`、`docs/security_paper.docx`、`docs/eda_5class_phase1_analysis.md`、`docs/phase_b_state.md`、`docs/upgrade_to_5class_plan.md`、`models/classes_5class_v2.json`、`utils/config.py`、`utils/versions.py`、`models/clip_classifier.py`、`models/efficientnet_classifier.py`、`safety/shieldgemma_guard.py`、`pages/6_MLOps.py`、`db/schema.sql`、`rag/prompts.py`、`rag/generator.py`、`utils/auth.py`、`aggregation/h3_utils.py`、`app.py`。

---

## Task 1: 報告骨架 + 第 1 章 系統概述 / AI Use Case Canvas

**Files:** Create `docs/MLSecOps_Final_Report.md`
**來源:** `docs/system_card.md`、`app.py`(流程)、本 session 已知架構。

- [ ] **Step 1: 建立檔頭與目錄**
  寫入:標題「CrisisLens — MLSecOps 期末報告」、課程/作者/日期(2026-06-13)、一段 100 字內摘要(災情圖文分類 + RAG 應變建議 + 安全治理)、以及對應課程交付包的對照說明(本報告 = AI Use Case Canvas + Data/Model/Prompt Card + Threat Model + Test Report + Compliance Mapping)。接著放 9 章目錄(錨點連結)。

- [ ] **Step 2: 寫第 1 章內容**
  必含:
  - **AI Use Case Canvas**:問題、使用者(民眾回報端 / admin 審核端)、決策情境、人類監督點(admin 審核 `need_review` 案件)、風險分級(影響公共安全 → 中高風險)。
  - **ML 生命週期圖**(mermaid flowchart):Plan → Data → Train → Validate → Deploy → Monitor → Retire,每階段標一句控制重點。
  - **系統架構圖**(mermaid):上傳影像 → ShieldGemma 影像/輸入安全 → 雙主投票(CLIP linear-probe + EfficientNet-B0)→ need_review 判斷 → RAG(Gemini)應變建議 → 輸出安全 → 寫入 DB/事件聚合 → MLOps 監控。
  - 一句話點出本系統對應課程 Workshop 2(視覺安全偵測)+ Workshop 3(RAG 助理)。

- [ ] **Step 3: 事實核對**
  確認架構圖的元件名稱與 `app.py` 實際流程一致(ShieldGemma 三檢查點、雙主投票、RAG)。確認無杜撰元件。

- [ ] **Step 4: Commit**
  `git add docs/MLSecOps_Final_Report.md && git commit -m "docs(report): 骨架 + 第1章 系統概述/Use Case Canvas"`

---

## Task 2: 第 2 章 Data Card(8 段模板)

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 2 章)
**來源:** `docs/data_card.md`、`docs/eda_5class_phase1_analysis.md`、`models/classes_5class_v2.json`、`utils/config.py`、`models/efficientnet_classifier.py:72-76`。

- [ ] **Step 1: 取材**
  讀上述來源,擷取:MEDIC = QCRI、ACL 2021、research/academic 非商業授權;5 類 EN/ZH 與索引 0–4;train 類別分布(Earthquake 12,296/53.3%、Hurricane→Typhoon 4,517/19.6%、Flood 3,401/14.7%、Fire 1,796/7.8%、Landslide 1,065/4.6%,合計 23,075;val 2,672/test 5,649;不平衡比 11.55x);清理(dHash 去重 3,616、test 洩漏排除 60、img_size 256);前處理(Resize288→CenterCrop256、ImageNet normalize)。

- [ ] **Step 2: 依 8 段模板寫第 2 章**
  逐段填:(1) Dataset identity (2) Provenance & licensing (3) Schema & labels(含 5 類表) (4) Protected attributes(說明本資料集**無人口屬性 protected attribute**,改以「災害類別 / 地區 / 時段」作為 slice 維度) (5) Privacy controls(影像可能含可識別場景/車牌、回報含地理位置 → H3 res9 模糊化) (6) Quality & bias(類別不平衡 11.55x、去重/洩漏數字、Typhoon 改名自 Hurricane) (7) Splits & lineage(train/val/test 數字、清理 pipeline) (8) Security controls(資料來源驗證、poisoning 風險、使用者上傳為不受信任輸入 → 走 ShieldGemma)。
  放一張類別分布表(類別 / 張數 / 占比)。

- [ ] **Step 3: 事實核對**
  每個數字對回來源行號;確認 8 段全部有內容(無「TBD」)。

- [ ] **Step 4: Commit**
  `git commit -am "docs(report): 第2章 Data Card"`

---

## Task 3: 第 3 章 Model Card(9 段模板)

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 3 章)
**來源:** `docs/model_card.md`、`models/efficientnet_classifier.py`、`models/clip_classifier.py`、`utils/versions.py`、`docs/phase_b_state.md`、`docs/superpowers/specs/2026-06-13-clip-linear-probe-revival-design.md`。

- [ ] **Step 1: 取材**
  擷取:三條推論路徑(CLIP zero-shot ViT-L/14 多 prompt;CLIP linear-probe = 舊 6 類切片成 5 類、temperature 0.3814;EfficientNet-B0 微調 5 類);legacy(Custom CNN macro-F1 0.7012 已淘汰、ResNet50 baseline);版本號(全部 `utils/versions.py` 常數);EfficientNet 指標(test macro-F1 0.8375;per-class recall:地震0.862/淹水0.877/火災0.894/颱風0.783/土石流0.843;Landslide precision 0.694);EfficientNet 分類頭(`efficientnet_b0(weights=None)` + `Linear(in_features,5)`);雙主投票機制。

- [ ] **Step 2: 依 9 段模板寫第 3 章**
  (1) Model identity(三模型 + 版本 + 權重檔路徑) (2) Intended use(災情輔助分類、非自動決策、admin 保留最終裁量) (3) Training data(MEDIC 5 類,引第 2 章) (4) Performance(指標表:macro-F1、per-class recall/precision) (5) Fairness & XAI(逐類 recall 落差即 slice 公平性,Typhoon 0.783 最弱;XAI 現況 = Top-3+信心,SHAP/Grad-CAM 列未來) (6) Security testing(對抗/poisoning 測試現況與缺口) (7) Limitations & residual risk(linear-probe temperature 為 6 類校準、無新 5 類驗證、Landslide precision 偏低) (8) Deployment & monitoring(need_review、retraining 觸發、rollback,詳見第 7 章) (9) Approval gate(deploy/improve/block 條件)。
  放雙主投票機制圖(mermaid)。

- [ ] **Step 3: 事實核對**
  指標數字對回 `docs/phase_b_state.md`;版本字串對回 `utils/versions.py`;9 段全部有內容。

- [ ] **Step 4: Commit**
  `git commit -am "docs(report): 第3章 Model Card"`

---

## Task 4: 第 4 章 Prompt Card

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 4 章)
**來源:** `utils/config.py:36-97`(PROMPT_SETS / MULTI_PROMPT_SETS)、`models/clip_classifier.py:88-102`、`rag/prompts.py`、`rag/generator.py:21`。

- [ ] **Step 1: 取材**
  擷取:CLIP 分類 prompt(PROMPT_SETS 三組各 5 條、MULTI_PROMPT_SETS 每類 3–7 條;`prompts_generated.json` 設計支援但目前未生成 → 回退內建);RAG = `RAG_SYSTEM_PROMPT`(台灣災害應變專家、3–5 條「・」建議)+ `RAG_USER_TEMPLATE`(context/type/confidence/location)+ `FALLBACK_ADVICE`;Gemini 模型 `gemini-2.5-flash`;版本 `CLIP_PROMPT_VERSION` / `RAG_PROMPT_VERSION`。

- [ ] **Step 2: 寫第 4 章**
  必含:CLIP 分類 prompt 設計與多描述平均策略(各放 1–2 條範例,不全貼);RAG 應變建議 prompt 結構與 fallback 機制;prompt 版本控管;**prompt injection 風險面**(使用者描述會進 RAG context → 由 ShieldGemma input guard 與 RAG fallback 緩解,詳見第 6 章)。

- [ ] **Step 3: 事實核對**
  prompt 條數、Gemini 模型名、版本字串對回來源;確認標明 `prompts_generated.json` 現況為「未生成」。

- [ ] **Step 4: Commit**
  `git commit -am "docs(report): 第4章 Prompt Card"`

---

## Task 5: 第 5 章 可信度測試 (TEVV)

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 5 章)
**來源:** `docs/phase_b_state.md`、`docs/model_card.md`、`safety/shieldgemma_guard.py`、`aggregation/h3_utils.py`、`models/clip_classifier.py`。

- [ ] **Step 1: 寫第 5 章(對應 TEVV 六項)**
  依課程 TEVV 六面向逐項:
  - **Performance**:macro-F1 0.8375、雙模型互補。
  - **Fairness(slice)**:明確說明 CrisisLens 無人口 protected attribute,改以「逐類別 / 地區 / 時段」slice 評估;逐類 recall 落差(颱風 0.783 最弱、Landslide precision 0.694)即 slice 不均,提出對策(增樣/重採樣)。
  - **Explainability**:CLIP 文字-影像相似度本身可解釋、Top-3 + 信心條、雙主投票一致性;缺口 = 無 SHAP/Grad-CAM → 列未來工作。
  - **Robustness**:對抗樣本 / 低光 / OOD / 影像壓縮的風險討論與現況(尚未做正式 robustness test → 未來工作)。
  - **Privacy**:影像 PII(車牌/人臉)、地理位置 H3 res9(~174m)模糊化、ShieldGemma 對身分證/手機/精確地址的 review 攔截。
  放一張 TEVV 六項「現況 / 證據 / 缺口」對照表。

- [ ] **Step 2: 事實核對**
  H3 res9 邊長、ShieldGemma review 類別、per-class 數字對回來源;凡未實作者明確標示。

- [ ] **Step 3: Commit**
  `git commit -am "docs(report): 第5章 可信度測試 TEVV"`

---

## Task 6: 第 6 章 威脅模型與資安 (Threat Model)

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 6 章)
**來源:** `docs/security_paper.docx`(需用 docx 技能或 python 解析提取文字)、`safety/shieldgemma_guard.py`、`utils/auth.py`、`utils/storage.py`、`models/*_classifier.py`(weights_only)、`models/resnet_baseline.py`(缺口)。

- [ ] **Step 1: 提取既有 security paper**
  用 anthropic-skills:docx 技能(或 venv python-docx)讀 `docs/security_paper.docx`,摘要其威脅模型與防禦,納入本章(避免重複造輪)。若提取失敗則記錄並改以程式碼實證為主。

- [ ] **Step 2: 寫第 6 章**
  必含:
  - **七層防禦對照表**(Governance/Data/Model/Application/RAG/Agent/Supply Chain)→ 每層填 CrisisLens 對應控制 + 稽核產出物。
  - **攻擊面與防禦**:data poisoning(使用者上傳不受信任)、prompt injection(RAG context → ShieldGemma input guard,P>0.7 block / >0.4 review)、對抗樣本影像、model extraction / API 濫用、**supply chain**(`torch.load(weights_only=True)` 已套用於 CLIP/EfficientNet/CustomCNN;**實證缺口:`models/resnet_baseline.py` 未加 weights_only** → 列為已知殘餘風險與修補建議)、輸出安全(ShieldGemma sanitize 不安全建議)。
  - **ShieldGemma 三檢查點**:input / image / output guard,後端優先鏈(keyword→本機 ShieldGemma→Gemini),門檻。
  - **認證**:PBKDF2-SHA256 120,000 iters + salt;admin 權限。
  - **MITRE ATLAS / OWASP LLM Top 10 對應**:列出 CrisisLens 相關條目(prompt injection、sensitive info disclosure、model poisoning 等)與緩解。

- [ ] **Step 3: 事實核對**
  ShieldGemma 門檻、PBKDF2 iters、weights_only 各檔狀態(含 resnet 缺口)對回來源行號;security_paper 摘要忠實不誇大。

- [ ] **Step 4: Commit**
  `git commit -am "docs(report): 第6章 威脅模型與資安"`

---

## Task 7: 第 7 章 MLOps 監控與部署 Gate (Test Report)

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 7 章)
**來源:** `pages/6_MLOps.py`、`db/schema.sql:168-185`、`utils/versions.py:23-26`、`app.py`(投票段)、`docs/system_card.md:246-249`、`tools/seed_mlops_demo.py`、`tests/test_clip_linear_probe.py`。

- [ ] **Step 1: 寫第 7 章**
  必含:
  - **監控指標**:推論記錄數、人工修正數、待審核率、推論延遲、信心 drift、版本摘要(`model_runs` 表記錄各版本 + `inference_latency_ms`)。
  - **need_review 邏輯**:`confidence<0.50 OR top2_gap<0.15 OR model_agreement==0`(放程式片段);並註明 linear-probe temperature 放大信心 → need_review 主靠模型不一致。
  - **Deployment Gate(deploy/improve/block)**:把課程 gate 概念對應到 CrisisLens 的上線判準(效能/一致性/安全控制/監控擁有者)。
  - **Retraining 觸發**:need_review 率 >30%(連續 100 筆)或 model agreement <60%(持續 7 天)。
  - **Rollback**:版本化權重 + 可切回 zero-shot CLIP。
  - **自動化測試證據**:`tests/test_clip_linear_probe.py` 8 passed(切片/載入/路由/fallback)。
  - 一張監控指標流程或儀表板示意(mermaid 或表)。

- [ ] **Step 2: 事實核對**
  閾值、retraining 觸發數字、model_runs 欄位、pytest 數量對回來源。

- [ ] **Step 3: Commit**
  `git commit -am "docs(report): 第7章 MLOps 監控與部署 Gate"`

---

## Task 8: 第 8 章 合規對應 (Compliance Mapping)

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 8 章)
**來源:** 課程 deck 標準清單 + 前 7 章已述控制。

- [ ] **Step 1: 寫第 8 章**
  製作**主對照表**:左欄為 CrisisLens 控制(資料來源驗證、ShieldGemma、雙主投票 need_review、weights_only、PBKDF2、H3 模糊化、版本化/監控、RAG fallback…),右欄對應到:
  - **NIST AI RMF**(Govern / Map / Measure / Manage 哪一項)
  - **ISO/IEC 42001**(AI 管理系統)/ **ISO/IEC 27001**(資安)
  - **ETSI EN 304 223**(安全設計/開發/部署/維運/退役)
  - **OWASP LLM Top 10 (2025)**(對應條目,如 LLM01 Prompt Injection)
  - **MITRE ATLAS**(對應戰術/技術)
  每列附一句「對應證據在本報告第 X 章」。

- [ ] **Step 2: 事實核對**
  每個對應的控制都能在前面章節找到出處;不杜撰未實作的控制(未做的標「規劃中」)。

- [ ] **Step 3: Commit**
  `git commit -am "docs(report): 第8章 合規對應"`

---

## Task 9: 第 9 章 殘餘風險與反思

**Files:** Modify `docs/MLSecOps_Final_Report.md`(append 第 9 章)
**來源:** 前 8 章 + `docs/phase_b_state.md` + linear-probe spec。

- [ ] **Step 1: 寫第 9 章**
  必含:
  - **已知限制 / 殘餘風險**:linear-probe temperature 為 6 類校準(信心校準近似)、取代 zero-shot 後 need_review 互補性下降、無新 5 類驗證資料、Typhoon recall 0.783 / Landslide precision 0.694、`resnet_baseline.py` weights_only 缺口、`prompts_generated.json` 未生成、無正式 SHAP/對抗測試。
  - **未來工作**:5 類資料重訓 linear-probe head 並重新校準閾值、SHAP/Grad-CAM、正式 robustness/紅隊測試、AI-BOM/簽章、demographic-free fairness 深化。
  - **學習反思**:把 MLSecOps 框架套到真實系統的收穫(從 accuracy-only → risk-aware)。

- [ ] **Step 2: 事實核對**
  所列風險皆有前文依據;無新杜撰數字。

- [ ] **Step 3: Commit**
  `git commit -am "docs(report): 第9章 殘餘風險與反思"`

---

## Task 10: 最終整合與一致性校對

**Files:** Modify `docs/MLSecOps_Final_Report.md`

- [ ] **Step 1: 目錄與錨點**
  依實際章節更新目錄,確認所有錨點連結可跳轉。

- [ ] **Step 2: 結構完整性檢查**
  確認:Data Card 8 段、Model Card 9 段全部到齊;七層防禦表、TEVV 表、合規對應表都有;mermaid 圖語法正確(可用線上或 `mmdc` 心算檢視語法,至少確認 code fence 標 `mermaid`)。

- [ ] **Step 3: 事實一致性與術語校對**
  全文抽查關鍵數字(0.8375、3,616、60、11.55x、temperature 0.3814、need_review 三閾值、PBKDF2 120k、H3 res9、Gemini 2.5-flash)是否前後一致且對得上來源;統一術語(linear-probe / zero-shot / 雙主投票)。修正不一致。

- [ ] **Step 4: Commit**
  `git commit -am "docs(report): 最終整合、目錄與一致性校對"`

---

## 完成定義

- `docs/MLSecOps_Final_Report.md` 單檔含 9 章,涵蓋課程交付包全部項目(Use Case Canvas / Data Card 8 段 / Model Card 9 段 / Prompt Card / Threat Model 含七層防禦 / Test Report / Compliance Mapping)。
- 所有關鍵數字皆可對回 repo 來源,無杜撰;未實作項目明確標示為缺口/未來工作。
- 既有 `docs/*_card.md` 與 `security_paper.docx` 已整合進報告。
- 目錄、表格、mermaid 圖完整,術語與數字前後一致。
