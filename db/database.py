"""
資料庫連線與初始化。

模式選擇（由環境變數決定）：
  DATABASE_URL 已設定 → PostgreSQL（psycopg2）
  DATABASE_URL 未設定 → SQLite（本機開發用）

_PGConnWrapper 讓 queries.py 不需大幅修改：
  • execute(sql, params) 自動轉換 ? → %s、:name → %(name)s
  • fetchone() / fetchall() 回傳 dict-like RealDictRow
"""
import os
import re
import sys
import sqlite3
import hashlib
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 環境偵測 ──────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")          # e.g. postgresql://user:pass@host:5432/dbname
_USE_PG      = bool(DATABASE_URL)

if _USE_PG:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    _pg_pool = None
else:
    DB_PATH     = os.path.join(os.path.dirname(__file__), "..", "crisislens.db")
    SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

SCHEMA_PG_PATH = os.path.join(os.path.dirname(__file__), "schema_pg.sql")


# ── PostgreSQL 相容包裝層 ─────────────────────────────────────
_NAMED_PARAM_RE = re.compile(r':([A-Za-z_]\w*)')


def _to_pg_sql(sql: str, params) -> tuple[str, object]:
    """
    轉換 SQLite 語法 → PostgreSQL 語法。
    1. INSERT OR IGNORE INTO X → INSERT INTO X … ON CONFLICT DO NOTHING
    2. :name  → %(name)s  （dict 參數）
    3. ?      → %s        （tuple 參數）
    """
    # INSERT OR IGNORE → INSERT … ON CONFLICT DO NOTHING
    if re.search(r'INSERT\s+OR\s+IGNORE', sql, re.IGNORECASE):
        sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', sql, flags=re.IGNORECASE)
        sql = sql.rstrip().rstrip(';') + '\nON CONFLICT DO NOTHING'

    if isinstance(params, dict):
        # Named params: :name → %(name)s
        sql = _NAMED_PARAM_RE.sub(r'%(\1)s', sql)
    else:
        # Positional params: ? → %s
        sql = sql.replace('?', '%s')

    return sql, params


class _PGConnWrapper:
    """psycopg2 連線的 sqlite3 相容包裝。"""

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, sql: str, params=None):
        sql, params = _to_pg_sql(sql, params)
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        return cur

    def executescript(self, sql: str):
        """切分 SQL script 後逐句執行。"""
        cur = self._conn.cursor()
        buf = []
        for line in sql.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
            buf.append(line)
            if stripped.endswith(';'):
                stmt = '\n'.join(buf).strip().rstrip(';')
                if stmt:
                    try:
                        cur.execute(stmt)
                    except psycopg2.Error:
                        self._conn.rollback()   # 讓後續 stmt 繼續
                buf = []
        cur.close()

    def commit(self):   self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):    self._conn.close()


# ── 連線工廠 ──────────────────────────────────────────────────
def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1, maxconn=10, dsn=DATABASE_URL
        )
    return _pg_pool


@contextmanager
def get_conn():
    """
    取得資料庫連線（context manager）。
    自動 commit / rollback，用完即還給 pool（PG）或關閉（SQLite）。
    """
    if _USE_PG:
        pool = _get_pg_pool()
        raw  = pool.getconn()
        conn = _PGConnWrapper(raw)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(raw)
    else:
        raw  = sqlite3.connect(DB_PATH)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL")
        raw.execute("PRAGMA foreign_keys=ON")
        try:
            yield raw
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            raw.close()


# ── Schema 初始化 ────────────────────────────────────────────
_SQLITE_EXTRA_COLS = [
    # (table, column, definition)  ← 向後相容，新欄位在此補
    ("reports", "power_outage",             "INTEGER DEFAULT 0"),
    ("reports", "clip_top2_gap",            "REAL"),
    # Safety Guard 欄位（ShieldGemma 架構）
    ("reports", "input_safety_label",       "TEXT DEFAULT 'safe'"),
    ("reports", "output_safety_label",      "TEXT DEFAULT 'safe'"),
    ("reports", "safety_reason",            "TEXT"),
    # 提交者（速率限制 / 稽核用）
    ("reports", "submitted_by",             "TEXT"),
    ("events",  "vulnerability_score",      "INTEGER DEFAULT 0"),
    ("events",  "credibility_score",        "INTEGER DEFAULT 0"),
    ("events",  "power_outage",             "INTEGER DEFAULT 0"),
    ("users",   "role",                     "TEXT NOT NULL DEFAULT 'user'"),
    ("users",   "permission_status",        "TEXT NOT NULL DEFAULT 'none'"),
    ("users",   "created_at",               "TEXT"),
    ("users",   "updated_at",               "TEXT"),
    ("model_runs", "inference_latency_ms",  "REAL"),
]

