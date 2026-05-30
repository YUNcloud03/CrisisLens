import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Model ─────────────────────────────────────────────────
CLIP_MODEL_NAME   = "ViT-B/32"
RESNET_WEIGHTS    = "models/resnet50_linear.pth"
FAISS_INDEX_PATH  = "rag/faiss_index"
RAG_DOCS_DIR      = "rag_docs"

# ── Disaster classes ──────────────────────────────────────
CLASSES_EN = [
    "Cyclone",
    "Earthquake",
    "Flood",
    "Wildfire",
]

CLASSES_ZH = [
    "颱風或強風災損",
    "地震或建築損壞",
    "淹水",
    "火災",
]

CLASS_MAP = dict(zip(CLASSES_EN, CLASSES_ZH))

# ── Prompt sets ───────────────────────────────────────────
PROMPT_SETS = {
    "A｜簡短版": [
        "cyclone",
        "earthquake",
        "flood",
        "wildfire",
    ],
    "B｜完整句版": [
        "a photo of typhoon or cyclone damage with strong wind",
        "a photo of earthquake damage with collapsed buildings",
        "a photo of a flooded street after heavy rain",
        "a photo of wildfire with smoke and flames",
    ],
    "C｜社群情境版": [
        "a social media photo showing typhoon or cyclone damage",
        "a social media photo showing earthquake damage after a strong earthquake",
        "a social media photo showing flood damage after heavy rainfall",
        "a social media photo showing a wildfire emergency",
    ],
}

# ── RAG ───────────────────────────────────────────────────
TOP_K_DOCS         = 4
CHUNK_SIZE         = 400   # characters per chunk
CHUNK_OVERLAP      = 80

# ── ResNet training ───────────────────────────────────────
BATCH_SIZE   = 32
LEARNING_RATE = 1e-3
EPOCHS        = 5
NUM_CLASSES   = 4
