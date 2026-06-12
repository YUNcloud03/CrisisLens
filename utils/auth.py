"""Simple Streamlit auth helpers for CrisisLens."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import mimetypes
from pathlib import Path

import streamlit as st

from db.queries import (
    create_user,
    get_user,
    get_user_by_username,
    request_admin_permission,
)


def logo_data_uri() -> str:
    assets_dir = Path(__file__).resolve().parents[1] / "assets"
    logo_path = next(
        (path for path in (
            assets_dir / "logo.png",
            assets_dir / "logo.webp",
            assets_dir / "logo.jpg",
            assets_dir / "logo.jpeg",
            assets_dir / "logo.svg",
        ) if path.exists()),
        None,
    )
    if not logo_path:
        return ""
    mime_type = mimetypes.guess_type(str(logo_path))[0] or "image/png"
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, digest = stored_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(_hash_password(password, salt), stored_hash)


def current_user() -> dict | None:
    user_id = st.session_state.get("user_id")
    if not user_id:
        return None
    user = get_user(user_id)
    if not user:
        st.session_state.pop("user_id", None)
    return user


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("role") == "admin" and user.get("permission_status") == "approved")


def _account_labels(user: dict) -> tuple[str, str, str]:
    role = user.get("role")
    permission = user.get("permission_status")
    role_label = "管理員" if role == "admin" else "一般使用者"
    permission_label = {
        "approved": "已通過",
        "pending": "審核中",
        "rejected": "未通過",
        "none": "未申請",
    }.get(permission, "未申請")
    permission_tone = {
        "approved": "verified",
        "pending": "medium",
        "rejected": "high",
        "none": "muted",
    }.get(permission, "muted")
    return role_label, permission_label, permission_tone


def logout_button():
    if st.sidebar.button("登出", use_container_width=True):
        for key in (
            "user_id",
            "citizen_analysis",
            "report_latitude",
            "report_longitude",
            "latitude_input",
            "longitude_input",
            "gps_status",
            "gps_approved",
            "selected_event_id",
        ):
            st.session_state.pop(key, None)
        st.switch_page("app.py")


def render_sidebar_navigation(user: dict | None = None) -> None:
    """Render stable navigation so auth pages do not lose the sidebar."""
    admin = bool(user and user.get("role") == "admin" and user.get("permission_status") == "approved")
    logo_src = logo_data_uri()
    logo_html = (
        f'<img class="cl-brand-logo" src="{logo_src}" alt="CrisisLens logo">'
        if logo_src
        else '<div class="cl-brand-logo" style="display:flex;align-items:center;justify-content:center;background:rgba(56,189,248,.15);border:1px solid rgba(56,189,248,.3);font-weight:900">CL</div>'
    )
    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">
              {logo_html}
              <div>
                <div style="font-weight:800;font-size:1rem;color:#e2e8f0">CrisisLens</div>
                <div style="font-size:0.7rem;color:#7f8da3">災情分類與應變建議</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### 導覽")
        if admin:
            st.page_link("pages/2_Event_Dashboard.py", label="管理端總覽", icon="📊")
            st.page_link("pages/3_Event_Detail.py", label="事件詳細", icon="📍")
            st.page_link("pages/4_H3_Heatmap.py", label="H3 熱區地圖", icon="🗺️")
            st.page_link("pages/5_Permission_Review.py", label="權限審核", icon="🔐")
            st.page_link("pages/6_MLOps.py", label="MLOps 監控", icon="🔬")
            st.caption("目前登入為管理員，預設進入管理端。")
        elif user:
            st.page_link("app.py", label="民眾端回報", icon="🏠")
            st.caption("管理端功能需通過權限審核後才會開放。")
        else:
            st.page_link("app.py", label="登入 / 註冊", icon="🔑")
            st.caption("請先登入或註冊後使用平台。")


def render_login_page() -> None:
    """Render a centered login/register screen."""
    logo_src = logo_data_uri()
    logo_html = (
        f'<img class="cl-login-logo" src="{logo_src}" alt="CrisisLens logo">'
        if logo_src
        else '<div class="cl-logo-mark"></div>'
    )
    st.markdown(
        f"""
        <div class="cl-login-page"></div>
        <div class="cl-top-pill"><span class="cl-top-index">1</span>登入頁面 <span style="color:var(--cl-dim);font-size:.82rem">/ Login Page</span></div>
        <div class="cl-login-shell">
          {logo_html}
          <div class="cl-login-title">CrisisLens</div>
          <div class="cl-login-subtitle">災情分類與應變建議平台</div>
          <div class="cl-login-subtitle">AI 輔助災害辨識 · 事件聚合 · 風險排序 · 決策支援</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.05, 1])
    with center:
        tab_login, tab_register = st.tabs(["Email 登入", "註冊帳號"])
        with tab_login:
            username = st.text_input("帳號", key="login_username")
            password = st.text_input("密碼", type="password", key="login_password")
            if st.button("使用 Email 登入", use_container_width=True, key="login_submit"):
                found = get_user_by_username(username.strip())
                if found and _verify_password(password, found["password_hash"]):
                    for key in (
                        "citizen_analysis",
                        "report_latitude",
                        "report_longitude",
                        "latitude_input",
                        "longitude_input",
                        "gps_status",
                        "gps_approved",
                    ):
                        st.session_state.pop(key, None)
                    st.session_state["user_id"] = found["user_id"]
                    st.session_state["just_logged_in"] = True
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤。")

        with tab_register:
            new_username = st.text_input("帳號", key="register_username")
            new_password = st.text_input("密碼", type="password", key="register_password")
            confirm = st.text_input("確認密碼", type="password", key="register_confirm")
            if st.button("立即註冊", use_container_width=True, key="register_submit"):
                username_clean = new_username.strip()
                if len(username_clean) < 3:
                    st.error("帳號至少需要 3 個字元。")
                elif len(new_password) < 6:
                    st.error("密碼至少需要 6 個字元。")
                elif new_password != confirm:
                    st.error("兩次密碼不一致。")
                elif get_user_by_username(username_clean):
                    st.error("此帳號已存在。")
                else:
                    user_id = create_user(username_clean, _hash_password(new_password))
                    st.session_state["user_id"] = user_id
                    st.success("註冊成功。")
                    st.rerun()


