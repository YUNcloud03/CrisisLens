"""SQLite 連線與初始化（含 column migration）。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlite3
from contextlib import contextmanager

DB_PATH     = os.path.join(os.path.dirname(__file__), "..", "crisislens.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# (table, column, definition)
_MIGRATIONS = [
    # ── reports 舊欄位 ──────────────────────────────────────
    ("reports", "location_source",          "TEXT"),
    ("reports", "h3_cell",                  "TEXT"),
    ("reports", "h3_resolution",            "INTEGER DEFAULT 9"),
    # ── reports 新欄位 v2 ───────────────────────────────────
    ("reports", "grid_id",                  "TEXT"),
    ("reports", "grid_type",                "TEXT"),
    ("reports", "clip_model_version",       "TEXT"),
    ("reports", "clip_prompt_version",      "TEXT"),
    ("reports", "clip_disaster_type",       "TEXT"),
    ("reports", "clip_top3",                "TEXT"),
    ("reports", "resnet_model_version",     "TEXT"),
    ("reports", "resnet_disaster_type",     "TEXT"),
    ("reports", "resnet_confidence",        "REAL"),
    ("reports", "model_agreement",          "INTEGER DEFAULT 1"),
    ("reports", "need_review",              "INTEGER DEFAULT 0"),
    ("reports", "rag_version",              "TEXT"),
    ("reports", "model_run_id",             "INTEGER"),
    ("reports", "aggregation_rule_version", "TEXT"),
    ("reports", "priority_rule_version",    "TEXT"),
    # ── events 舊欄位 ───────────────────────────────────────
    ("events",  "location_source",          "TEXT"),
    ("events",  "h3_cell",                  "TEXT"),
    ("events",  "h3_resolution",            "INTEGER DEFAULT 9"),
    # ── events 新欄位 v2 ────────────────────────────────────
    ("events",  "grid_id",                  "TEXT"),
    ("events",  "grid_type",                "TEXT"),
    ("events",  "aggregation_rule_version", "TEXT"),
    ("events",  "priority_rule_version",    "TEXT"),
]


def _data_migration(conn):
    """
    一次性資料遷移（冪等，全部使用 INSERT OR IGNORE / UPDATE WHERE NULL）。

    Step 1  h3_grid_summary → grid_summary（grid_type='h3'）
    Step 2  Backfill reports.grid_id / grid_type（H3 > district > city）
    Step 3  Build grid_summary for district / city grid types
    """
    # ── Step 1：舊 H3 表遷移 ─────────────────────────────────
    try:
        conn.execute("""
            INSERT OR IGNORE INTO grid_summary (
                grid_id, grid_type, h3_resolution,
                report_count, event_count, image_count,
                main_disaster_type,
                max_priority_score, max_priority_level,
                max_report_severity_score, estimated_people_need_help,
                latest_report_time, center_lat, center_lng, updated_at
            )
            SELECT
                h3_cell, 'h3', h3_resolution,
                report_count, event_count, image_count,
                main_disaster_type,
                max_priority_score, max_priority_level,
                max_report_severity_score, estimated_people_need_help,
                latest_report_time, center_lat, center_lng, updated_at
            FROM h3_grid_summary
            WHERE h3_cell IS NOT NULL AND h3_cell != ''
        """)
    except sqlite3.OperationalError:
        pass  # h3_grid_summary 不存在（全新安裝），略過

    # ── Step 2：Backfill reports.grid_id / grid_type ─────────
    # 優先 H3
    conn.execute("""
        UPDATE reports
        SET grid_id = h3_cell, grid_type = 'h3'
        WHERE (grid_id IS NULL OR grid_id = '')
          AND h3_cell IS NOT NULL AND h3_cell != ''
    """)
    # 次選 city + district
    conn.execute("""
        UPDATE reports
        SET grid_id = city || '_' || district, grid_type = 'district'
        WHERE (grid_id IS NULL OR grid_id = '')
          AND city     IS NOT NULL AND city     != ''
          AND district IS NOT NULL AND district != ''
    """)
    # 最後 city only
    conn.execute("""
        UPDATE reports
        SET grid_id = city, grid_type = 'city'
        WHERE (grid_id IS NULL OR grid_id = '')
          AND city IS NOT NULL AND city != ''
    """)

    # ── Step 3：為 district / city 建立 grid_summary 基礎記錄 ─
    # 先確保 need_review_count 欄位存在（老版本 schema 可能缺少）
    try:
        conn.execute("ALTER TABLE grid_summary ADD COLUMN need_review_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.execute("""
        INSERT OR IGNORE INTO grid_summary (
            grid_id, grid_type, h3_resolution,
            city, district,
            report_count, event_count, image_count,
            main_disaster_type,
            max_priority_score, max_priority_level,
            max_report_severity_score, estimated_people_need_help,
            need_review_count,
            latest_report_time,
            center_lat, center_lng, updated_at
        )
        SELECT
            r.grid_id,
            r.grid_type,
            NULL,
            MAX(r.city),
            MAX(r.district),
            COUNT(*),
            0,
            COUNT(*),
            (
                SELECT r2.disaster_type
                FROM reports r2
                WHERE r2.grid_id    = r.grid_id
                  AND r2.grid_type  = r.grid_type
                  AND r2.disaster_type IS NOT NULL
                GROUP BY r2.disaster_type
                ORDER BY COUNT(*) DESC
                LIMIT 1
            ),
            COALESCE(MAX(CAST(r.report_severity_score AS REAL)), 0),
            CASE
                WHEN MAX(CAST(r.report_severity_score AS REAL)) >= 70 THEN 'High'
                WHEN MAX(CAST(r.report_severity_score AS REAL)) >= 40 THEN 'Medium'
                ELSE 'Low'
            END,
            COALESCE(MAX(r.report_severity_score), 0),
            COALESCE(MAX(r.reported_people_count),  0),
            SUM(CASE WHEN r.need_review = 1 THEN 1 ELSE 0 END),
            MAX(r.upload_time),
            NULL,
            NULL,
            strftime('%Y-%m-%dT%H:%M:%S', 'now')
        FROM reports r
        WHERE r.grid_type IN ('district', 'city')
          AND r.grid_id IS NOT NULL AND r.grid_id != ''
        GROUP BY r.grid_id, r.grid_type
    """)


def init_db():
    """建立資料表並執行 column migration。"""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        for table, col, defn in _MIGRATIONS:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass  # 欄位已存在，略過
        _data_migration(conn)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
