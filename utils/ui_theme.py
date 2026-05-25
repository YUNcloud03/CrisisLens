"""Shared Streamlit visual theme for CrisisLens pages."""
import streamlit as st


def apply_theme() -> None:
    """Apply a black, high-contrast dashboard theme without changing app logic."""
    st.markdown(
        """
<style>
:root {
    --cl-bg: #020409;
    --cl-panel: rgba(7, 14, 25, 0.88);
    --cl-panel-strong: rgba(10, 20, 35, 0.96);
    --cl-border: rgba(83, 166, 219, 0.26);
    --cl-border-hot: rgba(56, 189, 248, 0.55);
    --cl-text: #f8fafc;
    --cl-muted: #a8b3c7;
    --cl-dim: #68758c;
    --cl-blue: #38bdf8;
    --cl-cyan: #67e8f9;
    --cl-green: #4ade80;
    --cl-yellow: #fbbf24;
    --cl-red: #f87171;
}

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 76% 6%, rgba(56, 189, 248, 0.16), transparent 28rem),
        radial-gradient(circle at 8% 76%, rgba(14, 165, 233, 0.12), transparent 22rem),
        linear-gradient(180deg, #020409 0%, #030711 48%, #010205 100%) !important;
    color: var(--cl-text) !important;
}

[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    opacity: 0.46;
    background-image:
        linear-gradient(rgba(56, 189, 248, 0.09) 1px, transparent 1px),
        linear-gradient(90deg, rgba(56, 189, 248, 0.09) 1px, transparent 1px),
        radial-gradient(circle, rgba(103, 232, 249, 0.45) 1px, transparent 1.5px);
    background-size: 72px 72px, 72px 72px, 130px 130px;
    mask-image: linear-gradient(90deg, transparent 0%, black 18%, black 100%);
}

[data-testid="stAppViewContainer"]::after {
    content: "";
    position: fixed;
    right: -8vw;
    top: -10vh;
    width: 58vw;
    height: 56vh;
    z-index: 0;
    pointer-events: none;
    opacity: 0.5;
    background:
        linear-gradient(128deg, transparent 0 18%, rgba(56, 189, 248, 0.22) 18.4% 18.8%, transparent 19.2% 36%, rgba(56, 189, 248, 0.16) 36.4% 36.8%, transparent 37.2%),
        linear-gradient(28deg, transparent 0 22%, rgba(103, 232, 249, 0.18) 22.4% 22.8%, transparent 23.2% 48%, rgba(56, 189, 248, 0.2) 48.4% 48.8%, transparent 49.2%);
}

.main .block-container {
    position: relative;
    z-index: 1;
    max-width: 1420px;
    padding-top: 2.1rem;
    padding-bottom: 2.5rem;
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(2, 6, 14, 0.98), rgba(3, 11, 20, 0.96)),
        linear-gradient(145deg, rgba(56, 189, 248, 0.12), transparent 45%) !important;
    border-right: 1px solid var(--cl-border) !important;
    box-shadow: 12px 0 40px rgba(0, 0, 0, 0.42);
}

[data-testid="stSidebar"] * { color: var(--cl-text) !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .st-emotion-cache-ue6h4q {
    color: var(--cl-muted) !important;
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
    background: linear-gradient(90deg, var(--cl-blue), rgba(56, 189, 248, 0.16), transparent) !important;
    margin: 1rem 0 1.35rem !important;
}

.card, .metric-card, .event-row, .report-card,
[data-testid="stExpander"],
[data-testid="stForm"] {
    background:
        linear-gradient(180deg, rgba(10, 20, 35, 0.94), rgba(4, 10, 19, 0.94)) !important;
    border: 1px solid var(--cl-border) !important;
    border-radius: 8px !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 18px 42px rgba(0, 0, 0, 0.28);
    color: var(--cl-text) !important;
}

.card:hover, .metric-card:hover, .event-row:hover {
    border-color: var(--cl-border-hot) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 0 28px rgba(56, 189, 248, 0.12);
}

.metric-label, .score-label {
    color: var(--cl-muted) !important;
    text-transform: uppercase;
}

.metric-val, .score-value {
    color: var(--cl-text) !important;
}

.score-sub,
[data-testid="stCaptionContainer"],
.stMarkdown p {
    color: var(--cl-muted) !important;
}

div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
[data-baseweb="select"] > div,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background: rgba(1, 6, 14, 0.86) !important;
    border: 1px solid rgba(83, 166, 219, 0.32) !important;
    color: var(--cl-text) !important;
    border-radius: 8px !important;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02) !important;
}

input::placeholder,
textarea::placeholder {
    color: #6f7d92 !important;
}

div.stButton > button,
button[kind="primary"],
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #0369a1, #0ea5e9 52%, #67e8f9) !important;
    color: #ffffff !important;
    border: 1px solid rgba(125, 211, 252, 0.42) !important;
    border-radius: 999px !important;
    font-weight: 800 !important;
    box-shadow: 0 0 22px rgba(14, 165, 233, 0.24) !important;
}

div.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    border-color: rgba(255, 255, 255, 0.82) !important;
    filter: brightness(1.08);
}

[data-testid="stFileUploader"] {
    background: rgba(5, 12, 22, 0.76) !important;
    border: 1px dashed rgba(103, 232, 249, 0.38) !important;
    border-radius: 8px !important;
    padding: 0.75rem !important;
}

[data-testid="stAlert"] {
    background: rgba(7, 14, 25, 0.92) !important;
    border: 1px solid var(--cl-border) !important;
    color: var(--cl-text) !important;
}

.advice-item {
    background: rgba(56, 189, 248, 0.08) !important;
    border-left: 3px solid var(--cl-blue) !important;
    color: var(--cl-text) !important;
}

.badge, .h3-badge, .source-badge {
    border-radius: 999px !important;
}

.cl-hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    margin: 0.2rem 0 1.2rem;
    padding: 1.2rem 0 0.2rem;
}

.cl-kicker {
    color: var(--cl-blue);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em !important;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
}

.cl-title {
    color: var(--cl-text);
    font-size: clamp(2.05rem, 4vw, 3.35rem);
    font-weight: 900;
    line-height: 1.02;
    margin: 0;
}

.cl-subtitle {
    color: var(--cl-muted);
    font-size: 0.98rem;
    margin-top: 0.65rem;
    max-width: 760px;
}

.cl-timebox {
    min-width: 168px;
    text-align: right;
    color: var(--cl-text);
    font-size: 1.05rem;
    font-weight: 800;
}

.cl-timebox span {
    display: block;
    color: var(--cl-muted);
    font-size: 0.78rem;
    font-weight: 500;
    margin-top: 0.25rem;
}

.cl-map-shell {
    overflow: hidden;
    border: 1px solid var(--cl-border);
    border-radius: 8px;
    background: rgba(2, 6, 14, 0.92);
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02), 0 26px 80px rgba(0,0,0,0.42);
}

@media (max-width: 760px) {
    .cl-hero {
        display: block;
    }
    .cl-timebox {
        text-align: left;
        margin-top: 1rem;
    }
}

img {
    border-radius: 8px;
}

footer, #MainMenu, header { visibility: hidden; }
</style>
        """,
        unsafe_allow_html=True,
    )
