"""Shared Streamlit design system for CrisisLens pages."""
from __future__ import annotations

import html
import logging
import os
import warnings
from typing import Literal

import streamlit as st

# ── 壓制 transformers 棄用警告（所有頁面共用，冪等設定）────────
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=r".*__path__.*")
warnings.filterwarnings("ignore", message=r".*Accessing.*", module=r"transformers.*")
warnings.filterwarnings("ignore", category=FutureWarning, module=r"transformers.*")
warnings.filterwarnings("ignore", category=UserWarning,   module=r"transformers.*")
logging.getLogger("transformers").setLevel(logging.ERROR)
# ─────────────────────────────────────────────────────────────


RiskLevel = Literal["High", "Medium", "Low", "Verified", "pending_review", "verified", "closed"]


def apply_theme() -> None:
    """Apply a unified command-center theme without changing app logic."""
    st.markdown(
        """
<style>
:root {
    --cl-bg: #050a11;
    --cl-surface: #0b111a;
    --cl-surface-2: #101824;
    --cl-surface-3: #151f2d;
    --cl-border: rgba(148, 163, 184, 0.20);
    --cl-border-strong: rgba(125, 211, 252, 0.38);
    --cl-text: #f8fafc;
    --cl-muted: #b6c2d2;
    --cl-dim: #7f8da3;
    --cl-blue: #38bdf8;
    --cl-blue-soft: rgba(56, 189, 248, 0.12);
    --cl-green: #4ade80;
    --cl-yellow: #facc15;
    --cl-red: #fb7185;
    --cl-purple: #a78bfa;
}

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"] {
    background: var(--cl-bg) !important;
    color: var(--cl-text) !important;
}

[data-testid="stAppViewContainer"]::before {
    display: none !important;
}

[data-testid="stAppViewContainer"]::after {
    display: none !important;
}

.main .block-container,
.block-container,
[data-testid="block-container"],
[data-testid="stMainBlockContainer"] {
    position: relative;
    z-index: 1;
    max-width: 1440px;
    padding-top: 0 !important;
    margin-top: 0 !important;
    padding-bottom: 2rem !important;
}

section.main > div,
[data-testid="stMain"] > div {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

[data-testid="stSidebar"] {
    background: #060b12 !important;
    border-right: 1px solid var(--cl-border) !important;
    box-shadow: 10px 0 36px rgba(0, 0, 0, 0.32);
    visibility: visible !important;
    display: block !important;
    min-width: 17.5rem !important;
    max-width: 17.5rem !important;
    width: 17.5rem !important;
    transform: translateX(0) !important;
}

[data-testid="stSidebar"] * { color: var(--cl-text) !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--cl-muted) !important;
}

[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 17.5rem !important;
    max-width: 17.5rem !important;
    width: 17.5rem !important;
    margin-left: 0 !important;
    transform: translateX(0) !important;
}

[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

[data-testid="stSidebarContent"] {
    width: 17.5rem !important;
    padding-top: 0 !important;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 0.6rem !important;
}

[data-testid="stAppViewContainer"]:has(.cl-login-page) [data-testid="stSidebar"],
[data-testid="stAppViewContainer"]:has(.cl-login-page) [data-testid="stSidebarContent"],
[data-testid="stAppViewContainer"]:has(.cl-login-page) [data-testid="stSidebarNav"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
}

[data-testid="stAppViewContainer"]:has(.cl-login-page) .main .block-container {
    max-width: 1080px;
    padding-top: 0 !important;
    padding-left: 2rem;
    padding-right: 2rem;
}

[data-testid="stAppViewContainer"]:has(.cl-login-page) .cl-top-pill {
    margin-top: 0 !important;
    margin-bottom: 0.45rem;
}

[data-testid="stAppViewContainer"]:has(.cl-login-page) .cl-login-shell {
    margin-top: 0.35rem;
}

[data-testid="stSidebarNav"] {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[title="View fullscreen"],
button[title="Collapse sidebar"],
button[title="Expand sidebar"] {
    display: none !important;
}

h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] strong {
    color: var(--cl-text) !important;
    letter-spacing: 0 !important;
}

p, li, label, span, div {
    letter-spacing: 0 !important;
}

hr {
    border: 0 !important;
    height: 1px !important;
    margin: 0.85rem 0 1.05rem !important;
    background: var(--cl-border) !important;
}

/* Layout primitives */
.cl-page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1.5rem;
    margin: 0 0 0.55rem;
}

.cl-inline-header {
    margin: 0.25rem 0 0.9rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--cl-border);
}

.cl-inline-header .cl-title {
    font-size: clamp(2rem, 3.2vw, 3.15rem);
}

.cl-inline-header .cl-subtitle {
    max-width: none;
    margin-top: 0.55rem;
}

.cl-top-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.38rem 0.8rem;
    margin-top: 0 !important;
    margin-bottom: 0.55rem;
    border: 1px solid rgba(248, 250, 252, 0.42);
    border-radius: 999px;
    background: rgba(8, 13, 22, 0.82);
    color: var(--cl-text);
    font-size: 0.95rem;
    font-weight: 750;
    box-shadow: 0 10px 28px rgba(0,0,0,.26);
}

.cl-top-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.35rem;
    height: 1.35rem;
    border: 1px solid rgba(248,250,252,.42);
    border-radius: 999px;
    color: var(--cl-muted);
    font-size: 0.78rem;
}

.cl-login-shell {
    max-width: 460px;
    margin: 1.4rem auto 0;
    padding: 2.1rem 2.2rem;
    border: 1px solid rgba(56, 189, 248, 0.36);
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(14, 23, 35, 0.94), rgba(4, 9, 15, 0.94));
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.48);
    text-align: center;
}

.cl-logo-mark {
    width: 78px;
    height: 78px;
    margin: 0 auto 1rem;
    border-radius: 18px;
    background:
        linear-gradient(135deg, rgba(248,250,252,.95) 0 42%, transparent 42%),
        linear-gradient(135deg, transparent 0 54%, rgba(56,189,248,.95) 54% 68%, transparent 68%),
        linear-gradient(135deg, rgba(148,163,184,.95), rgba(15,23,42,.8));
    border: 1px solid rgba(125,211,252,.5);
    position: relative;
}

.cl-brand-logo {
    width: 46px;
    height: 46px;
    object-fit: contain;
    flex: 0 0 auto;
    border-radius: 10px;
    filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.25));
}

.cl-login-logo {
    width: 148px;
    height: 148px;
    object-fit: contain;
    margin: -0.35rem auto -1.1rem;
    display: block;
    filter: drop-shadow(0 0 18px rgba(56, 189, 248, 0.35));
}

.cl-logo-mark::after {
    content: "";
    position: absolute;
    right: 9px;
    top: 8px;
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: #67e8f9;
    box-shadow: 0 0 14px rgba(103,232,249,.85);
}

.cl-login-title {
    font-size: 1.85rem;
    line-height: 1.08;
    font-weight: 900;
    color: var(--cl-text);
}

.cl-login-subtitle {
    margin-top: 0.55rem;
    color: var(--cl-muted);
    font-size: 0.93rem;
}

.cl-login-divider {
    display: flex;
    align-items: center;
    gap: 1rem;
    color: var(--cl-dim);
    font-size: 0.82rem;
    margin: 1rem 0;
}

.cl-login-divider::before,
.cl-login-divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--cl-border);
}

.cl-citizen-grid {
    display: grid;
    grid-template-columns: minmax(360px, 1fr) minmax(360px, 0.95fr);
    gap: 1rem;
    align-items: stretch;
}

.cl-panel {
    min-height: 100%;
    padding: 1.05rem 1.15rem;
    border: 1px solid var(--cl-border);
    border-radius: 10px;
    background: rgba(10, 17, 27, 0.96);
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
}

.cl-panel-title {
    color: var(--cl-text);
    font-size: 1.05rem;
    font-weight: 900;
    margin-bottom: 0.95rem;
}

.cl-step-label {
    margin: 0.9rem 0 0.48rem;
    color: var(--cl-text);
    font-size: 0.88rem;
    font-weight: 800;
}

.cl-upload-preview {
    border: 1px solid var(--cl-border);
    border-radius: 8px;
    overflow: hidden;
    background: rgba(2, 6, 12, 0.62);
}

.cl-ai-result {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.9rem;
    margin: 0.65rem 0;
    border: 1px solid var(--cl-border);
    border-radius: 8px;
    background: rgba(8, 13, 22, 0.86);
}

.cl-ai-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 3.15rem;
    height: 3.15rem;
    border-radius: 999px;
    background: rgba(56,189,248,.22);
    color: var(--cl-blue);
    font-size: 1.45rem;
    flex: 0 0 auto;
}

.cl-advice-card {
    padding: 1.05rem;
    border: 1px solid var(--cl-border);
    border-radius: 10px;
    background: rgba(13, 21, 32, 0.88);
}

.cl-map-preview {
    min-height: 320px;
    border: 1px solid var(--cl-border);
    border-radius: 10px;
    background: #07111c;
    position: relative;
    overflow: hidden;
}

.cl-map-pin {
    position: absolute;
    left: 54%;
    top: 56%;
    width: 1.35rem;
    height: 1.35rem;
    transform: translate(-50%, -50%) rotate(45deg);
    border-radius: 50% 50% 50% 0;
    background: #2563eb;
    box-shadow: 0 0 0 0.75rem rgba(37, 99, 235, 0.12), 0 0 42px rgba(56, 189, 248, 0.45);
}

.cl-map-pin::after {
    content: "";
    position: absolute;
    inset: 0.39rem;
    border-radius: 999px;
    background: #bfdbfe;
}

.cl-map-label {
    position: absolute;
    right: 1rem;
    top: 1rem;
    padding: 0.38rem 0.65rem;
    border: 1px solid var(--cl-border);
    border-radius: 999px;
    background: rgba(5, 10, 17, 0.82);
    color: var(--cl-muted);
    font-size: 0.78rem;
    font-weight: 700;
}

.cl-map-preview::after {
    content: "";
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    color: var(--cl-muted);
    font-size: 0.8rem;
}

.cl-location-empty {
    min-height: 320px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    border: 1px dashed var(--cl-border);
    border-radius: 10px;
    background: #07111c;
    color: var(--cl-muted);
    text-align: center;
}

.cl-location-empty strong {
    color: var(--cl-text) !important;
    font-size: 1rem;
}

.cl-priority-rank {
    display: grid;
    grid-template-columns: 2rem 1fr auto;
    align-items: center;
    gap: 0.7rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.cl-priority-rank:last-child {
    border-bottom: 0;
}

.cl-kicker {
    color: var(--cl-blue);
    font-size: 0.74rem;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.cl-title {
    color: var(--cl-text);
    font-size: clamp(1.9rem, 3.5vw, 3rem);
    font-weight: 900;
    line-height: 1.08;
    margin: 0;
}

.cl-subtitle {
    color: var(--cl-muted);
    font-size: 0.96rem;
    margin-top: 0.62rem;
    max-width: 780px;
}

.cl-meta {
    color: var(--cl-muted);
    text-align: right;
    min-width: 150px;
    font-size: 0.8rem;
}

.cl-meta strong {
    display: block;
    color: var(--cl-text) !important;
    font-size: 1.05rem;
    margin-bottom: 0.2rem;
}

.cl-card,
.card,
.metric-card,
.event-row,
.report-card,
[data-testid="stExpander"],
[data-testid="stForm"] {
    background: rgba(10, 17, 27, 0.96) !important;
    border: 1px solid var(--cl-border) !important;
    border-radius: 8px !important;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.24);
    color: var(--cl-text) !important;
}

.cl-card,
.card,
.metric-card,
.report-card {
    padding: 1rem 1.1rem;
    margin-bottom: 0.85rem;
}

.cl-card:hover,
.card:hover,
.metric-card:hover,
.event-row:hover {
    border-color: var(--cl-border-strong) !important;
}

[data-testid="stExpander"] details > summary,
[data-testid="stExpander"] details > summary * {
    color: var(--cl-text) !important;
}

[data-testid="stExpander"] details[open] > summary,
[data-testid="stExpander"] details > summary:hover,
[data-testid="stExpander"] details > summary:focus,
[data-testid="stExpander"] details > summary:focus-visible {
    background: #e8eef7 !important;
    color: #06101a !important;
}

[data-testid="stExpander"] details[open] > summary *,
[data-testid="stExpander"] details > summary:hover *,
[data-testid="stExpander"] details > summary:focus *,
[data-testid="stExpander"] details > summary:focus-visible * {
    color: #06101a !important;
    fill: #06101a !important;
}

.cl-stat-label,
.metric-label,
.score-label {
    color: var(--cl-muted) !important;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
}

.cl-stat-value,
.metric-val,
.score-value {
    color: var(--cl-text) !important;
    font-size: 1.75rem;
    font-weight: 900;
    line-height: 1.1;
    margin-top: 0.25rem;
}

.cl-card-note,
.score-sub,
[data-testid="stCaptionContainer"],
.stMarkdown p {
    color: var(--cl-muted) !important;
}

.cl-section-title {
    color: var(--cl-text);
    font-size: 1.05rem;
    font-weight: 800;
    margin: 1.15rem 0 0.7rem;
}

.cl-empty-state {
    text-align: center;
    padding: 3.25rem 1.5rem;
    border: 1px dashed var(--cl-border);
    border-radius: 8px;
    background: rgba(11, 17, 26, 0.72);
}

.cl-empty-icon {
    color: var(--cl-blue);
    font-size: 2.5rem;
    margin-bottom: 0.8rem;
}

.cl-empty-title {
    color: var(--cl-text);
    font-size: 1.05rem;
    font-weight: 800;
}

.cl-empty-desc {
    color: var(--cl-muted);
    font-size: 0.88rem;
    margin-top: 0.35rem;
}

.cl-map-shell {
    overflow: hidden;
    border: 1px solid var(--cl-border);
    border-radius: 8px;
    background: #05070b;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.36);
}

/* Badges */
.badge,
.cl-badge,
.h3-badge,
.source-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border-radius: 999px !important;
    padding: 0.18rem 0.62rem;
    font-size: 0.72rem;
    font-weight: 800;
    white-space: nowrap;
}

.badge-high,
.cl-badge-high {
    background: rgba(251, 113, 133, 0.13);
    color: var(--cl-red);
    border: 1px solid rgba(251, 113, 133, 0.38);
}

.badge-medium,
.cl-badge-medium {
    background: rgba(250, 204, 21, 0.13);
    color: var(--cl-yellow);
    border: 1px solid rgba(250, 204, 21, 0.36);
}

.badge-low,
.cl-badge-low {
    background: rgba(74, 222, 128, 0.13);
    color: var(--cl-green);
    border: 1px solid rgba(74, 222, 128, 0.34);
}

.badge-blue,
.badge-verified,
.cl-badge-blue,
.cl-badge-verified {
    background: rgba(56, 189, 248, 0.13);
    color: var(--cl-blue);
    border: 1px solid rgba(56, 189, 248, 0.36);
}

.cl-badge-muted {
    background: rgba(148, 163, 184, 0.12);
    color: var(--cl-muted);
    border: 1px solid rgba(148, 163, 184, 0.24);
}

/* 事件狀態 badge */
.cl-badge-active {
    background: rgba(74, 222, 128, 0.13);
    color: #4ade80;
    border: 1px solid rgba(74, 222, 128, 0.36);
}
.cl-badge-resolved {
    background: rgba(56, 189, 248, 0.13);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.36);
}
.cl-badge-archived {
    background: rgba(100, 116, 139, 0.13);
    color: #64748b;
    border: 1px solid rgba(100, 116, 139, 0.28);
}

.risk-high { color: var(--cl-red) !important; }
.risk-medium { color: var(--cl-yellow) !important; }
.risk-low { color: var(--cl-green) !important; }

/* Forms */
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
[data-baseweb="select"] > div,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background: rgba(5, 9, 15, 0.92) !important;
    border: 1px solid var(--cl-border) !important;
    color: var(--cl-text) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

input::placeholder,
textarea::placeholder {
    color: #78869a !important;
}

[data-testid="InputInstructions"] {
    display: none !important;
}

div.stButton > button,
[data-testid="stFormSubmitButton"] button {
    background: #0ea5e9 !important;
    color: #ffffff !important;
    border: 1px solid rgba(125, 211, 252, 0.42) !important;
    border-radius: 8px !important;
    font-weight: 850 !important;
    box-shadow: none !important;
}

div.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background: #38bdf8 !important;
    color: #04111d !important;
}

[data-testid="stFileUploader"] {
    background: rgba(11, 17, 26, 0.82) !important;
    border: 1px dashed rgba(148, 163, 184, 0.34) !important;
    border-radius: 8px !important;
    padding: 0.85rem !important;
}

[data-testid="stAlert"] {
    background: rgba(16, 24, 36, 0.96) !important;
    border: 1px solid var(--cl-border) !important;
    color: var(--cl-text) !important;
}

.advice-item {
    background: rgba(56, 189, 248, 0.08) !important;
    border-left: 3px solid var(--cl-blue) !important;
    border-radius: 0 8px 8px 0 !important;
    color: var(--cl-text) !important;
    padding: 0.65rem 0.85rem !important;
    margin: 0.42rem 0 !important;
    line-height: 1.65;
}

.bar-bg {
    background: rgba(148, 163, 184, 0.16);
    border-radius: 999px;
    height: 8px;
    overflow: hidden;
}
.bar-high, .bar-medium, .bar-low, .bar-blue {
    height: 8px;
    border-radius: 999px;
}
.bar-high { background: var(--cl-red); }
.bar-medium { background: var(--cl-yellow); }
.bar-low { background: var(--cl-green); }
.bar-blue { background: var(--cl-blue); }

img { border-radius: 8px; }
#MainMenu, footer { visibility: hidden; }
header {
    display: none !important;
}

@media (max-width: 760px) {
    .cl-page-header {
        display: block;
    }
    .cl-meta {
        text-align: left;
        margin-top: 1rem;
    }
    .cl-citizen-grid {
        grid-template-columns: 1fr;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "", kicker: str = "CrisisLens", meta: str = "") -> None:
    """Render a consistent page header."""
    subtitle_html = f'<div class="cl-subtitle">{html.escape(subtitle)}</div>' if subtitle else ""
    meta_html = f'<div class="cl-meta">{meta}</div>' if meta else ""
    st.markdown(
        f"""
<section class="cl-page-header">
  <div>
    <div class="cl-kicker">{html.escape(kicker)}</div>
    <h1 class="cl-title">{html.escape(title)}</h1>
    {subtitle_html}
  </div>
  {meta_html}
</section>
<hr>
        """,
        unsafe_allow_html=True,
    )


def top_pill(index: int, title: str, subtitle: str = "") -> None:
    sub = f' <span style="color:var(--cl-dim);font-size:.82rem">/ {html.escape(subtitle)}</span>' if subtitle else ""
    st.markdown(
        f'<div class="cl-top-pill"><span class="cl-top-index">{index}</span>{html.escape(title)}{sub}</div>',
        unsafe_allow_html=True,
    )


def badge(label: str, level: str = "muted") -> str:
    """Return a shared badge HTML string."""
    normalized = {
        # 優先級 / 嚴重度
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        # 可信度
        "Verified": "verified",
        # 事件狀態（新名稱）
        "pending_review": "muted",
        "active":         "active",
        "resolved":       "resolved",
        "archived":       "archived",
        # 事件狀態（舊名稱，向下相容）
        "verified": "active",
        "closed":   "resolved",
    }.get(level, level.lower() if level else "muted")
    if normalized not in {"high", "medium", "low", "verified",
                          "active", "resolved", "archived", "blue", "muted"}:
        normalized = "muted"
    return f'<span class="cl-badge cl-badge-{normalized}">{html.escape(str(label))}</span>'


def stat_card(label: str, value: str | int, note: str = "", tone: str = "text") -> str:
    """Return a compact metric card."""
    colors = {
        "text": "var(--cl-text)",
        "blue": "var(--cl-blue)",
        "green": "var(--cl-green)",
        "yellow": "var(--cl-yellow)",
        "red": "var(--cl-red)",
        "purple": "var(--cl-purple)",
    }
    color = colors.get(tone, colors["text"])
    note_html = f'<div class="cl-card-note">{html.escape(note)}</div>' if note else ""
    return f"""
<div class="cl-card">
  <div class="cl-stat-label">{html.escape(label)}</div>
  <div class="cl-stat-value" style="color:{color}">{html.escape(str(value))}</div>
  {note_html}
</div>
"""


def empty_state(title: str, description: str = "", icon: str = "—") -> None:
    """Render a shared empty state."""
    st.markdown(
        f"""
<div class="cl-empty-state">
  <div class="cl-empty-icon">{html.escape(icon)}</div>
  <div class="cl-empty-title">{html.escape(title)}</div>
  <div class="cl-empty-desc">{html.escape(description)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )
