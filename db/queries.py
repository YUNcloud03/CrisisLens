"""所有 SQL 查詢的封裝層。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime
from db.database import get_conn


# ═══════════════════════════════════════════════════════════
# Users / Permissions
# ═══════════════════════════════════════════════════════════

def create_user(username: str, password_hash: str) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (
                username, password_hash, role, permission_status, created_at, updated_at
            ) VALUES (?, ?, 'user', 'none', ?, ?)
            RETURNING user_id
            """,
            (username, password_hash, now, now),
        )
        return cur.fetchone()["user_id"]


def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,),
        ).fetchone()
    return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def request_admin_permission(user_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET permission_status='pending', updated_at=?
            WHERE user_id=? AND role='user' AND permission_status IN ('none', 'rejected')
            """,
            (now, user_id),
        )


def get_pending_permission_requests() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM users
            WHERE permission_status='pending'
            ORDER BY updated_at ASC, user_id ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def approve_admin_permission(user_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET role='admin', permission_status='approved', updated_at=?
            WHERE user_id=?
            """,
            (now, user_id),
        )


def reject_admin_permission(user_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET role='user', permission_status='rejected', updated_at=?
            WHERE user_id=?
            """,
            (now, user_id),
        )


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
        clip_disaster_type, clip_confidence, clip_top3, top3_predictions,
        resnet_model_version, resnet_disaster_type, resnet_confidence,
        disaster_type, model_agreement, need_review,
        need_help, reported_people_count,
        has_trapped_people, has_injured_people, road_blocked, power_outage,
        report_severity_score, report_severity_level,
        rag_version, rag_advice, rag_sources,
        model_run_id, aggregation_rule_version, priority_rule_version,
        input_safety_label, output_safety_label, safety_reason,
        submitted_by
    ) VALUES (
        :event_id, :image_path, :description, :location_name,
        :city, :district, :latitude, :longitude,
        :location_source, :h3_cell, :h3_resolution,
        :grid_id, :grid_type,
        :event_time, :upload_time,
        :clip_model_version, :clip_prompt_version,
        :clip_disaster_type, :clip_confidence, :clip_top3, :top3_predictions,
        :resnet_model_version, :resnet_disaster_type, :resnet_confidence,
        :disaster_type, :model_agreement, :need_review,
        :need_help, :reported_people_count,
        :has_trapped_people, :has_injured_people, :road_blocked, :power_outage,
        :report_severity_score, :report_severity_level,
        :rag_version, :rag_advice, :rag_sources,
        :model_run_id, :aggregation_rule_version, :priority_rule_version,
        :input_safety_label, :output_safety_label, :safety_reason,
        :submitted_by
    )
    RETURNING report_id
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.fetchone()["report_id"]


def update_report_event(report_id: int, event_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE reports SET event_id=? WHERE report_id=?",
            (event_id, report_id)
        )


def update_report_disaster_type(report_id: int, disaster_type: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE reports SET disaster_type=? WHERE report_id=?",
            (disaster_type, report_id)
        )


def update_event_disaster_type(event_id: int, disaster_type: str, event_name: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE events SET disaster_type=?, event_name=? WHERE event_id=?",
            (disaster_type, event_name, event_id)
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


def get_event_ids_with_need_review() -> set:
    """回傳含有待審核回報的事件 ID 集合（用於 Dashboard 篩選）。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT event_id FROM reports WHERE need_review=1 AND event_id IS NOT NULL"
        ).fetchall()
    return {r["event_id"] for r in rows}


def count_recent_reports_by_user(username: str, minutes: int = 60) -> int:
    """
    計算指定使用者在最近 minutes 分鐘內送出的回報數（速率限制用）。
    使用 reports.submitted_by 欄位；舊回報若此欄為空則不計入。
    """
    from datetime import datetime as _dt, timedelta as _td
    cutoff = (_dt.now() - _td(minutes=minutes)).isoformat(timespec="seconds")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM reports WHERE submitted_by=? AND upload_time >= ?",
            (username, cutoff),
        ).fetchone()
    return dict(row)["c"] if row else 0


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
        has_trapped_people, has_injured_people, road_blocked, power_outage,
        event_priority_score, event_priority_level,
        vulnerability_score, credibility_score, credibility_level,
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
        :has_trapped_people, :has_injured_people, :road_blocked, :power_outage,
        :event_priority_score, :event_priority_level,
        :vulnerability_score, :credibility_score, :credibility_level,
        :aggregation_rule_version, :priority_rule_version,
        :status, :created_at, :updated_at
    )
    RETURNING event_id
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.fetchone()["event_id"]


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
        power_outage                = :power_outage,
        event_priority_score        = :event_priority_score,
        event_priority_level        = :event_priority_level,
        vulnerability_score         = :vulnerability_score,
        credibility_score           = :credibility_score,
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
    """
    取相同災害類型、時間差在 hours 小時內的事件。
    在 Python 層做時間過濾，避免 julianday（SQLite）/ EXTRACT（PostgreSQL）的方言差異。
    """
    from datetime import datetime as _dt

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE disaster_type = ?",
            (disaster_type,)
        ).fetchall()

    results = []
    try:
        ref_dt = _dt.fromisoformat(event_time.replace(" ", "T"))
    except (ValueError, AttributeError):
        return [dict(r) for r in rows]   # 無法解析時間，回傳全部

    for r in rows:
        ev = dict(r)
        try:
            ev_dt = _dt.fromisoformat((ev.get("latest_report_time") or "").replace(" ", "T"))
            if abs((ref_dt - ev_dt).total_seconds()) / 3600 <= hours:
                results.append(ev)
        except (ValueError, AttributeError):
            results.append(ev)   # 無法解析，保守保留
    return results


