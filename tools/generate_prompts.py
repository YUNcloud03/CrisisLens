"""
使用 Gemini 為每個災害類別生成多條視覺描述，存成 utils/prompts_generated.json。
執行一次即可，之後 CLIP 分類會自動載入這份 JSON。

執行方式：
    python tools/generate_prompts.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import google.generativeai as genai
from utils.config import GEMINI_API_KEY, CLASSES_EN

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "utils", "prompts_generated.json")

SYSTEM_PROMPT = (
    "You are an expert in computer vision and disaster image recognition. "
    "Your descriptions will be used for CLIP zero-shot image classification. "
    "Always respond in English only."
)

USER_TEMPLATE = """\
List exactly 12 short visual descriptions of what "{disaster_type}" looks like \
in a photo taken by a smartphone.

Rules:
- Each description must be under 15 words
- Focus only on visible physical features (what the camera actually sees)
- Cover diverse scenarios: urban, rural, close-up, wide shot, day, night
- Do NOT include the disaster type name in every sentence
- Return one description per line, no numbering, no bullet points, no extra text
"""


def _call_gemini(model, disaster_type: str) -> list[str]:
    response = model.generate_content(
        USER_TEMPLATE.format(disaster_type=disaster_type)
    )
    lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
    # 過濾掉空行和多餘的標點
    return [l.lstrip("-•・").strip() for l in lines if len(l) > 5][:12]


def generate(force: bool = False):
    if not GEMINI_API_KEY:
        print("❌ 找不到 GEMINI_API_KEY，請確認 .env 檔案設定正確。")
        sys.exit(1)

    if os.path.exists(OUTPUT_PATH) and not force:
        print(f"✅ {OUTPUT_PATH} 已存在，跳過生成。")
        print("   加上 --force 參數可強制重新生成。")
        return

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    result = {}
    for cls in CLASSES_EN:
        print(f"⏳ 生成中：{cls} ...")
        try:
            prompts = _call_gemini(model, cls)
            result[cls] = prompts
            print(f"   ✓ 取得 {len(prompts)} 條描述")
            for p in prompts:
                print(f"     · {p}")
        except Exception as e:
            print(f"   ⚠️  失敗：{e}，使用空列表")
            result[cls] = []
        time.sleep(1)  # 避免超過 API rate limit

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已儲存至 {OUTPUT_PATH}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    generate(force=force)
