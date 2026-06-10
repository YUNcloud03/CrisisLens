# CrisisLens Engineering TODO

本文件給後續工程師使用，目標是把目前 CrisisLens 從「可展示雛形」整理成「可穩定部署的 demo」。請優先維持既有使用流程，不要一次重寫整個專案。

## Current Status

CrisisLens 目前已有：

- 民眾端：登入、註冊、上傳災害圖片、AI 辨識、RAG 防災建議、災情回報送出。
- 管理端：事件列表、事件詳情、H3 熱區圖、權限審核。
- 權限邏輯：`user / admin` 與 `none / pending / approved / rejected`。
- AI 流程：CLIP、Custom CNN、兩者比較、RAG 建議。
- 聚合邏輯：依災害群組與地點距離聚合，時間條件先不納入。
- UI 主題：黑底白字、共用 sidebar、卡片、badge、表單樣式。

目前主要風險在：

- Streamlit session state 容易殘留，尤其是 AI 結果、GPS、登入狀態。
- SQLite 與本機圖片路徑不適合 Azure 部署。
- GPS 定位在 Streamlit iframe 中不一定穩定。
- H3、FAISS、CNN/CLIP 依賴在部署環境可能會失敗。
- 前端仍有一些版面細節需要收斂。

## Priority 0: Do Not Break These Flows

修改前後都要手動測這些流程：

1. 新使用者註冊後登入。
2. 一般使用者送出管理員權限申請。
3. admin 登入後進入管理端。
4. admin 審核 pending 使用者。
5. 一般使用者上傳圖片並按「AI 辨識並產生建議」。
6. AI 結果與防災建議出現在右側，不要出現在頁面底部。
7. 使用者送出災情回報後，管理端事件列表有資料。
8. H3 熱區頁面在缺少 `h3` 或無 GPS 資料時不 crash，要顯示清楚提示。

## Priority 1: Stabilize Frontend State

### Files

- `app.py`
- `utils/auth.py`
- `utils/ui_theme.py`

### Tasks

- 確認 `citizen_analysis` 只代表目前這次分析結果，不要跨帳號殘留。
- 登出與登入時清除以下 session keys：
  - `citizen_analysis`
  - `report_latitude`
  - `report_longitude`
  - `latitude_input`
  - `longitude_input`
  - `gps_status`
- 切換模型模式時清掉舊分析結果，避免「CLIP 結果」殘留到「兩者比較」。
- 「兩者比較」時，右側應顯示兩張短版 model result cards：
  - CLIP ViT-L/14
  - Custom CNN
- 下方不應再重複渲染 AI 辨識結果。
- 未完成 AI 辨識前，右側不要顯示防災建議。

### Acceptance Criteria

- 第一次按分析後，結果與建議直接出現在右側。
- 重新登入不會看到前一個帳號或前一次分析的殘留建議。
- 切換模型後，右側會回到「尚未進行 AI 辨識」或重新分析狀態。

## Priority 2: Database Migration

目前使用 SQLite：`crisislens.db`。

Azure 部署時建議改為：

- 快速 demo：Supabase PostgreSQL
- Azure-only 架構：Azure Database for PostgreSQL

### Files

- `db/database.py`
- `db/queries.py`
- `db/schema.sql`
- `.env`
- `.env.example`

### Tasks

- 抽象 DB connection，不要讓業務邏輯直接依賴 SQLite。
- 將 `schema.sql` 改成 PostgreSQL 相容語法。
- 調整 SQL placeholder 寫法。
- 保留現有 query function 名稱，避免影響 `app.py` 和 `pages/*`。
- 新增環境變數：
  - `DATABASE_URL`
  - 或 `SUPABASE_DB_URL`
- 不要把 Supabase service key 或 DB password commit 到 repo。

### Suggested Migration Order

1. 先讓 PostgreSQL schema 建立成功。
2. 改 `db/database.py` connection。
3. 改 `db/queries.py` SQL placeholder。
4. 跑登入、註冊、權限審核。
5. 跑災情回報與事件聚合。

## Priority 3: Image Storage

