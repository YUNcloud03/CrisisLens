# CrisisLens 🔍

> **災情圖文分類與應變建議系統 v2.0**  
> 上傳一張災情照片，AI 自動辨識災害類型、產生防災建議，並將回報聚合為事件、在 H3 地圖上展示災情熱度。
>
> **CLIP ViT-L/14（zero-shot）+ ResNet50 Linear Probe（fine-tuned on MEDIC）+ DisasterCNN_v1（自訓 CNN）+ RAG（FAISS + Gemini）+ H3 地理聚合**

---

## 目錄

- [專案特色](#專案特色)
- [快速開始（本機 SQLite 模式）](#快速開始本機-sqlite-模式)
- [模型權重下載](#模型權重下載)
- [種子資料](#種子資料)
- [環境變數](#環境變數)
- [使用流程](#使用流程)
- [Docker 本機測試](#docker-本機測試)
- [Azure 部署](#azure-部署)
- [專案結構](#專案結構)
- [MLOps 版本管理](#mlops-版本管理)
- [AI Safety 聲明](#ai-safety-聲明)
- [常見問題](#常見問題)

---

## 專案特色

| 功能模組 | 說明 |
|---|---|
| **CLIP ViT-L/14 零樣本分類** | 多描述投票（每類 4–7 prompts）+ 100× temperature scaling → 6 類高信心分類 |
| **ResNet50 Linear Probe** | ImageNet ResNet50 backbone + Linear head，fine-tuned on QCRI/MEDIC 5 classes（90MB weights） |
| **DisasterCNN_v1 輔助驗證** | 自訓 4-block CNN（QCRI/MEDIC，val_acc=68.57%）交叉確認，不一致時觸發人工審查 |
| **model_agreement + need_review** | 雙模型標籤一致性比對；信心度 < 50% 或 Top-2 gap < 15% 或模型不一致 → 待審核旗標 |
| **RAG 防災建議** | FAISS 檢索 6 份防災 SOP → Gemini 2.0 Flash 生成；無 API key 自動 fallback |
| **事件自動聚合 v4** | 依災害類型分組 + 地點距離 + 各類型時間窗口（6–48 hr）聚合 |
| **H3 多層次熱區圖** | 縣市（res 5）→ 鄉鎮（res 7）→ 街區（res 9）動態縮放，支援過濾 resolved 事件 |
| **三維 Priority Score** | Severity × 0.50 + Vulnerability × 0.30 + Credibility × 0.20 |
| **事件狀態管理** | pending_review / active / resolved / archived + Admin Action Log |
| **MLOps 版號追蹤** | 每次推論寫入 `model_runs`，支援 retraining 資料追溯 |
| **PostgreSQL / SQLite 雙模式** | 本機用 SQLite，Azure 部署設定 `DATABASE_URL` 自動切換 |
| **Azure Blob Storage** | 設定 `AZURE_STORAGE_CONNECTION_STRING` 啟用，未設定則存本機 |

---

## 快速開始（本機 SQLite 模式）

### 前置需求

- **Python 3.10 / 3.11**（建議 3.11）
- **Git**
- **磁碟空間**：約 2GB（CLIP ViT-L/14 快取 ~900MB + 套件）

### 安裝步驟

```bash
# 1. 取得專案
git clone <your-repo-url>
cd crisislens

# 2. 建立虛擬環境
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. 安裝套件（PyTorch CPU-only，大幅縮小安裝量）
pip install torch==2.2.0+cpu torchvision==0.17.0+cpu \
  --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env，至少填入 GEMINI_API_KEY（選填，未填使用內建指引）

# 5. 建立 FAISS 向量索引
python rag/build_index.py

# 6. （選填）匯入測試種子資料
python seed.py --reset

# 7. 啟動
streamlit run app.py
```

預設網址：<http://localhost:8501>  
管理員帳號請透過部署環境變數或初始化腳本建立；不要在前端或公開文件顯示預設密碼。

---

## 模型權重下載

### CLIP ViT-L/14

首次推論時**自動下載**，無需手動操作。  
快取路徑：`~/.cache/clip/ViT-L-14.pt`（約 900MB）

### ResNet50 Linear Probe

需手動放置到 `models/resnet50_linear.pth`（約 90MB）。

```bash
# 從組員共用雲端下載後放到 models/
ls models/resnet50_linear.pth   # 確認存在（90MB）
```

> 若缺少此檔案，系統仍可正常運作，ResNet50 選項在 Sidebar 顯示但推論結果不可用。  
> 訓練指令：`python models/train_resnet.py`（需先準備 QCRI/MEDIC 資料集）

### DisasterCNN_v1

需手動放置到 `models/custom_cnn.pth`（約 1.5MB）。

```bash
# 訓練（使用 QCRI/MEDIC 資料集）後取得 custom_cnn.pth
# 或從組員共用雲端下載後放到 models/
ls models/custom_cnn.pth   # 確認存在
```

> 若缺少此檔案，系統仍可正常運作，僅 CLIP 模式有效，CNN 輔助驗證功能停用。
> 系統啟動時側邊欄會顯示 CNN 狀態。

---

## 種子資料

```bash
# 寫入 10 筆固定測試回報（重複執行安全）
python seed.py

# 清空 reports / events / grid_summary 後重新寫入
python seed.py --reset
```

> 不影響 `users`、`model_runs`、`admin_corrections` 等表。

---

## 環境變數

複製 `.env.example` 為 `.env` 後填入：

| 變數 | 必填 | 說明 |
|------|------|------|
| `GEMINI_API_KEY` | 否 | 未填時 RAG 使用內建指引（功能仍可用）；亦用於 ShieldGemma Layer 2 |
| `USE_LOCAL_SHIELDGEMMA` | 否 | 設為 `true` 啟用本地 ShieldGemma 3B（需約 2GB VRAM）|
| `DATABASE_URL` | 否（本機）| PostgreSQL 連線字串，未填使用 SQLite |
| `AZURE_STORAGE_CONNECTION_STRING` | 否 | 未填時圖片存 `uploads/reports/` |
| `AZURE_STORAGE_CONTAINER` | 否 | 預設 `crisislens-uploads` |

---

## 使用流程

### 民眾端

1. 登入或註冊帳號
2. 上傳災情照片（JPG / PNG / WEBP）
3. 選擇定位方式（瀏覽器 GPS / 手動座標 / 行政區）
4. 點擊「AI 辨識並產生建議」→ 右側出現辨識結果 + 防災建議
5. 確認後點擊「送出災情回報」

> GPS 失敗或未填座標時，仍可用行政區送出回報，不影響事件聚合統計。

### 管理端

1. Admin 帳號登入後自動跳轉到 Event Dashboard
2. 依災害類型、縣市、優先級、狀態篩選事件
3. 點選事件卡片進入詳細頁，可查看所有回報照片與地圖
4. 在 H3 熱圖頁觀察全台災情分布
5. 在權限審核頁批准 / 拒絕使用者的 admin 申請

---

## Docker 本機測試

```bash
# 建置（包含 CPU-only PyTorch）
docker build -t crisislens:local .

# 執行（本機 SQLite + 圖片存容器內）
docker run -p 8501:8501 \
  -e GEMINI_API_KEY=你的key \
  crisislens:local

# 執行（掛載本機 DB + uploads）
docker run -p 8501:8501 \
  -v "$(pwd)/crisislens.db:/app/crisislens.db" \
  -v "$(pwd)/uploads:/app/uploads" \
  -e GEMINI_API_KEY=你的key \
  crisislens:local
```

---

## Azure 部署

詳細步驟請參閱 [docs/deployment_azure.md](docs/deployment_azure.md)。

**一句話摘要**：
```bash
# 建置並推送映像
docker build -t crisislensacr.azurecr.io/crisislens:latest .
docker push crisislensacr.azurecr.io/crisislens:latest

# 更新 Container App
az containerapp update --name crisislens --resource-group crisislens-rg \
  --image crisislensacr.azurecr.io/crisislens:latest
```

---

## 專案結構

```
crisislens/
├── app.py                      # 主頁：民眾端（災情回報 + AI 辨識）
├── startup.sh                  # Docker / Azure 啟動腳本
├── Dockerfile
├── requirements.txt
├── .env.example
├── seed.py                     # 測試種子資料
│
├── pages/
│   ├── 2_Event_Dashboard.py    # 管理端：事件列表（含 need_review 過濾）
│   ├── 3_Event_Detail.py       # 管理端：事件詳細（含 Admin Corrections）
│   ├── 4_H3_Heatmap.py         # 管理端：H3 熱區地圖
│   ├── 5_Permission_Review.py  # 管理端：使用者權限審核
│   └── 6_MLOps.py              # 管理端：MLOps 監控（版本記錄 / 修正 / 待審核）
│
├── models/
│   ├── clip_classifier.py      # CLIP ViT-L/14 推論（multi-prompt averaging）
│   ├── resnet_baseline.py      # ResNet50 Linear Probe 推論（5-class fine-tuned on MEDIC）
│   ├── resnet50_linear.pth     # ResNet50 weights（90MB，需手動下載）
│   ├── resnet50_linear_classes.json  # 5-class label mapping
│   ├── train_resnet.py         # ResNet50 fine-tuning 訓練腳本
│   ├── custom_cnn_classifier.py # DisasterCNN_v1 推論包裝
│   └── custom_cnn_model.py     # DisasterCNN_v1 架構定義（與訓練筆記本同步）
│
├── rag/
│   ├── build_index.py          # 建立 FAISS 索引
│   ├── retriever.py            # 向量檢索
│   └── generator.py            # Gemini 生成 + fallback
│
├── rag_docs/                   # 6 份防災 SOP 文件（Traditional Chinese）
│
├── aggregation/
│   ├── event_matcher.py        # 事件聚合（v4：類型+地點+時間窗口）
│   ├── h3_utils.py             # H3 網格工具
│   ├── scoring.py              # Report / Event / Priority 評分
│   └── distance.py             # Haversine 距離
│
├── db/
│   ├── schema.sql              # SQLite schema（含 admin_action_logs, error_logs）
│   ├── schema_pg.sql           # PostgreSQL schema
│   ├── database.py             # 雙模式連線（SQLite / PostgreSQL）
│   └── queries.py              # CRUD 查詢（含 RETURNING）
│
├── utils/
│   ├── config.py               # 類別、Prompt Set
│   ├── versions.py             # MLOps 版本常數
│   ├── storage.py              # 圖片儲存（Azure Blob / 本機）
│   ├── geocoding.py            # Nominatim 反向地理編碼（LRU cache）
│   ├── logger.py               # 錯誤日誌（SQLite handler）
│   ├── auth.py                 # 登入 / 登出 / 權限
│   ├── ui_theme.py             # 深色主題 CSS + 共用元件
│   └── image_utils.py
│
└── docs/
    ├── data_card.md            # MLSecOps Workshop 1 資料卡
    ├── model_card.md           # MLSecOps Workshop 1 模型卡
    ├── system_card.md          # 系統總覽（流程、聚合規則、安全）
    └── deployment_azure.md     # Azure 部署完整指南
```

---

## MLOps 版本管理

版號統一在 [`utils/versions.py`](utils/versions.py)：

```python
CLIP_MODEL_VERSION       = "clip-vitl14-v1"
CLIP_PROMPT_VERSION      = "multi-prompt-avg-v1"
RESNET_MODEL_VERSION     = "resnet50-linear-probe-medic-5class-v1"
CNN_MODEL_VERSION        = "custom-cnn-medic-6class-v1"
RAG_INDEX_VERSION        = "faiss-multilingual-minilm-v1"
RAG_PROMPT_VERSION       = "gemini-flash-rag-v1"
AGGREGATION_RULE_VERSION = "disaster-group-distance-timewindow-v4"
PRIORITY_RULE_VERSION    = "svcp-weighted-v2"
```

每次更新對應元件時手動遞增版號，所有版號都會寫入 `model_runs` 表。

**Retraining 觸發建議**：
- `need_review` 率 > 30%（連續 100 筆）
- Model agreement 率 < 60%（7 天窗口）

---

## AI Safety 聲明

> ⚠️ **本系統的分類與建議僅供災害資訊整理與初步參考，不代表任何官方災害判定。**

- 若有人員受困、受傷或有立即危險，請**優先撥打 119、110**
- CLIP 信心度 < 0.50 或 Top-2 gap < 0.15 的回報標記 `need_review = 1`
- 模型不一致時（CLIP ≠ CNN）標記 `model_agreement = 0`，一律送人工審查
- UI 所有推論結果均附加 Safety disclaimer，不可移除

### ShieldGemma 3-層安全防護

每次使用者點擊「AI 辨識並產生建議」時，系統**自動執行三層安全檢查**：

| 層級 | 觸發條件 | 方法 | 說明 |
|------|----------|------|------|
| Layer 1 — Keyword 規則 | 永遠執行 | `keyword` | 比對禁用關鍵字清單，零延遲 |
| Layer 2 — Gemini API | `GEMINI_API_KEY` 設定時 | `gemini` / `gemini_vision` | 語意分析文字描述 + Vision API 檢查圖片 |
| Layer 3 — ShieldGemma 本地 | `USE_LOCAL_SHIELDGEMMA=true` 時 | `shieldgemma` | google/shieldgemma-2b 本地推論（約 2GB） |

**三個檢查點**：
1. **文字輸入** — 使用者描述文字（`check_user_input`）
2. **圖片內容** — 上傳照片（`check_image_safety`，需 Gemini Vision）
3. **建議輸出** — RAG 生成的防災建議（`check_rag_output`）

**結果 label**：
- `safe` — 通過，不顯示警告
- `review` — 觸發敏感詞，標記為需人工審查
- `sanitize` — 輸出含危險語句，自動替換
- `block` — 封鎖，中止流程並顯示錯誤

每次分析完成後，右側結果面板的「🛡️ ShieldGemma 3-層安全檢查結果」卡片會顯示三個檢查點的 label 與使用的方法，供使用者確認系統確實執行了安全防護。

啟用本地 ShieldGemma：
```bash
# .env
USE_LOCAL_SHIELDGEMMA=true
# 首次載入約 2GB，需 CUDA 或 MPS；CPU 推論極慢，不建議生產使用
```

---

## 常見問題

**Q1：CLIP 首次推論很慢？**  
A：ViT-L/14 首次需下載約 900MB，快取後之後推論正常（約 2–5 秒 / 張，CPU）。

**Q2：FAISS index 錯誤？**  
A：執行 `python rag/build_index.py`。側邊欄顯示 ✅ 表示就緒。

**Q3：CNN 輔助驗證沒出現？**  
A：確認 `models/custom_cnn.pth` 存在，且 `CNN_AUX_ENABLED=True`（預設）。

**Q4：H3 地圖無法顯示？**  
A：確認已安裝 `h3>=3.7.7`。若缺套件，頁面會顯示安裝提示。

**Q5：如何切換 PostgreSQL？**  
A：在 `.env` 填入 `DATABASE_URL=postgresql://...`，重啟 Streamlit。Schema 初始化是冪等的，會自動建表。

**Q6：送出回報後沒看到事件？**  
A：可能 GPS 和行政區都未填，`grid_id = NULL`，仍有 report 但 grid_summary 未建立。建議至少填入縣市。

---

**v2.0** · CLIP ViT-L/14 + DisasterCNN_v1 + RAG · 2026
