"""Sidebar component for the LLM Benchmarker app."""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from database import get_stats, clear_cache


def render_sidebar(task_mgr):
    """Render the sidebar with navigation and global stats."""
    with st.sidebar:
        st.title("🚀 LLM Benchmarker")
        menu = st.radio("菜单", ["用例管理", "执行测试", "历史记录", "统计分析", "评分模型设置"])

        # 任务进度区域 - 仅在运行时显示
        if task_mgr.is_running or task_mgr.pending_evals > task_mgr.completed_evals:
            st.divider()
            st.subheader("⏳ 正在执行测试")
            st.info(task_mgr.status)
            st.progress(task_mgr.progress)

            if task_mgr.pending_evals > 0:
                eval_progress = min(task_mgr.completed_evals / task_mgr.pending_evals, 1.0)
                st.write(f"异步评分进度: {task_mgr.completed_evals}/{task_mgr.pending_evals}")
                st.progress(eval_progress)

            if task_mgr.is_running and st.button("🛑 停止任务"):
                task_mgr.stop_task()

            # 仅在任务运行时启用自动刷新，间隔加大到3秒
            st_autorefresh(interval=3000, key="progress_refresh")
        elif task_mgr.status == "全部完成":
            st.divider()
            st.success("✅ 测试任务已完成")
            if st.button("清除状态"):
                task_mgr.status = "空闲"
                task_mgr.pending_evals = 0
                task_mgr.completed_evals = 0
                clear_cache()  # 清除缓存以显示最新数据
                st.rerun()

        st.divider()
        st.header("📊 全局统计")
        # 统计数据已被缓存，无需重复查询
        stats = get_stats()
        st.metric("测试用例数", stats['total_cases'])
        st.metric("总评测次数", stats['total_evals'])
        st.metric("平均得分", f"{stats['avg_score']:.2f}/100")
        st.metric("平均速度", f"{stats['avg_tps']:.2f} tps")

    return menu