目前圖片存在本機：

- `uploads/reports`

部署到 Azure 時不建議依賴本機檔案。

### Options

- Supabase Storage
- Azure Blob Storage

### Tasks

- 新增 storage helper，例如：
  - `utils/storage.py`
- 上傳圖片後回傳 public URL 或 private object path。
- DB 中 `image_path` 改存雲端路徑。
- 管理端讀圖時支援 URL。
- 本機開發可以保留 local fallback。

### Acceptance Criteria

- Azure 重啟後，舊回報圖片仍可顯示。
- 管理端事件詳情能讀到雲端圖片。

## Priority 4: GPS Handling

目前 GPS 使用 browser `navigator.geolocation` via Streamlit component。

### Known Issue

Streamlit component 可能受 iframe permission policy 影響，瀏覽器定位授權不一定穩定。

### Tasks

- 保留手動輸入座標與行政區 fallback。
- GPS 取得逾時時要顯示明確訊息，不要一直卡在「取得中」。
- 成功取得 GPS 後同步更新：
  - `report_latitude`
  - `report_longitude`
  - `latitude_input`
  - `longitude_input`
- 如果定位 API 被擋，使用者仍可送出行政區回報。

### Acceptance Criteria

- GPS 失敗不阻止送出回報。
- H3 只在有 GPS 且 `h3` 套件可用時運作。
- 沒有 GPS 時仍可用 city/district 進行事件聚合與統計。

## Priority 5: Deployment on Azure

不要部署 `.venv`。

### Required Files

- `requirements.txt`
- startup command
- `.env.example`
- optional `Dockerfile`

### Suggested Azure Startup Command

```bash
cd crisislens && streamlit run app.py --server.address 0.0.0.0 --server.port 8000
```

若使用 Azure Container Apps，建議 Docker：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY crisislens/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY crisislens ./crisislens

WORKDIR /app/crisislens

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
```

### Azure App Settings

至少需要：

```txt
GEMINI_API_KEY=
DATABASE_URL=
```

若使用 Supabase Storage：

```txt
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_BUCKET=
```

## Priority 6: Documentation

目前已有：

- `docs/data_card.md`
- `docs/model_card.md`

建議再補：

- `docs/system_card.md`
- `docs/deployment_azure.md`
- `docs/demo_script.md`

### system_card.md Should Cover

- 民眾端流程
- 管理端流程
- 權限審核
- AI 辨識流程
- RAG 建議來源
- 事件聚合規則
- Priority Score
- H3 熱區圖
- Safety disclaimer

## Priority 7: Testing Checklist

至少補手動測試清單，之後可改成 automated tests。

### Auth

- 註冊新 user。
- user 申請 admin。
- admin 審核通過。
- rejected user 可重新申請。

### Citizen Portal

- 沒上傳圖片時按分析，要顯示錯誤。
- 上傳圖片後可分析。
- CLIP 模式可產生結果。
- CNN 模式在缺權重時不 crash。
- 兩者比較模式不跑版。
- 無 GPS 仍可送出。
- 有 GPS 可產生 H3 cell。

### Admin

- 非 admin 不能進管理頁。
- admin 可看事件列表。
- admin 可看事件詳情。
- H3 頁缺資料時顯示空狀態。
- 權限審核頁能 approve/reject。

## Important Notes

- 不要把 `crisislens.db` 當成正式資料庫。
- 不要把 `.venv` 部署到 Azure。
- 不要把 API key、DB password、service role key commit。
- 不要在前端直接暴露 Supabase service role key。
- 圖片和 GPS 都可能涉及個資，展示時要避免使用真實可識別資料。

## Recommended Next Sprint

建議下一輪只做這 5 件事：

1. 修完 frontend state 與兩者比較 UI。
2. 改 PostgreSQL/Supabase DB。
3. 圖片改雲端 Storage。
4. 補 `system_card.md` 與 Azure deployment doc。
5. 建立 demo seed data 與 demo script。

完成後，平台可從目前約 70% demo 完成度提升到約 85% 可展示部署版本。
