from PIL import Image
import io


def strip_exif(img: Image.Image) -> Image.Image:
    """
    移除所有 EXIF 資料，保護上傳者隱私。

    原始照片中可能含有 GPS 座標、設備序號等個資。
    做法：逐像素重建新圖像，不攜帶任何 metadata。
    """
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    # 保留色彩設定檔（若有），但不保留其他 info
    if "icc_profile" in img.info:
        clean.info["icc_profile"] = img.info["icc_profile"]
    return clean


def load_image(uploaded_file) -> Image.Image:
    """讀取 Streamlit UploadedFile，回傳已剝離 EXIF 的 PIL Image（RGB）。"""
    img_bytes = uploaded_file.read()
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return strip_exif(img)


def resize_for_display(img: Image.Image, max_size: int = 480) -> Image.Image:
    """等比例縮小，用於前端顯示（不影響模型輸入）。"""
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    scale = max_size / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
