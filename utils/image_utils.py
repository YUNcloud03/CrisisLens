from PIL import Image
import io


def load_image(uploaded_file) -> Image.Image:
    """讀取 Streamlit UploadedFile，回傳 PIL Image（RGB）。"""
    img_bytes = uploaded_file.read()
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return img


def resize_for_display(img: Image.Image, max_size: int = 480) -> Image.Image:
    """等比例縮小，用於前端顯示（不影響模型輸入）。"""
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    scale = max_size / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
