# CrisisLens — Azure 部署指南

> **適用版本**：CrisisLens v2.0  
> **最後更新**：2026-06-08  
> **建議部署目標**：Azure Container Apps + Azure Database for PostgreSQL + Azure Blob Storage

---

## 架構概覽

```
使用者瀏覽器
    │
    ▼
Azure Container Apps
  └── CrisisLens Streamlit (Docker)
        ├── models/  ← CLIP ViT-L/14, DisasterCNN_v1
        ├── rag/     ← FAISS index + Gemini API
        └── utils/   ← storage.py → Azure Blob Storage
              │
              ├── PostgreSQL (Azure Database for PostgreSQL)
              └── Azure Blob Storage (圖片)
```

---

## 前置需求

| 工具 | 版本 | 說明 |
|------|------|------|
| Azure CLI | >= 2.50 | `az login` 登入 |
| Docker Desktop | >= 24 | 本機建置映像 |
| Python | 3.11 | 本機測試用 |

---

## Step 1：建立 Azure 資源

```bash
# 登入
az login

# 建立 Resource Group
az group create --name crisislens-rg --location japaneast

# 建立 Container Registry（ACR）
az acr create --resource-group crisislens-rg \
  --name crisislensacr --sku Basic

# 建立 PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group crisislens-rg \
  --name crisislens-pg \
  --location japaneast \
  --admin-user cladmin \
  --admin-password "請改成強密碼!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --public-access 0.0.0.0

# 建立資料庫
az postgres flexible-server db create \
  --resource-group crisislens-rg \
  --server-name crisislens-pg \
  --database-name crisislens

# 建立 Storage Account
az storage account create \
  --name crisislensstore \
  --resource-group crisislens-rg \
  --location japaneast \
  --sku Standard_LRS

# 建立 Blob Container
az storage container create \
  --name crisislens-uploads \
  --account-name crisislensstore \
  --public-access off
```

---

## Step 2：取得連線字串

```bash
# PostgreSQL 連線字串
# 格式：postgresql://USER:PASS@HOST:5432/DBNAME?sslmode=require
# 範例：
# postgresql://cladmin:密碼@crisislens-pg.postgres.database.azure.com:5432/crisislens?sslmode=require

# Blob Storage 連線字串
az storage account show-connection-string \
  --name crisislensstore \
  --resource-group crisislens-rg \
  --query connectionString -o tsv
```

---

## Step 3：建立 Docker 映像並推送

```bash
cd "C:\Users\LIYUN\Desktop\DisasterAid AI\crisislens"

# 登入 ACR
az acr login --name crisislensacr

# 建置（CPU-only torch，約 4GB）
docker build -t crisislensacr.azurecr.io/crisislens:latest .

# 推送
docker push crisislensacr.azurecr.io/crisislens:latest
```

> **注意**：首次建置需下載 PyTorch CPU 約 700MB，建議在網路穩定環境執行。

---

## Step 4：部署 Container App

```bash
# 建立 Container Apps Environment
az containerapp env create \
  --name crisislens-env \
  --resource-group crisislens-rg \
  --location japaneast

# 部署（一次設定所有環境變數）
az containerapp create \
  --name crisislens \
  --resource-group crisislens-rg \
  --environment crisislens-env \
  --image crisislensacr.azurecr.io/crisislens:latest \
  --registry-server crisislensacr.azurecr.io \
  --target-port 8501 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 2.0 \
  --memory 4.0Gi \
  --env-vars \
    GEMINI_API_KEY=secretref:gemini-key \
    DATABASE_URL=secretref:db-url \
    AZURE_STORAGE_CONNECTION_STRING=secretref:blob-conn \
    AZURE_STORAGE_CONTAINER=crisislens-uploads \
    STREAMLIT_SERVER_COOKIE_SECRET=secretref:cookie-secret
```

> 使用 `secretref:` 讓 Secret 不直接出現在指令歷史中。  
> 先用 `az containerapp secret set` 建立 Secret：
> ```bash
> # 產生隨機 cookie secret（執行一次，保存輸出）
> python -c "import secrets; print(secrets.token_hex(32))"
>
> az containerapp secret set \
>   --name crisislens \
>   --resource-group crisislens-rg \
>   --secrets \
>     gemini-key="你的_GEMINI_API_KEY" \
>     db-url="postgresql://..." \
>     blob-conn="DefaultEndpointsProtocol=https;..." \
>     cookie-secret="你產生的64字元隨機字串"
> ```

