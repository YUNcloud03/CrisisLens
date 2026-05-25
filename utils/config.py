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
    "Earthquake Damage",
    "Flood",
    "Fire",
    "Typhoon or Storm Damage",
    "Landslide",
    "Other or No Disaster",
]

CLASSES_ZH = [
    "地震或建築損壞",
    "淹水",
    "火災",
    "颱風或強風災損",
    "土石流或坍方",
    "其他或無明顯災害",
]

CLASS_MAP = dict(zip(CLASSES_EN, CLASSES_ZH))

# ── Prompt sets ───────────────────────────────────────────
PROMPT_SETS = {
    "A｜簡短版": [
        "earthquake",
        "flood",
        "fire",
        "typhoon damage",
        "landslide",
        "normal scene",
    ],
    "B｜完整句版": [
        "a photo of earthquake damage with collapsed buildings",
        "a photo of a flooded street after heavy rain",
        "a photo of a fire disaster with smoke and flames",
        "a photo of storm or typhoon damage",
        "a photo of a landslide blocking a road",
        "a normal street photo without disaster",
    ],
    "C｜社群情境版": [
        "a social media photo showing earthquake damage after a strong earthquake",
        "a social media photo showing flood damage after heavy rainfall",
        "a social media photo showing a fire emergency",
        "a social media photo showing typhoon damage in a city",
        "a social media photo showing landslide damage in a mountain area",
        "a social media photo showing no visible disaster",
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
NUM_CLASSES   = 6