_PG_EXTRA_COLS = [
    # PostgreSQL 版本的 ALTER TABLE IF NOT EXISTS 用 DO 塊
]


def _run_migrations(conn):
    """冪等欄位補增（SQLite / PostgreSQL 共用邏輯）。"""
    if _USE_PG:
        for table, col, defn in _SQLITE_EXTRA_COLS:
            try:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {defn}"
                )
            except Exception:
                pass
    else:
        for table, col, defn in _SQLITE_EXTRA_COLS:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass


def _fix_event_names(conn):
    """
    冪等：將仍含英文 disaster_type 的事件名稱改成中文格式。
    格式：{YYYY-MM-DD} {縣市}{行政區}{災害中文}事件
    """
    from aggregation.event_matcher import _build_event_name, _disaster_zh, _TYPE_ZH

    # 取所有事件
    rows = conn.execute(
        "SELECT event_id, event_name, city, district, disaster_type, first_report_time FROM events"
    ).fetchall()

    for row in rows:
        ev       = dict(row)
        name     = ev.get("event_name") or ""
        dtype_en = ev.get("disaster_type") or ""

        # 判斷是否含有英文 type（需要修正）
        needs_fix = any(en in name for en in _TYPE_ZH) or (dtype_en and dtype_en in name)
        if not needs_fix:
            continue

        new_name = _build_event_name({
            "city":         ev.get("city"),
            "district":     ev.get("district"),
            "disaster_type": dtype_en,
            "event_time":   ev.get("first_report_time"),
        })

        if new_name != name:
            conn.execute(
                "UPDATE events SET event_name = ? WHERE event_id = ?",
                (new_name, ev["event_id"]),
            )


