#!/bin/bash
# ============================================================
# CrisisLens 啟動腳本
# 在 Streamlit 啟動前執行 DB schema 初始化
# ============================================================
set -e

echo "[startup] Python: $(python --version)"
echo "[startup] DATABASE_URL: ${DATABASE_URL:+已設定（已隱藏）}${DATABASE_URL:-未設定，使用 SQLite}"

# 建立 FAISS index（若還沒建）
if [ ! -f "rag/faiss_index.bin" ]; then
    echo "[startup] 建立 FAISS index..."
    python rag/build_index.py || echo "[startup] FAISS index 建立失敗，RAG 將使用 fallback"
fi

# 啟動 Streamlit
echo "[startup] 啟動 Streamlit..."
exec streamlit run app.py \
    --server.port "${PORT:-8501}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false
