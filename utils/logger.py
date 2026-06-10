"""
CrisisLens 系統日誌工具。

使用方式：
    from utils.logger import get_logger
    logger = get_logger("clip_classify")
    logger.error("推論失敗", exc_info=True)

或快捷函式：
    from utils.logger import log_error, log_warning
    log_error("geocoding", "Nominatim 逾時", exc_info=True)

所有 WARNING 以上的訊息會：
  1. 輸出到 stderr（開發用）
  2. 寫入 SQLite error_logs 表（持久化）
"""
import json
import logging
import os
import sqlite3
import sys
import traceback
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "crisislens.db")


# ────────────────────────────────────────────────────────────────
# SQLite Handler
# ────────────────────────────────────────────────────────────────
class _SQLiteHandler(logging.Handler):
    """將 log record 寫入 error_logs 表。"""

    def emit(self, record: logging.LogRecord):
        try:
            tb = None
            if record.exc_info:
                tb = "".join(traceback.format_exception(*record.exc_info))

            extra_data = {}
            for attr in ("username", "request_id"):
                if hasattr(record, attr):
                    extra_data[attr] = getattr(record, attr)

            with sqlite3.connect(_DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO error_logs
                        (logged_at, level, context, message, traceback, username, extra)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        record.levelname,
                        record.name,                              # context = logger name
                        record.getMessage(),
                        tb,
                        extra_data.get("username"),
                        json.dumps(extra_data, ensure_ascii=False) if extra_data else None,
                    ),
                )
        except Exception:
            # Handler 本身不能拋例外（會造成遞迴）
            self.handleError(record)


# ────────────────────────────────────────────────────────────────
# 全域設定（只初始化一次）
# ────────────────────────────────────────────────────────────────
_root_configured = False

def _configure_root():
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    root = logging.getLogger("crisislens")
    root.setLevel(logging.DEBUG)

    if not root.handlers:
        # stderr handler（開發環境可見）
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.WARNING)
        sh.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))
        root.addHandler(sh)

        # SQLite handler
        db_h = _SQLiteHandler()
        db_h.setLevel(logging.WARNING)
        root.addHandler(db_h)


def get_logger(context: str) -> logging.Logger:
    """
    取得指定 context 的 logger。
    context 會成為 error_logs.context 欄位值，例如 "clip_classify"、"geocoding"。
    """
    _configure_root()
    return logging.getLogger(f"crisislens.{context}")


# ────────────────────────────────────────────────────────────────
# 快捷函式
# ────────────────────────────────────────────────────────────────
def log_error(context: str, message: str, exc_info=False,
              username: str = None, extra: dict = None):
    """將 ERROR 寫入 error_logs，不需手動建 logger。"""
    logger = get_logger(context)
    if username or extra:
        logger = logging.LoggerAdapter(logger, {
            **({"username": username} if username else {}),
            **(extra or {}),
        })
    logger.error(message, exc_info=exc_info)


def log_warning(context: str, message: str, exc_info=False):
    """將 WARNING 寫入 error_logs。"""
    get_logger(context).warning(message, exc_info=exc_info)
