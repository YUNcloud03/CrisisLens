"""Legacy submit page — citizen report flow now lives on app.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from db.database import init_db
from utils.auth import require_login
from utils.ui_theme import apply_theme, page_header

init_db()

st.set_page_config(page_title="災情回報｜CrisisLens", page_icon="📋", layout="wide")
apply_theme()
require_login()

page_header(
    "災情回報已整合至民眾端首頁",
    "為了讓平台邏輯清楚，民眾端現在集中在首頁完成上傳圖片、模型辨識、基本建議與送出災情回報。",
    "Submit Report",
)

st.info("請使用首頁的民眾災情回報流程。")
st.page_link("app.py", label="前往民眾端首頁", icon="🏠")
