"""Admin page — permission request review."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from db.database import init_db
from db.queries import (
    approve_admin_permission,
    get_pending_permission_requests,
    reject_admin_permission,
    log_admin_action,
)
from utils.auth import require_admin
from utils.ui_theme import apply_theme, empty_state, page_header, stat_card, top_pill

init_db()

st.set_page_config(page_title="權限審核｜CrisisLens", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
apply_theme()
admin = require_admin()

top_pill(5, "權限申請", "Permission Request")
page_header(
    "權限申請審核",
    "審核一般使用者提出的管理員權限申請，通過後才能查看事件列表、案件排序與 H3 熱區。",
    "Permission Review",
    f"<strong>{datetime.now().strftime('%H:%M:%S')}</strong>{admin['username']}",
)

requests = get_pending_permission_requests()

c1, c2 = st.columns(2)
with c1:
    st.markdown(stat_card("待審核申請", len(requests), "permission_status = pending", "yellow"), unsafe_allow_html=True)
with c2:
    st.markdown(stat_card("審核後權限", "admin", "role = admin · permission_status = approved", "blue"), unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

if not requests:
    empty_state("目前沒有待審核申請", "一般使用者可在登入後於側欄申請管理員權限。", "🛡️")
    st.stop()

for req in requests:
    with st.container():
        st.markdown(
            f"""
            <div class="cl-card">
              <div class="cl-stat-label">申請者</div>
              <div style="font-weight:900;font-size:1.15rem;margin-top:.25rem">{req['username']}</div>
              <div class="cl-card-note">
                user_id={req['user_id']} · role={req['role']} · permission_status={req['permission_status']} · updated_at={req.get('updated_at') or '—'}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        a1, a2, _ = st.columns([1, 1, 4])
        with a1:
            if st.button("通過", key=f"approve_{req['user_id']}", use_container_width=True):
                approve_admin_permission(req["user_id"])
                log_admin_action(
                    admin_user=admin["username"],
                    action="permission_approve",
                    target_type="user",
                    target_id=req["user_id"],
                    old_value="pending",
                    new_value="approved",
                    extra={"username": req["username"]},
                )
                st.success(f"已核准 {req['username']} 成為管理員。")
                st.rerun()
        with a2:
            if st.button("拒絕", key=f"reject_{req['user_id']}", use_container_width=True):
                reject_admin_permission(req["user_id"])
                log_admin_action(
                    admin_user=admin["username"],
                    action="permission_reject",
                    target_type="user",
                    target_id=req["user_id"],
                    old_value="pending",
                    new_value="rejected",
                    extra={"username": req["username"]},
                )
                st.warning(f"已拒絕 {req['username']} 的申請。")
                st.rerun()