def render_auth_panel() -> dict | None:
    """Render auth UI and return the current user."""
    user = current_user()

    if not user:
        render_login_page()
        return None

    render_sidebar_navigation(user)
    with st.sidebar:
        st.markdown("### 帳號")
        role_label, permission_label, permission_tone = _account_labels(user)
        st.markdown(
            f"""
            <div class="cl-card">
              <div class="cl-stat-label">目前登入</div>
              <div style="font-weight:900;margin-top:.25rem;font-size:1.05rem">{user['username']}</div>
              <div style="margin-top:.6rem;display:flex;flex-wrap:wrap;gap:.4rem">
                <span class="cl-badge cl-badge-blue">{role_label}</span>
                <span class="cl-badge cl-badge-{permission_tone}">{permission_label}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if user["role"] == "user":
            if user["permission_status"] == "none" or user["permission_status"] == "rejected":
                if st.button("申請管理員權限", use_container_width=True):
                    request_admin_permission(user["user_id"])
                    st.success("已送出申請，等待管理員審核。")
                    st.rerun()
            elif user["permission_status"] == "pending":
                st.info("管理員權限審核中。")
        logout_button()
    return user


def require_login() -> dict | None:
    user = render_auth_panel()
    if not user:
        st.info("請先註冊或登入後使用平台。")
        st.stop()
    return user


def require_admin() -> dict | None:
    user = render_auth_panel()
    if not user:
        st.info("請先登入。")
        st.stop()
    if not is_admin():
        # 非 admin 用戶自動跳回民眾端，不顯示錯誤頁
        st.switch_page("app.py")
    return user