> ⚠️ **`STREAMLIT_SERVER_COOKIE_SECRET` 必須設定**：未設定時 Streamlit 使用固定預設值，存在 session 偽造風險。同一 app 的所有副本（replicas）需使用相同值，否則水平擴展後 session 會失效。

---

## Step 5：初始化資料庫

Container 首次啟動時 `startup.sh` 會自動呼叫 `init_db()`，包含：
- 建立所有 Tables（schema_pg.sql）
- 建立管理員帳號，密碼請由部署環境變數或安全的初始化流程提供；不要使用公開預設密碼。
- ⚠️ **請在首次登入後立即修改密碼！**

---

## Step 6：模型權重

CLIP ViT-L/14 在首次推論時會從 OpenAI CDN 自動下載（約 900MB），快取於容器內 `~/.cache/clip/`。

DisasterCNN_v1 需手動放置：
```bash
# 在本機把 custom_cnn.pth 打包進映像前複製進去
cp models/custom_cnn.pth <build-context>/models/
```
或在 Dockerfile 中加入：
```dockerfile
COPY models/custom_cnn.pth models/custom_cnn.pth
```

---

## Step 7：驗收清單

| 項目 | 驗證方式 |
|------|---------|
| 首頁可開啟 | 瀏覽器訪問 Container App URL |
| admin 登入正常 | 使用部署時建立的管理員帳號登入 → 進入 Event Dashboard |
| 上傳圖片可分析 | 上傳測試圖 → 右側出現 AI 結果 |
| 圖片存入 Blob | Azure Portal → Storage → crisislens-uploads |
| 回報送出後有事件 | 管理端 Event Dashboard 顯示事件 |
| H3 熱圖可開啟 | 無 h3 資料時顯示「尚無資料」提示 |
| RAG 建議出現 | 有 GEMINI_API_KEY 時顯示「✨ Gemini LLM」 |

---

## 環境變數完整清單

| 變數 | 必填 | 說明 |
|------|------|------|
| `GEMINI_API_KEY` | 否 | 未填時 RAG 使用內建指引 |
| `DATABASE_URL` | **是**（Azure） | `postgresql://USER:PASS@HOST:5432/DB?sslmode=require` |
| `AZURE_STORAGE_CONNECTION_STRING` | 否（Azure 建議） | 未填時圖片存在容器本機（重啟後遺失）|
| `AZURE_STORAGE_CONTAINER` | 否 | 預設 `crisislens-uploads` |
| `STREAMLIT_SERVER_COOKIE_SECRET` | **是**（正式部署） | 防止 session cookie 偽造，需 64 字元隨機字串 |
| `USE_LOCAL_SHIELDGEMMA` | 否 | `true` 啟用本機 ShieldGemma，需 GPU 環境 |

---

## 常見問題

**Q: Container 啟動後 CLIP 首次推論很慢？**  
A: ViT-L/14 首次需下載約 900MB 到 `~/.cache/clip/`。若需快速冷啟動，可在 Dockerfile 預先下載。

**Q: 如何更新程式碼後重新部署？**  
```bash
docker build -t crisislensacr.azurecr.io/crisislens:latest .
docker push crisislensacr.azurecr.io/crisislens:latest
az containerapp update --name crisislens --resource-group crisislens-rg \
  --image crisislensacr.azurecr.io/crisislens:latest
```

**Q: 資料庫 migration 怎麼執行？**  
`init_db()` 是冪等的 — 重新啟動 Container 會自動執行，不會破壞現有資料。

**Q: 如何備份資料庫？**  
```bash
az postgres flexible-server backup create \
  --resource-group crisislens-rg \
  --name crisislens-pg
```

---

## 費用估算（每月，日本東區）

| 服務 | 規格 | 估算費用 |
|------|------|---------|
| Container Apps | 2 vCPU / 4GB，1 replica | ~USD 80 |
| PostgreSQL | Burstable B1ms | ~USD 14 |
| Storage | 10GB LRS | ~USD 1 |
| **合計** | | **~USD 95 / 月** |

> Demo 期間可手動縮減至 0 replicas 停止計費。
