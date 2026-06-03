"""所有 SQL 查詢的封裝層。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime
from db.database import get_conn


# ═══════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════

def insert_report(data: dict) -> int:
    sql = """
    INSERT INTO reports (
        event_id, image_path, description, location_name,
        city, district, latitude, longitude,
        location_source, h3_cell, h3_resolution,
        grid_id, grid_type,
        event_time, upload_time,
        clip_model_version, clip_prompt_version,
        clip_disaster_type, clip_confidence, clip_top2_gap, clip_top3, top3_predictions,
        resnet_model_version, resnet_disaster_type, resnet_confidence,
        disaster_type, model_agreement, need_review,
        need_help, reported_people_count,
        has_trapped_people, has_injured_people, road_blocked,
        report_severity_score, report_severity_level,
        rag_version, rag_advice, rag_sources,
        model_run_id, aggregation_rule_version, priority_rule_version
    ) VALUES (
        :event_id, :image_path, :description, :location_name,
        :city, :district, :latitude, :longitude,
        :location_source, :h3_cell, :h3_resolution,
        :grid_id, :grid_type,
        :event_time, :upload_time,
        :clip_model_version, :clip_prompt_version,
        :clip_disaster_type, :clip_confidence, :clip_top2_gap, :clip_top3, :top3_predictions,
        :resnet_model_version, :resnet_disaster_type, :resnet_confidence,
        :disaster_type, :model_agreement, :need_review,
        :need_help, :reported_people_count,
        :has_trapped_people, :has_injured_people, :road_blocked,
        :report_severity_score, :report_severity_level,
        :rag_version, :rag_advice, :rag_sources,
        :model_run_id, :aggregation_rule_version, :priority_rule_version
    )
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def update_report_event(report_id: int, event_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE reports SET event_id=? WHERE report_id=?",
            (event_id, report_id)
        )


def get_reports_by_event(event_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM reports
            WHERE event_id=?
            ORDER BY report_severity_score DESC, upload_time DESC
        """, (event_id,)).fetchall()
    return [dict(r) for r in rows]


def get_all_reports() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY upload_time DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_reports_by_h3_cell(h3_cell: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reports WHERE h3_cell=? ORDER BY upload_time DESC",
            (h3_cell,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_reports_by_grid(grid_id: str, grid_type: str) -> list[dict]:
    """取得指定 grid_id + grid_type 的所有 reports。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reports WHERE grid_id=? AND grid_type=? ORDER BY upload_time DESC",
            (grid_id, grid_type)
        ).fetchall()
    return [dict(r) for r in rows]


def get_need_review_reports() -> list[dict]:
    """取得所有需人工審核的 reports。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reports WHERE need_review=1 ORDER BY upload_time DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# Events
# ═══════════════════════════════════════════════════════════

def insert_event(data: dict) -> int:
    sql = """
    INSERT INTO events (
        event_name, location_name, city, district,
        latitude, longitude, location_source,
        h3_cell, h3_resolution, grid_id, grid_type,
        disaster_type, first_report_time, latest_report_time,
        report_count, image_count,
        max_report_severity_score, max_report_severity_level,
        estimated_people_need_help,
        has_trapped_people, has_injured_people, road_blocked,
        event_priority_score, event_priority_level,
        credibility_level,
        aggregation_rule_version, priority_rule_version,
        status, created_at, updated_at
    ) VALUES (
        :event_name, :location_name, :city, :district,
        :latitude, :longitude, :location_source,
        :h3_cell, :h3_resolution, :grid_id, :grid_type,
        :disaster_type, :first_report_time, :latest_report_time,
        :report_count, :image_count,
        :max_report_severity_score, :max_report_severity_level,
        :estimated_people_need_help,
        :has_trapped_people, :has_injured_people, :road_blocked,
        :event_priority_score, :event_priority_level,
        :credibility_level,
        :aggregation_rule_version, :priority_rule_version,
        :status, :created_at, :updated_at
    )
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def update_event_summary(event_id: int, data: dict):
    sql = """
    UPDATE events SET
        report_count                = :report_count,
        image_count                 = :image_count,
        latest_report_time          = :latest_report_time,
        max_report_severity_score   = :max_report_severity_score,
        max_report_severity_level   = :max_report_severity_level,
        estimated_people_need_help  = :estimated_people_need_help,
        has_trapped_people          = :has_trapped_people,
        has_injured_people          = :has_injured_people,
        road_blocked                = :road_blocked,
        event_priority_score        = :event_priority_score,
        event_priority_level        = :event_priority_level,
        credibility_level           = :credibility_level,
        updated_at                  = :updated_at
    WHERE event_id = :event_id
    """
    data["event_id"] = event_id
    with get_conn() as conn:
        conn.execute(sql, data)


