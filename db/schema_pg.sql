-- =============================================================
-- CrisisLens Database Schema  v2 — PostgreSQL
-- =============================================================

-- ── Users / Permissions ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id          SERIAL PRIMARY KEY,
    username         TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    role             TEXT NOT NULL DEFAULT 'user',
    permission_status TEXT NOT NULL DEFAULT 'none',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

-- ── Reports ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    report_id              SERIAL PRIMARY KEY,
    event_id               INTEGER REFERENCES events(event_id),
    image_path             TEXT NOT NULL,
    description            TEXT,
    location_name          TEXT,
    city                   TEXT,
    district               TEXT,
    latitude               DOUBLE PRECISION,
    longitude              DOUBLE PRECISION,
    location_source        TEXT,
    h3_cell                TEXT,
    h3_resolution          INTEGER DEFAULT 9,
    grid_id                TEXT,
    grid_type              TEXT,
    event_time             TEXT,
    upload_time            TEXT NOT NULL,
    clip_model_version     TEXT,
    clip_prompt_version    TEXT,
    clip_disaster_type     TEXT,
    clip_confidence        DOUBLE PRECISION,
    clip_top3              TEXT,
    top3_predictions       TEXT,
    resnet_model_version   TEXT,
    resnet_disaster_type   TEXT,
    resnet_confidence      DOUBLE PRECISION,
    disaster_type          TEXT,
    model_agreement        INTEGER DEFAULT 1,
    need_review            INTEGER DEFAULT 0,
    need_help              INTEGER DEFAULT 0,
    reported_people_count  INTEGER DEFAULT 0,
    has_trapped_people     INTEGER DEFAULT 0,
    has_injured_people     INTEGER DEFAULT 0,
    road_blocked           INTEGER DEFAULT 0,
    power_outage           INTEGER DEFAULT 0,
    report_severity_score  INTEGER DEFAULT 0,
    report_severity_level  TEXT,
    rag_version            TEXT,
    rag_advice             TEXT,
    rag_sources            TEXT,
    model_run_id           INTEGER,
    aggregation_rule_version TEXT,
    priority_rule_version  TEXT,
    clip_top2_gap          DOUBLE PRECISION
);

-- ── Events ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id                    SERIAL PRIMARY KEY,
    event_name                  TEXT,
    location_name               TEXT,
    city                        TEXT,
    district                    TEXT,
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
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
    power_outage                INTEGER DEFAULT 0,
    event_priority_score        INTEGER DEFAULT 0,
    event_priority_level        TEXT,
    vulnerability_score         INTEGER DEFAULT 0,
    credibility_score           INTEGER DEFAULT 0,
    credibility_level           TEXT,
    aggregation_rule_version    TEXT,
    priority_rule_version       TEXT,
    status                      TEXT DEFAULT 'pending_review',
    created_at                  TEXT,
    updated_at                  TEXT
);

-- ── Grid Summary ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grid_summary (
    grid_id                     TEXT NOT NULL,
    grid_type                   TEXT NOT NULL,
    h3_resolution               INTEGER,
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
    center_lat                  DOUBLE PRECISION,
    center_lng                  DOUBLE PRECISION,
    updated_at                  TEXT,
    PRIMARY KEY (grid_id, grid_type)
);

-- ── H3 Grid Summary（舊版，向下相容）─────────────────────────
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
    center_lat                 DOUBLE PRECISION,
    center_lng                 DOUBLE PRECISION,
    updated_at                 TEXT
);

-- ── Model Runs ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_runs (
    run_id                      SERIAL PRIMARY KEY,
    run_time                    TEXT NOT NULL,
    trigger                     TEXT,
    clip_model_version          TEXT,
    clip_prompt_version         TEXT,
    resnet_model_version        TEXT,
    rag_index_version           TEXT,
    rag_prompt_version          TEXT,
    aggregation_rule_version    TEXT,
    priority_rule_version       TEXT,
    report_id                   INTEGER,
    notes                       TEXT
);

-- ── Admin Action Log ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_action_logs (
    log_id      SERIAL PRIMARY KEY,
    logged_at   TEXT NOT NULL,
    admin_user  TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   INTEGER,
    old_value   TEXT,
    new_value   TEXT,
    reason      TEXT,
    extra       TEXT
);

-- ── Error Log ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS error_logs (
    log_id      SERIAL PRIMARY KEY,
    logged_at   TEXT NOT NULL,
    level       TEXT NOT NULL DEFAULT 'ERROR',
    context     TEXT,
    message     TEXT NOT NULL,
    traceback   TEXT,
    username    TEXT,
    extra       TEXT
);

-- ── Admin Corrections ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_corrections (
    correction_id               SERIAL PRIMARY KEY,
    corrected_at                TEXT NOT NULL,
    corrected_by                TEXT DEFAULT 'admin',
    report_id                   INTEGER REFERENCES reports(report_id),
    event_id                    INTEGER REFERENCES events(event_id),
    field_name                  TEXT NOT NULL,
    original_value              TEXT,
    corrected_value             TEXT,
    correction_reason           TEXT,
    used_for_retraining         INTEGER DEFAULT 0,
    retraining_batch_id         TEXT,
    notes                       TEXT
);