def _data_migration(conn):
    """
    一次性資料遷移（冪等）。
    Step 1  h3_grid_summary → grid_summary
    Step 2  Backfill reports.grid_id / grid_type
    Step 3  Build grid_summary for district / city
    Step 4  Event status rename: verified→active, closed→resolved
    """
    # Step 1
    try:
        conn.execute("""
            INSERT INTO grid_summary (
                grid_id, grid_type, h3_resolution,
                report_count, event_count, image_count,
                main_disaster_type, max_priority_score, max_priority_level,
                max_report_severity_score, estimated_people_need_help,
                latest_report_time, center_lat, center_lng, updated_at
            )
            SELECT
                h3_cell, 'h3', h3_resolution,
                report_count, event_count, image_count,
                main_disaster_type, max_priority_score, max_priority_level,
                max_report_severity_score, estimated_people_need_help,
                latest_report_time, center_lat, center_lng, updated_at
            FROM h3_grid_summary
            WHERE h3_cell IS NOT NULL AND h3_cell != ''
            ON CONFLICT DO NOTHING
        """)
    except Exception:
        pass

    # Step 2
    conn.execute("""
        UPDATE reports SET grid_id = h3_cell, grid_type = 'h3'
        WHERE (grid_id IS NULL OR grid_id = '')
          AND h3_cell IS NOT NULL AND h3_cell != ''
    """)
    conn.execute("""
        UPDATE reports
        SET grid_id = city || '_' || district, grid_type = 'district'
        WHERE (grid_id IS NULL OR grid_id = '')
          AND city IS NOT NULL AND city != ''
          AND district IS NOT NULL AND district != ''
    """)
    conn.execute("""
        UPDATE reports SET grid_id = city, grid_type = 'city'
        WHERE (grid_id IS NULL OR grid_id = '')
          AND city IS NOT NULL AND city != ''
    """)

    # Step 3 — ensure need_review_count column exists (SQLite only)
    if not _USE_PG:
        try:
            conn.execute("ALTER TABLE grid_summary ADD COLUMN need_review_count INTEGER DEFAULT 0")
        except Exception:
            pass

    conn.execute("""
        INSERT INTO grid_summary (
            grid_id, grid_type, h3_resolution, city, district,
            report_count, event_count, image_count, main_disaster_type,
            max_priority_score, max_priority_level, max_report_severity_score,
            estimated_people_need_help, need_review_count,
            latest_report_time, center_lat, center_lng, updated_at
        )
        SELECT
            r.grid_id, r.grid_type, NULL, MAX(r.city), MAX(r.district),
            COUNT(*), 0, COUNT(*),
            (
                SELECT r2.disaster_type FROM reports r2
                WHERE r2.grid_id = r.grid_id AND r2.grid_type = r.grid_type
                  AND r2.disaster_type IS NOT NULL
                GROUP BY r2.disaster_type ORDER BY COUNT(*) DESC LIMIT 1
            ),
            COALESCE(MAX(CAST(r.report_severity_score AS FLOAT)), 0),
            CASE
                WHEN MAX(CAST(r.report_severity_score AS FLOAT)) >= 70 THEN 'High'
                WHEN MAX(CAST(r.report_severity_score AS FLOAT)) >= 40 THEN 'Medium'
                ELSE 'Low'
            END,
            COALESCE(MAX(r.report_severity_score), 0),
            COALESCE(MAX(r.reported_people_count), 0),
            SUM(CASE WHEN r.need_review = 1 THEN 1 ELSE 0 END),
            MAX(r.upload_time), NULL, NULL,
            strftime('%Y-%m-%dT%H:%M:%S','now')
        FROM reports r
        WHERE r.grid_type IN ('district', 'city')
          AND r.grid_id IS NOT NULL AND r.grid_id != ''
        GROUP BY r.grid_id, r.grid_type
        ON CONFLICT DO NOTHING
    """ if not _USE_PG else """
        INSERT INTO grid_summary (
            grid_id, grid_type, h3_resolution, city, district,
            report_count, event_count, image_count, main_disaster_type,
            max_priority_score, max_priority_level, max_report_severity_score,
            estimated_people_need_help, need_review_count,
            latest_report_time, center_lat, center_lng, updated_at
        )
        SELECT
            r.grid_id, r.grid_type, NULL, MAX(r.city), MAX(r.district),
            COUNT(*), 0, COUNT(*),
            (
                SELECT r2.disaster_type FROM reports r2
                WHERE r2.grid_id = r.grid_id AND r2.grid_type = r.grid_type
                  AND r2.disaster_type IS NOT NULL
                GROUP BY r2.disaster_type ORDER BY COUNT(*) DESC LIMIT 1
            ),
            COALESCE(MAX(CAST(r.report_severity_score AS FLOAT)), 0),
            CASE
                WHEN MAX(CAST(r.report_severity_score AS FLOAT)) >= 70 THEN 'High'
                WHEN MAX(CAST(r.report_severity_score AS FLOAT)) >= 40 THEN 'Medium'
                ELSE 'Low'
            END,
            COALESCE(MAX(r.report_severity_score), 0),
            COALESCE(MAX(r.reported_people_count), 0),
            SUM(CASE WHEN r.need_review = 1 THEN 1 ELSE 0 END),
            MAX(r.upload_time), NULL, NULL,
            NOW()
        FROM reports r
        WHERE r.grid_type IN ('district', 'city')
          AND r.grid_id IS NOT NULL AND r.grid_id != ''
        GROUP BY r.grid_id, r.grid_type
        ON CONFLICT DO NOTHING
    """)

    # Step 4 — status rename
    conn.execute("UPDATE events SET status = 'active'   WHERE status = 'verified'")
    conn.execute("UPDATE events SET status = 'resolved' WHERE status = 'closed'")

    # Step 5 — event name 中文化（冪等：只更新仍含英文 type 的舊事件）
    _fix_event_names(conn)


def _bootstrap_admin(conn):
    """新安裝時建立初始 admin 帳號。"""
    if _USE_PG:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        count = row["c"] if row else 0
    else:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        count = dict(row)["c"] if row else 0
    if count > 0:
        return
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin").strip() or "admin"
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "").strip()
    if not admin_password:
        # Local development fallback only. Production should always set
        # DEFAULT_ADMIN_PASSWORD in environment variables.
        admin_password = "change-me-before-deploy"
    salt   = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", admin_password.encode("utf-8"), salt.encode(), 120_000)
    phash  = f"pbkdf2_sha256${salt}${digest.hex()}"
    now    = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role, permission_status, created_at, updated_at)
        VALUES (%s, %s, 'admin', 'approved', %s, %s)
        """ if _USE_PG else
        """
        INSERT INTO users (username, password_hash, role, permission_status, created_at, updated_at)
        VALUES (?, ?, 'admin', 'approved', ?, ?)
        """,
        (admin_username, phash, now, now),
    )


def init_db():
    """建立所有資料表並執行遷移。"""
    schema_path = SCHEMA_PG_PATH if _USE_PG else SCHEMA_PATH
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    with get_conn() as conn:
        conn.executescript(schema_sql)
        _run_migrations(conn)
        _bootstrap_admin(conn)
        _data_migration(conn)
