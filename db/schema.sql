-- =============================================================
-- CrisisLens Database Schema  v2
-- 5 張表：reports / events / grid_summary / model_runs / admin_corrections
-- =============================================================

-- ── Users / Permissions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    username                TEXT NOT NULL UNIQUE,
    password_hash           TEXT NOT NULL,
    role                    TEXT NOT NULL DEFAULT 'user',
    permission_status       TEXT NOT NULL DEFAULT 'none',
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL
);

-- ── Reports ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    report_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id               INTEGER REFERENCES events(event_id),

    image_path             TEXT NOT NULL,
    description            TEXT,
    location_name          TEXT,
    city                   TEXT,
    district               TEXT,

    -- 地點（GPS 優先 → 手動座標 → city+district）
    latitude               REAL,
    longitude              REAL,
    location_source        TEXT,           -- 'gps' | 'manual_gps' | 'district'
    h3_cell                TEXT,
    h3_resolution          INTEGER DEFAULT 9,
    grid_id                TEXT,           -- h3_cell | "{city}_{district}" | "{city}"
    grid_type              TEXT,           -- 'h3' | 'district' | 'city'

    event_time             TEXT,
    upload_time            TEXT NOT NULL,

    -- CLIP（主分類）
    clip_model_version     TEXT,
    clip_prompt_version    TEXT,
    clip_disaster_type     TEXT,
    clip_confidence        REAL,
    clip_top3              TEXT,           -- JSON（取代舊 top3_predictions）
    top3_predictions       TEXT,           -- 保留舊欄位向下相容

    -- ResNet50（輔助 / baseline）
    resnet_model_version   TEXT,
    resnet_disaster_type   TEXT,
    resnet_confidence      REAL,

    -- 最終決策
    disaster_type          TEXT,           -- 以 CLIP 為主
    model_agreement        INTEGER DEFAULT 1,   -- 1=一致, 0=不一致
    need_review            INTEGER DEFAULT 0,   -- 1=需人工審核

    need_help              INTEGER DEFAULT 0,
    reported_people_count  INTEGER DEFAULT 0,
    has_trapped_people     INTEGER DEFAULT 0,
    has_injured_people     INTEGER DEFAULT 0,
    road_blocked           INTEGER DEFAULT 0,

    report_severity_score  INTEGER DEFAULT 0,
    report_severity_level  TEXT,

    rag_version            TEXT,
    rag_advice             TEXT,
    rag_sources            TEXT,

    -- MLOps
    model_run_id           INTEGER REFERENCES model_runs(run_id),
    aggregation_rule_version TEXT,
    priority_rule_version  TEXT
);

-- ── Events ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name                  TEXT,
    location_name               TEXT,
    city                        TEXT,
    district                    TEXT,
    latitude                    REAL,
    longitude                   REAL,
    location_source             TEXT,
    h3_cell                     TEXT,
    h3_resolution               INTEGER DEFAULT 9,
    grid_id                     TEXT,
    grid_type                   TEXT,

    disaster_type               TEXT,
    first_report_time           TEXT,
    latest_report_time          TEXT,

    report_count                INTEGER DEFAULT 1,
    image_count                 INTEGER DEFAULT 1,

    max_report_severity_score   INTEGER DEFAULT 0,
    max_report_severity_level   TEXT,
    estimated_people_need_help  INTEGER DEFAULT 0,
    has_trapped_people          INTEGER DEFAULT 0,
    has_injured_people          INTEGER DEFAULT 0,
    road_blocked                INTEGER DEFAULT 0,

    event_priority_score        INTEGER DEFAULT 0,
    event_priority_level        TEXT,
    credibility_level           TEXT,

    aggregation_rule_version    TEXT,
    priority_rule_version       TEXT,

    status                      TEXT DEFAULT 'pending_review',
    created_at                  TEXT,
    updated_at                  TEXT
);

-- ── Grid Summary ──────────────────────────────────────────────
-- 三種格網類型，所有 Report 都能進熱圖
--   grid_type = 'h3'       → grid_id = h3_cell（有 lat/lng）
--   grid_type = 'district' → grid_id = "{city}_{district}"
--   grid_type = 'city'     → grid_id = "{city}"
CREATE TABLE IF NOT EXISTS grid_summary (
    grid_id                     TEXT NOT NULL,
    grid_type                   TEXT NOT NULL,

    h3_resolution               INTEGER,        -- 僅 h3 類型有值
    city                        TEXT,
    district                    TEXT,

    report_count                INTEGER DEFAULT 0,
    event_count                 INTEGER DEFAULT 0,
    image_count                 INTEGER DEFAULT 0,

    main_disaster_type          TEXT,
    max_priority_score          INTEGER DEFAULT 0,
    max_priority_level          TEXT,
    max_report_severity_score   INTEGER DEFAULT 0,
    estimated_people_need_help  INTEGER DEFAULT 0,
    need_review_count           INTEGER DEFAULT 0,

    latest_report_time          TEXT,
    center_lat                  REAL,
    center_lng                  REAL,
    updated_at                  TEXT,

    PRIMARY KEY (grid_id, grid_type)
);

-- ── 舊 h3_grid_summary（保留向下相容，不再寫入）────────────────
CREATE TABLE IF NOT EXISTS h3_grid_summary (
    h3_cell                    TEXT PRIMARY KEY,
    h3_resolution              INTEGER DEFAULT 9,
    report_count               INTEGER DEFAULT 0,
    event_count                INTEGER DEFAULT 0,
    image_count                INTEGER DEFAULT 0,
    main_disaster_type         TEXT,
    max_priority_score         INTEGER DEFAULT 0,
    max_priority_level         TEXT,
    max_report_severity_score  INTEGER DEFAULT 0,
    estimated_people_need_help INTEGER DEFAULT 0,
    latest_report_time         TEXT,
    center_lat                 REAL,
    center_lng                 REAL,
    updated_at                 TEXT
);

-- ── Model Runs ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_runs (
    run_id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_time                    TEXT NOT NULL,
    trigger                     TEXT,           -- 'submit' | 'batch' | 'retrain'

    clip_model_version          TEXT,
    clip_prompt_version         TEXT,
    resnet_model_version        TEXT,
    rag_index_version           TEXT,
    rag_prompt_version          TEXT,
    aggregation_rule_version    TEXT,
    priority_rule_version       TEXT,

    report_id                   INTEGER,        -- 事後回填
    notes                       TEXT
);

-- ── Admin Action Log ─────────────────────────────────────────
-- 記錄每一筆管理員操作（狀態變更、審核、優先級覆寫等）
CREATE TABLE IF NOT EXISTS admin_action_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at   TEXT    NOT NULL,
    admin_user  TEXT    NOT NULL,
    action      TEXT    NOT NULL,   -- 'status_change' | 'permission_approve' | 'priority_override' | ...
    target_type TEXT,               -- 'event' | 'report' | 'user'
    target_id   INTEGER,            -- event_id / report_id / user_id
    old_value   TEXT,               -- 變更前的值
    new_value   TEXT,               -- 變更後的值
    reason      TEXT,               -- 選填：操作原因
    extra       TEXT                -- JSON 額外資訊
);

-- ── Error Log ─────────────────────────────────────────────────
-- 持久化系統錯誤（模型推論失敗、API 逾時、DB 例外等）
CREATE TABLE IF NOT EXISTS error_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at   TEXT    NOT NULL,
    level       TEXT    NOT NULL DEFAULT 'ERROR',  -- 'WARNING' | 'ERROR' | 'CRITICAL'
    context     TEXT,       -- 'clip_classify' | 'geocoding' | 'rag_generate' | 'submit_report' | ...
    message     TEXT    NOT NULL,
    traceback   TEXT,       -- 完整 traceback（若有）
    username    TEXT,       -- 觸發動作的使用者（若有）
    extra       TEXT        -- JSON 額外資訊
);

-- ── Admin Corrections ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_corrections (
    correction_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    corrected_at                TEXT NOT NULL,
    corrected_by                TEXT DEFAULT 'admin',

    report_id                   INTEGER REFERENCES reports(report_id),
    event_id                    INTEGER REFERENCES events(event_id),

    field_name                  TEXT NOT NULL,
    -- 可選值：'disaster_type' | 'event_merge' | 'priority' | 'status' | 'location'
    original_value              TEXT,
    corrected_value             TEXT,
    correction_reason           TEXT,

    used_for_retraining         INTEGER DEFAULT 0,
    retraining_batch_id         TEXT,
    notes                       TEXT
);
