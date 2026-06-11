"""
圖片儲存模組。

模式選擇（由環境變數決定）：
  AZURE_STORAGE_CONNECTION_STRING 已設定 → Azure Blob Storage
  未設定 → 本機 uploads/reports/（開發用）

用法：
    from utils.storage import save_image, is_azure_url
    fpath_or_url = save_image(pil_image, "abc123.jpg")
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image

# ── 環境偵測 ──────────────────────────────────────────────────
_CONN_STR  = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "crisislens-uploads").strip()
_USE_AZURE = bool(_CONN_STR)

_LOCAL_DIR = Path(__file__).resolve().parents[1] / "uploads" / "reports"

# ── Azure SDK 初始化（僅在設定連線字串時載入）────────────────
_AZURE_OK       = False
_blob_service   = None

if _USE_AZURE:
    try:
        from azure.storage.blob import (  # type: ignore[import-not-found]
            BlobServiceClient,
            ContentSettings as _ContentSettings,
        )
        _blob_service = BlobServiceClient.from_connection_string(_CONN_STR)
        # 確保 container 存在（已存在時 raise ResourceExistsError，直接忽略）
        try:
            _blob_service.create_container(_CONTAINER)
        except Exception:
            pass
        _AZURE_OK = True
    except ImportError:
        import warnings
        warnings.warn(
            "AZURE_STORAGE_CONNECTION_STRING 已設定，但 azure-storage-blob 套件未安裝。\n"
            "請執行：pip install 'azure-storage-blob>=12.19.0'\n"
            "本次改用本機 uploads/ 儲存。",
            stacklevel=1,
        )
        _USE_AZURE = False


# ── 公開 API ─────────────────────────────────────────────────
def save_image(img: Image.Image, filename: str) -> str:
    """
    儲存 PIL Image，回傳可存入 DB 的路徑或 URL。

    Parameters
    ----------
    img      : PIL.Image.Image  已開啟的圖片物件
    filename : str              目標檔名（建議用 uuid.hex + ".jpg"）

    Returns
    -------
    str
        Azure 模式 → Blob 的 HTTPS URL（可直接用於 <img src> / st.image）
        本機模式  → 本機絕對路徑
    """
    if _USE_AZURE and _AZURE_OK and _blob_service is not None:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        blob_client = _blob_service.get_blob_client(
            container=_CONTAINER, blob=filename
        )
        blob_client.upload_blob(
            buf,
            overwrite=True,
            content_settings=_ContentSettings(content_type="image/jpeg"),
        )
        return blob_client.url
    else:
        _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        fpath = str(_LOCAL_DIR / filename)
        img.save(fpath, "JPEG", quality=85)
        return fpath


def is_azure_url(path: str) -> bool:
    """
    判斷 DB 中儲存的 image_path 是否為 Azure Blob URL。
    True  → 可直接用作 <img src> / requests.get
    False → 本機路徑，需用 st.image(path) 或 open(path)
    """
    return bool(path and path.startswith("https://"))


def storage_mode() -> str:
    """回傳目前儲存模式說明字串，供 UI 顯示。"""
    if _USE_AZURE and _AZURE_OK:
        return f"Azure Blob Storage（container: {_CONTAINER}）"
    return f"本機檔案系統（{_LOCAL_DIR}）"
