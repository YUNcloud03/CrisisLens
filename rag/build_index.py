"""
建立 FAISS vector index。

執行方式：
    python rag/build_index.py

會讀取 rag_docs/ 下所有 .md 檔案，切塊後用 sentence-transformers 向量化，
儲存成 FAISS index 和 chunks 清單。
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import glob
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from utils.config import (
    RAG_DOCS_DIR, FAISS_INDEX_PATH,
    CHUNK_SIZE, CHUNK_OVERLAP
)

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"   # 支援中文
CHUNKS_PATH = FAISS_INDEX_PATH + "_chunks.json"


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """簡單固定長度切塊，帶 overlap。"""
    chunks = []
    start  = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 30]   # 過濾太短的片段


def build():
    md_files = glob.glob(os.path.join(RAG_DOCS_DIR, "*.md"))
    if not md_files:
        print(f"找不到 {RAG_DOCS_DIR}/*.md，請先建立 SOP 文件。")
        return

    print(f"找到 {len(md_files)} 個文件：{[os.path.basename(f) for f in md_files]}")

    all_chunks  = []
    all_sources = []

    for path in md_files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        chunks = _split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        all_chunks.extend(chunks)
        all_sources.extend([os.path.basename(path)] * len(chunks))
        print(f"  {os.path.basename(path)} → {len(chunks)} 塊")

    print(f"\n共 {len(all_chunks)} 個 chunks，開始 embedding...")

    embedder   = SentenceTransformer(EMBED_MODEL)
    embeddings = embedder.encode(all_chunks, show_progress_bar=True, batch_size=32)
    embeddings = np.array(embeddings, dtype="float32")

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    os.makedirs(os.path.dirname(FAISS_INDEX_PATH) or ".", exist_ok=True)
    faiss.write_index(index, FAISS_INDEX_PATH + ".bin")

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            [{"text": c, "source": s} for c, s in zip(all_chunks, all_sources)],
            f, ensure_ascii=False, indent=2
        )

    print(f"\nFAISS index  → {FAISS_INDEX_PATH}.bin")
    print(f"Chunks JSON  → {CHUNKS_PATH}")
    print("建立完成！")


if __name__ == "__main__":
    build()
