"""Test runner page for the LLM Benchmarker app."""

import streamlit as st
from database import get_all_test_cases


def render_test_runner(task_mgr):
    """Render the test execution page."""
    st.header("🧪 执行评测")

    if task_mgr.is_running:
        st.warning("🚀 测试任务正在后台运行中...")
        st.subheader(task_mgr.status)
        st.progress(task_mgr.progress)

        if task_mgr.pending_evals > 0:
            eval_progress = min(task_mgr.completed_evals / task_mgr.pending_evals, 1.0)
            st.write(f"**异步评分进度**: {task_mgr.completed_evals}/{task_mgr.pending_evals}")
            st.progress(eval_progress)

        with st.expander("🔍 查看实时执行日志", expanded=True):
            st.code("\n".join(task_mgr.logs))

        if st.button("🛑 停止当前任务"):
            task_mgr.stop_task()
            st.rerun()
    else:
        if task_mgr.pending_evals > task_mgr.completed_evals:
            st.info(f"ℹ️ 后台评分任务进行中: {task_mgr.completed_evals}/{task_mgr.pending_evals}。您可以继续启动新的测试。")
            eval_progress = min(task_mgr.completed_evals / task_mgr.pending_evals, 1.0)
            st.progress(eval_progress)
            st.divider()
        
        df_cases = get_all_test_cases()
        if df_cases.empty:
            st.warning("请先在'用例管理'中创建测试用例。")
        else:
            st.write("选择要测试的用例：")
            selected_indices = []
            for i, row in df_cases.iterrows():
                if st.checkbox(f"{row['title']} ({row['category']})", key=f"check_{row['id']}"):
                    selected_indices.append(i)

            # 1. 确保所有相关 session_state 变量在脚本开始时被初始化
            if 'use_remote' not in st.session_state:
                st.session_state.use_remote = False
            if 'remote_api_endpoint' not in st.session_state:
                st.session_state.remote_api_endpoint = "https://openrouter.ai/api/v1"
            if 'remote_model_name' not in st.session_state:
                st.session_state.remote_model_name = "z-ai/glm-4.5-air:free"
            if 'remote_api_key' not in st.session_state:
                st.session_state.remote_api_key = "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"

            with st.expander("⚙️ 远端模型配置", expanded=True):
                # 2. 启用/禁用开关，其状态自动同步到 session_state
                use_remote = st.checkbox("启用远端模型", key='use_remote')
                
                # 3. 输入框，完全依赖 key 与 session_state 同步，移除 value 参数
                st.text_input("API Endpoint", placeholder="例如: https://api.openai.com/v1", key="remote_api_endpoint")
                st.text_input("模型名称", placeholder="例如: gpt-4o", key="remote_model_name")
                st.text_input("API Key", type="password", placeholder="留空则使用环境变量", key="remote_api_key")

            st.divider()

            col_btn1, col_btn2 = st.columns([1, 4])
            start_batch = col_btn1.button("🚀 开始批量测试", type="primary", disabled=len(selected_indices) == 0)
            start_all = col_btn2.button("🔥 执行全部用例")

            if start_all:
                selected_indices = list(range(len(df_cases)))

            if start_batch or start_all:
                selected_cases = [df_cases.iloc[i].to_dict() for i in selected_indices]
                
                api_base = None
                model_id = None
                api_key = None

                # 4. 启动任务时，根据 use_remote 状态决定是否传递参数
                if st.session_state.use_remote:
                    api_base = st.session_state.remote_api_endpoint
                    model_id = st.session_state.remote_model_name
                    api_key = st.session_state.remote_api_key

                # 5. 传递参数
                print(f"\n[DEBUG] UI Triggering start_task with {len(selected_cases)} cases")
                print(f"[DEBUG] Remote config: base={api_base}, model={model_id}")
                task_mgr.start_task(
                    selected_cases,
                    api_base=api_base,
                    api_key=api_key,
                    model_id=model_id
                )
                st.success("任务已在后台启动！您可以切换到其他页面查看。")
                st.rerun()