def get_event(event_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
    return dict(row) if row else None


def get_all_events(
    disaster_type: str = None,
    city: str = None,
    priority_level: str = None,
    status: str = None,
) -> list[dict]:
    sql    = "SELECT * FROM events WHERE 1=1"
    params = []
    if disaster_type:  sql += " AND disaster_type=?";          params.append(disaster_type)
    if city:           sql += " AND city=?";                   params.append(city)
    if priority_level: sql += " AND event_priority_level=?";   params.append(priority_level)
    if status:         sql += " AND status=?";                 params.append(status)
    sql += " ORDER BY event_priority_score DESC, latest_report_time DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_candidate_events(disaster_type: str, event_time: str, hours: float = 2.0) -> list[dict]:
    sql = """
    SELECT * FROM events
    WHERE disaster_type = ?
      AND ABS((julianday(latest_report_time) - julianday(?)) * 24) <= ?
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (disaster_type, event_time, hours)).fetchall()
    return [dict(r) for r in rows]


def update_event_status(event_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE events SET status=?, updated_at=? WHERE event_id=?",
            (status, datetime.now().isoformat(), event_id)
        )


# ═══════════════════════════════════════════════════════════
# Grid Summary（支援 h3 / district / city 三種格網）
# ═══════════════════════════════════════════════════════════

def upsert_grid_summary(data: dict):
    """插入或更新 grid_summary（PRIMARY KEY = grid_id + grid_type）。"""
    sql = """
    INSERT INTO grid_summary (
        grid_id, grid_type, h3_resolution,
        city, district,
        report_count, event_count, image_count,
        main_disaster_type,
        max_priority_score, max_priority_level,
        max_report_severity_score, estimated_people_need_help,
        need_review_count,
        latest_report_time,
        center_lat, center_lng, updated_at
    ) VALUES (
        :grid_id, :grid_type, :h3_resolution,
        :city, :district,
        :report_count, :event_count, :image_count,
        :main_disaster_type,
        :max_priority_score, :max_priority_level,
        :max_report_severity_score, :estimated_people_need_help,
        :need_review_count,
        :latest_report_time,
        :center_lat, :center_lng, :updated_at
    )
    ON CONFLICT(grid_id, grid_type) DO UPDATE SET
        h3_resolution              = excluded.h3_resolution,
        city                       = excluded.city,
        district                   = excluded.district,
        report_count               = excluded.report_count,
        event_count                = excluded.event_count,
        image_count                = excluded.image_count,
        main_disaster_type         = excluded.main_disaster_type,
        max_priority_score         = excluded.max_priority_score,
        max_priority_level         = excluded.max_priority_level,
        max_report_severity_score  = excluded.max_report_severity_score,
        estimated_people_need_help = excluded.estimated_people_need_help,
        need_review_count          = excluded.need_review_count,
        latest_report_time         = excluded.latest_report_time,
        center_lat                 = excluded.center_lat,
        center_lng                 = excluded.center_lng,
        updated_at                 = excluded.updated_at
    """
    with get_conn() as conn:
        conn.execute(sql, data)


def get_grid_summaries(grid_type: str = None) -> list[dict]:
    """取得 grid_summary，可依 grid_type 篩選（None = 全部）。"""
    sql    = "SELECT * FROM grid_summary WHERE 1=1"
    params = []
    if grid_type:
        sql += " AND grid_type=?"
        params.append(grid_type)
    sql += " ORDER BY max_priority_score DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_grid_summary(grid_id: str, grid_type: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM grid_summary WHERE grid_id=? AND grid_type=?",
            (grid_id, grid_type)
        ).fetchone()
    return dict(row) if row else None


# ── 向下相容：舊的 h3_grid_summary 函式 ──────────────────────
def upsert_h3_summary(data: dict):
    """舊版介面，仍寫入 h3_grid_summary（已不建議使用，改用 upsert_grid_summary）。"""
    sql = """
    INSERT INTO h3_grid_summary (
        h3_cell, h3_resolution,
        report_count, event_count, image_count,
        main_disaster_type, max_priority_score, max_priority_level,
        max_report_severity_score, estimated_people_need_help,
        latest_report_time, center_lat, center_lng, updated_at
    ) VALUES (
        :h3_cell, :h3_resolution,
        :report_count, :event_count, :image_count,
        :main_disaster_type, :max_priority_score, :max_priority_level,
        :max_report_severity_score, :estimated_people_need_help,
        :latest_report_time, :center_lat, :center_lng, :updated_at
    )
    ON CONFLICT(h3_cell) DO UPDATE SET
        report_count               = excluded.report_count,
        event_count                = excluded.event_count,
        image_count                = excluded.image_count,
        main_disaster_type         = excluded.main_disaster_type,
        max_priority_score         = excluded.max_priority_score,
        max_priority_level         = excluded.max_priority_level,
        max_report_severity_score  = excluded.max_report_severity_score,
        estimated_people_need_help = excluded.estimated_people_need_help,
        latest_report_time         = excluded.latest_report_time,
        center_lat                 = excluded.center_lat,
        center_lng                 = excluded.center_lng,
        updated_at                 = excluded.updated_at
    """
    with get_conn() as conn:
        conn.execute(sql, data)


def get_all_h3_summaries() -> list[dict]:
    """向下相容：從新的 grid_summary 讀取 h3 類型。"""
    return get_grid_summaries(grid_type="h3")


def get_h3_summary(h3_cell: str) -> dict | None:
    return get_grid_summary(h3_cell, "h3")


# ═══════════════════════════════════════════════════════════
# Model Runs（MLOps 版本追蹤）
# ═══════════════════════════════════════════════════════════

def insert_model_run(data: dict) -> int:
    sql = """
    INSERT INTO model_runs (
        run_time, trigger,
        clip_model_version, clip_prompt_version,
        resnet_model_version,
        rag_index_version, rag_prompt_version,
        aggregation_rule_version, priority_rule_version,
        report_id, notes
    ) VALUES (
        :run_time, :trigger,
        :clip_model_version, :clip_prompt_version,
        :resnet_model_version,
        :rag_index_version, :rag_prompt_version,
        :aggregation_rule_version, :priority_rule_version,
        :report_id, :notes
    )
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def update_model_run_report(run_id: int, report_id: int):
    """回填 model_run 的 report_id（submit 後才知道）。"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE model_runs SET report_id=? WHERE run_id=?",
            (report_id, run_id)
        )


def get_model_runs(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM model_runs ORDER BY run_id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# Admin Corrections（人工修正 / MLOps retraining）
# ═══════════════════════════════════════════════════════════

def insert_admin_correction(data: dict) -> int:
    sql = """
    INSERT INTO admin_corrections (
        corrected_at, corrected_by,
        report_id, event_id,
        field_name, original_value, corrected_value, correction_reason,
        used_for_retraining, retraining_batch_id, notes
    ) VALUES (
        :corrected_at, :corrected_by,
        :report_id, :event_id,
        :field_name, :original_value, :corrected_value, :correction_reason,
        :used_for_retraining, :retraining_batch_id, :notes
    )
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def get_admin_corrections(
    report_id: int = None,
    event_id: int = None,
    used_for_retraining: int = None,
) -> list[dict]:
    sql    = "SELECT * FROM admin_corrections WHERE 1=1"
    params = []
    if report_id is not None:
        sql += " AND report_id=?";          params.append(report_id)
    if event_id is not None:
        sql += " AND event_id=?";           params.append(event_id)
    if used_for_retraining is not None:
        sql += " AND used_for_retraining=?"; params.append(used_for_retraining)
    sql += " ORDER BY corrected_at DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def mark_correction_for_retraining(correction_id: int, batch_id: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE admin_corrections SET used_for_retraining=1, retraining_batch_id=? WHERE correction_id=?",
            (batch_id, correction_id)
        )
