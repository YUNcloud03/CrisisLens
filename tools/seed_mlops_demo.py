"""
產生 MLOps Dashboard 測試用假資料（可重複執行、可清除）。

標記方式（方便日後清除）：
  reports.submitted_by      = 'seed_demo'
  model_runs.notes  LIKE    '%SEED_DEMO%'
  admin_corrections.notes   = 'SEED_DEMO'

用法：
  python tools/seed_mlops_demo.py          # 插入假資料
  python tools/seed_mlops_demo.py --clean  # 只清除假資料
"""
import os
import sqlite3
import random
import argparse
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "crisislens.db")

CLASSES = [
    "Earthquake Damage", "Flood", "Fire",
    "Typhoon or Storm Damage", "Landslide",
]

CLIP_VER   = "clip-vitl14-v1"
PROMPT_VER = "multi-prompt-avg-5class-v2"
EFFNET_VER = "efficientnet-b0-medic-5class-v2"
AGG_VER    = "disaster-group-distance-timewindow-v4"
PRI_VER    = "svcp-weighted-v2"


def _clean(con):
    con.execute("DELETE FROM admin_corrections WHERE notes = 'SEED_DEMO'")
    con.execute("DELETE FROM model_runs WHERE notes LIKE '%SEED_DEMO%'")
    con.execute("DELETE FROM reports WHERE submitted_by = 'seed_demo'")
    con.commit()
    print("[clean] 已清除所有 seed_demo 假資料")


def _seed(con):
    random.seed(42)
    today = datetime(2026, 6, 13, 12, 0, 0)

    # 14 天：信心穩定維持高檔（無 drift → 綠燈）
    reports = []
    for day_offset in range(13, -1, -1):     # 13..0 → 共 14 天
        day = today - timedelta(days=day_offset)
        n_per_day = random.choice([1, 2])
        for _ in range(n_per_day):
            cls  = random.choice(CLASSES)
            conf = round(random.uniform(0.84, 0.96), 4)   # 穩定高信心
            ts   = (day + timedelta(hours=random.randint(0, 10),
                                    minutes=random.randint(0, 59))
                    ).isoformat(timespec="seconds")
            need_review   = int(conf < 0.50 or random.random() < 0.08)
            agreement     = int(random.random() > 0.08)
            severity      = random.randint(20, 85)
            sev_level     = "High" if severity >= 70 else "Medium" if severity >= 40 else "Low"
            reports.append((cls, conf, ts, need_review, agreement, severity, sev_level))

    # ── 插入 reports + 對應 model_runs ──
    report_ids = []
    for (cls, conf, ts, nr, agr, sev, sev_lv) in reports:
        cur = con.execute(
            """
            INSERT INTO reports (
                event_id, image_path, disaster_type, clip_disaster_type, clip_confidence,
                upload_time, event_time, need_review, model_agreement,
                report_severity_score, report_severity_level,
                clip_model_version, clip_prompt_version,
                resnet_model_version, resnet_disaster_type, resnet_confidence,
                city, district, description, submitted_by,
                aggregation_rule_version, priority_rule_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (None, "seed_demo_placeholder.jpg", cls, cls, conf, ts, ts, nr, agr, sev, sev_lv,
             CLIP_VER, PROMPT_VER, EFFNET_VER, cls, round(conf - 0.05, 4),
             "臺北市", "中正區", "（測試假資料）", "seed_demo",
             AGG_VER, PRI_VER),
        )
        rid = cur.lastrowid
        report_ids.append((rid, cls, ts))

        latency = round(random.uniform(320, 880), 1)
        con.execute(
            """
            INSERT INTO model_runs (
                run_time, trigger, clip_model_version, clip_prompt_version,
                resnet_model_version, aggregation_rule_version, priority_rule_version,
                report_id, notes, inference_latency_ms
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (ts, "submit", CLIP_VER, PROMPT_VER, EFFNET_VER, AGG_VER, PRI_VER,
             rid, "SEED_DEMO", latency),
        )

    # ── admin_corrections：16 筆，確定性 2 筆真修正（準確率 87.5%、R1 不觸發）──
    chosen = report_ids[:16] if len(report_ids) >= 16 else report_ids
    wrong_idx = {5, 12}                            # 這兩筆當作模型分錯、被管理員更正
    n_corr = 0
    for i, (rid, cls, ts) in enumerate(chosen):
        if i in wrong_idx:
            corrected = random.choice([c for c in CLASSES if c != cls])  # 真修正
        else:
            corrected = cls                       # 確認無誤 → predicted == ground_truth
        corrected_at = (datetime.fromisoformat(ts) + timedelta(hours=2)
                        ).isoformat(timespec="seconds")
        reason = "" if corrected == cls else "現場勘查後更正分類"
        con.execute(
            """
            INSERT INTO admin_corrections (
                corrected_at, corrected_by, report_id, event_id,
                field_name, original_value, corrected_value, correction_reason,
                used_for_retraining, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (corrected_at, "admin", rid, None,
             "disaster_type", cls, corrected, reason, 0, "SEED_DEMO"),
        )
        n_corr += 1

    con.commit()
    print(f"[seed] 已插入 {len(report_ids)} 筆 reports（含 model_runs）")
    print(f"[seed] 已插入 {n_corr} 筆 admin_corrections")
    print("[seed] 完成。重新整理 MLOps → 效能分析 即可看到 A–G 全區塊。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="只清除假資料，不插入")
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON")
    try:
        _clean(con)                # 先清舊 seed，確保可重複執行
        if not args.clean:
            _seed(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