def update_event_status(event_id: int, status: str,
                        admin_user: str = "admin", reason: str = None):
    """
    更新事件狀態，並自動寫入 admin_action_logs。
    """
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        # 取舊狀態
        row = conn.execute(
            "SELECT status FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        old_status = row["status"] if row else None

        # 更新狀態
        conn.execute(
            "UPDATE events SET status=?, updated_at=? WHERE event_id=?",
            (status, now, event_id)
        )
        # 寫 admin_action_logs
        conn.execute(
            """
            INSERT INTO admin_action_logs
                (logged_at, admin_user, action, target_type, target_id,
                 old_value, new_value, reason)
            VALUES (?, ?, 'status_change', 'event', ?, ?, ?, ?)
            """,
            (now, admin_user, event_id, old_status, status, reason),
        )


# ── Admin Action Log ──────────────────────────────────────────
def log_admin_action(admin_user: str, action: str,
                     target_type: str = None, target_id: int = None,
                     old_value: str = None, new_value: str = None,
                     reason: str = None, extra: dict = None):
    """
    通用管理員操作記錄（status_change 以外的動作）。

    Parameters
    ----------
    action      : 'permission_approve' | 'permission_reject' | 'priority_override' | ...
    target_type : 'event' | 'report' | 'user'
    target_id   : 對應 ID
    """
    import json as _json
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO admin_action_logs
                (logged_at, admin_user, action, target_type, target_id,
                 old_value, new_value, reason, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now, admin_user, action, target_type, target_id,
                old_value, new_value, reason,
                _json.dumps(extra, ensure_ascii=False) if extra else None,
            ),
        )


def get_admin_action_logs(limit: int = 100, target_type: str = None,
                          target_id: int = None) -> list[dict]:
    """取最近的管理員操作記錄。"""
    sql    = "SELECT * FROM admin_action_logs WHERE 1=1"
    params = []
    if target_type:
        sql += " AND target_type=?"
        params.append(target_type)
    if target_id is not None:
        sql += " AND target_id=?"
        params.append(target_id)
    sql += " ORDER BY log_id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ── Error Log ─────────────────────────────────────────────────
def get_error_logs(level: str = None, context: str = None,
                   limit: int = 100) -> list[dict]:
    """取最近的錯誤記錄。"""
    sql    = "SELECT * FROM error_logs WHERE 1=1"
    params = []
    if level:
        sql += " AND level=?"
        params.append(level)
    if context:
        sql += " AND context LIKE ?"
        params.append(f"%{context}%")
    sql += " ORDER BY log_id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


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


def get_grid_summaries(grid_type: str = None, active_only: bool = False) -> list[dict]:
    """
    取得 grid_summary，可依 grid_type 篩選（None = 全部）。

    Parameters
    ----------
    grid_type   : 'h3' | 'district' | 'city' | None（全部）
    active_only : True → 只回傳至少有一個非 closed 事件的格網
                  False → 回傳全部（預設，向下相容）
    """
    if active_only:
        # 只取「至少有一個非 closed 事件」的格網
        # closed 狀態集合：closed / resolved / archived（向後相容）
        base = """
            SELECT gs.*
            FROM grid_summary gs
            WHERE 1=1
        """
        filter_closed = """
            AND EXISTS (
                SELECT 1
                FROM events e
                INNER JOIN reports r ON r.event_id = e.event_id
                WHERE r.grid_id   = gs.grid_id
                  AND r.grid_type = gs.grid_type
                  AND (e.status IS NULL
                       OR e.status NOT IN ('closed', 'resolved', 'archived'))
                  -- 'closed'/'verified' 為舊欄位名稱，DB migration 後可移除
            )
        """
        sql    = base + filter_closed
        params = []
    else:
        sql    = "SELECT * FROM grid_summary WHERE 1=1"
        params = []

    if grid_type:
        sql += " AND gs.grid_type=?" if active_only else " AND grid_type=?"
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
        report_id, notes, inference_latency_ms
    ) VALUES (
        :run_time, :trigger,
        :clip_model_version, :clip_prompt_version,
        :resnet_model_version,
        :rag_index_version, :rag_prompt_version,
        :aggregation_rule_version, :priority_rule_version,
        :report_id, :notes, :inference_latency_ms
    )
    RETURNING run_id
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.fetchone()["run_id"]


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
    RETURNING correction_id
    """
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.fetchone()["correction_id"]


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


def get_correction_accuracy_stats() -> list[dict]:
    """回傳所有 disaster_type 修正記錄，含原始預測與 ground truth，供計算線上準確率。"""
    sql = """
    SELECT
        r.disaster_type        AS predicted,
        ac.corrected_value     AS ground_truth,
        r.clip_confidence,
        r.model_agreement,
        ac.corrected_at
    FROM admin_corrections ac
    JOIN reports r ON ac.report_id = r.report_id
    WHERE ac.field_name = 'disaster_type'
    ORDER BY ac.corrected_at DESC
    """
    with get_conn() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def get_daily_confidence_stats(days: int = 14) -> list[dict]:
    """回傳最近 N 天每日平均信心與 need_review 率，供 drift 偵測使用。"""
    sql = """
    SELECT
        DATE(upload_time)    AS day,
        COUNT(*)             AS n,
        AVG(clip_confidence) AS avg_conf,
        AVG(need_review)     AS review_rate
    FROM reports
    WHERE upload_time >= DATE('now', ?)
    GROUP BY DATE(upload_time)
    ORDER BY day
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


def get_confidence_distribution(limit: int = 200) -> list[dict]:
    """回傳最近 N 筆推論的信心分佈資料，供趨勢圖使用。"""
    sql = """
    SELECT clip_confidence, model_agreement, need_review, disaster_type, upload_time
    FROM reports
    ORDER BY upload_time DESC
    LIMIT ?
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]
