import streamlit as st
from init_db import init_db
from background_tasks import BackgroundTaskManager
from ui_pages import render_sidebar, render_case_manager, render_test_runner, render_history, render_stats


@st.cache_resource
def initialize_database():
    init_db()


initialize_database()

st.set_page_config(page_title="Local LLM Code Benchmarker", layout="wide")

if "task_manager" not in st.session_state:
    st.session_state.task_manager = BackgroundTaskManager()

task_mgr = st.session_state.task_manager

menu = render_sidebar(task_mgr)

if menu == "用例管理":
    render_case_manager()
elif menu == "执行测试":
    render_test_runner(task_mgr)
elif menu == "历史记录":
    render_history()
elif menu == "统计分析":
    render_stats()
