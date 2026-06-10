# ============================================================
# CrisisLens — Dockerfile
# 用於 Azure Container Apps / Azure Container Registry
# ============================================================

FROM python:3.11-slim

# 系統依賴（psycopg2-binary 需要 libpq，slim 版已包含）
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先複製 requirements.txt，利用 Docker layer cache
COPY requirements.txt .

# 安裝 Python 套件
# --no-cache-dir 減少映像大小；torch CPU-only 版本大幅縮小
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.0+cpu torchvision==0.17.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 複製所有專案檔案（.dockerignore 會排除不需要的目錄）
COPY . .

# 建立上傳目錄（本機模式備用）
RUN mkdir -p uploads/reports

# Streamlit 預設設定
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 開放 Streamlit port
EXPOSE 8501

# 啟動腳本
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

CMD ["/startup.sh"]
