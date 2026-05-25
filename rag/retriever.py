"""FAISS 檢索模組。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import faiss
import numpy as np
import functools
from sentence_transformers import SentenceTransformer

from utils.config import FAISS_INDEX_PATH, TOP_K_DOCS

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNKS_PATH = FAISS_INDEX_PATH + "_chunks.json"


@functools.lru_cache(maxsize=1)
def _load_index():
    index_file  = FAISS_INDEX_PATH + ".bin"
    if not os.path.exists(index_file):
        return None, None, None

    index    = faiss.read_index(index_file)
    embedder = SentenceTransformer(EMBED_MODEL)

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)   # list of {"text": ..., "source": ...}

    return index, embedder, chunks


def retrieve(query: str, top_k: int = TOP_K_DOCS) -> list[dict]:
    """
    根據 query 檢索最相關的 top_k 個文件片段。

    Returns list of:
        {"text": "...", "source": "flood_sop.md", "score": 0.42}
    """
    index, embedder, chunks = _load_index()
    if index is None:
        return []

    q_vec = embedder.encode([query], show_progress_bar=False)
    q_vec = np.array(q_vec, dtype="float32")

    distances, indices = index.search(q_vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        results.append({
            "text":   chunks[idx]["text"],
            "source": chunks[idx]["source"],
            "score":  float(dist),
        })
    return results


def index_exists() -> bool:
    return os.path.exists(FAISS_INDEX_PATH + ".bin")
