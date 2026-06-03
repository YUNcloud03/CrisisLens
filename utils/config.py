import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Model ─────────────────────────────────────────────────
CLIP_MODEL_NAME   = "ViT-L/14"
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

# ── 多描述投票版（每類別多條 prompt，取平均相似度）────────────
MULTI_PROMPT_SETS = {
    "Earthquake Damage": [
        "a photo of earthquake damage with collapsed buildings",
        "a photo of cracked walls and rubble after an earthquake",
        "earthquake destruction, broken concrete and debris",
        "a building that collapsed due to earthquake",
        "a road cracked and broken by an earthquake",
        "ground rupture and pavement splitting caused by seismic activity",
        "earthquake damage showing cracked asphalt and road surface",
    ],
    "Flood": [
        "a photo of a flooded street after heavy rain",
        "floodwater covering roads and houses",
        "a neighborhood submerged in water",
        "heavy flooding with brown muddy water on streets",
    ],
    "Fire": [
        "a photo of a fire disaster with smoke and flames",
        "a building on fire with thick black smoke",
        "fire burning a house at night",
        "flames and fire damage to a structure",
    ],
    "Typhoon or Storm Damage": [
        "a photo of storm or typhoon damage",
        "trees and power lines knocked down by typhoon winds",
        "wind damage from a typhoon with debris on streets",
        "destroyed structures after a strong storm",
    ],
    "Landslide": [
        "a photo of a landslide with mud and rocks falling from a hillside",
        "mudslide covering a mountain road with rocks and mud",
        "hillside collapse with debris and mud flow",
        "landslide damage on a slope with soil and boulders",
        "a slope failure where dirt and rocks have slid down a mountain",
    ],
    "Other or No Disaster": [
        "a normal street photo without disaster",
        "an ordinary urban scene with no damage",
        "a regular outdoor photo taken by a smartphone",
        "no visible disaster or damage in this photo",
    ],
}

# ── RAG ───────────────────────────────────────────────────
TOP_K_DOCS         = 4
CHUNK_SIZE         = 400   # characters per chunk
CHUNK_OVERLAP      = 80

NUM_CLASSES   = 6
