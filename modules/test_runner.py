"""Test runner page for the LLM Benchmarker app."""

import streamlit as st
import requests
from database import get_all_test_cases
import config  # 使用集中配置文件


@st.cache_data(ttl=120)
def fetch_models_from_api(api_base: str, api_key: str):
    """从 OpenAI 兼容的 /v1/models 接口获取可用模型列表。

    Returns:
        list[str]: 模型 ID 列表；失败时返回空列表。
    """
    if not api_base or not api_key:
        return []
    try:
        url = api_base.rstrip("/") + "/models"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            models = []
            # 兼容 OpenAI / NewAPI 常见结构
            for m in data.get("data", []):
                mid = m.get("id") or m.get("name")
                if mid:
                    models.append(mid)
            return sorted(models)
        return []
    except Exception:
        return []


def render_test_runner(task_mgr):
    """Render the test execution page."""
    st.header("🧪 执行评测")

    # 初始化模型名称配置 - 移至函数顶部确保变量始终存在，防止 AttributeError
    if 'model_source_selector' not in st.session_state:
        st.session_state.model_source_selector = "本地"
    
    if 'model_name_input' not in st.session_state:
        st.session_state.model_name_input = "local"
    
    if 'remote_api_endpoint' not in st.session_state:
        st.session_state.remote_api_endpoint = config.DEFAULT_REMOTE_API_ENDPOINT
        
    if 'remote_api_key' not in st.session_state:
        st.session_state.remote_api_key = config.DEFAULT_REMOTE_API_KEY

    # 记录上次的选择，用于检测切换并重置默认值
    if 'last_model_source' not in st.session_state:
        st.session_state.last_model_source = st.session_state.model_source_selector

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

            with st.expander("⚙️ 模型配置", expanded=True):
                model_source = st.selectbox(
                    "模型来源",
                    options=["本地", "OpenRouter", "NVIDIA", "NewAPI", "LiteLLM"],
                    key="model_source_selector"
                )

                # 如果来源发生变化，手动重置相关输入
                if model_source != st.session_state.last_model_source:
                    if model_source == "本地":
                        st.session_state.model_name_input = "local"
                    elif model_source == "OpenRouter":
                        st.session_state.model_name_input = config.DEFAULT_REMOTE_MODEL_NAME
                        st.session_state.remote_api_endpoint = config.OPENROUTER_API_URL
                        st.session_state.remote_api_key = config.OPENROUTER_API_KEY
                    elif model_source == "NVIDIA":
                        st.session_state.model_name_input = config.NVIDIA_MODEL_ID
                        st.session_state.remote_api_endpoint = config.NVIDIA_API_URL
                        st.session_state.remote_api_key = config.NVIDIA_API_KEY
                    elif model_source == "NewAPI":
                        st.session_state.model_name_input = config.NEWAPI_MODEL_ID or ""
                        st.session_state.remote_api_endpoint = config.NEWAPI_API_URL
                        st.session_state.remote_api_key = config.NEWAPI_API_KEY
                    elif model_source == "LiteLLM":
                        st.session_state.model_name_input = ""  # 用户输入
                        st.session_state.remote_api_endpoint = config.LITELLM_API_URL
                        st.session_state.remote_api_key = config.LITELLM_API_KEY
                    st.session_state.last_model_source = model_source

                if model_source == "本地":
                    st.info("使用本地 Llama.cpp 服务 (URL 和 Key 将使用 config.py 中的默认值)")
                else:
                    # API URL / Key
                    api_base = st.text_input(
                        "API URL",
                        key="remote_api_endpoint"
                    )
                    api_key = st.text_input(
                        "API Key",
                        type="password",
                        key="remote_api_key"
                    )

                    # 获取可用模型列表
                    available_models = []
                    if model_source in ("NewAPI"):
                        available_models = fetch_models_from_api(api_base, api_key)

                    if available_models:
                        # 如果当前选中值在列表中，则保留；否则默认选第一个
                        current = st.session_state.get("model_name_input", "")
                        if current not in available_models:
                            current = available_models[0]
                            st.session_state.model_name_input = current

                        st.selectbox(
                            "模型名称",
                            options=available_models,
                            key="model_name_input",
                        )
                    else:
                        # 无法获取列表时，提供文本输入
                        st.text_input(
                            "模型名称",
                            key="model_name_input"
                        )

            st.divider()

            col_btn1, col_btn2 = st.columns([1, 4])
            start_batch = col_btn1.button("🚀 开始批量测试", type="primary", disabled=len(selected_indices) == 0)
            start_all = col_btn2.button("🔥 执行全部用例")

            if start_all:
                selected_indices = list(range(len(df_cases)))

            if start_batch or start_all:
                selected_cases = [df_cases.iloc[i].to_dict() for i in selected_indices]
                
                # 根据模型名称决定使用本地还是远端配置 - 使用 .get() 更加鲁棒
                model_name = st.session_state.get('model_name_input', 'local').strip()
                
                if model_name.lower() == "local":
                    # 使用本地模型配置（传递 None，让 llm_client 使用默认配置）
                    api_base = None
                    model_id = None
                    api_key = None
                    print(f"\n[DEBUG] Using LOCAL model configuration")
                else:
                    # 使用远端模型配置
                    api_base = st.session_state.get('remote_api_endpoint') or config.DEFAULT_REMOTE_API_ENDPOINT
                    model_id = model_name
                    api_key = st.session_state.get('remote_api_key') or config.DEFAULT_REMOTE_API_KEY
                    print(f"\n[DEBUG] Using REMOTE model: {model_id}")
                    print(f"[DEBUG] API Endpoint: {api_base}")

                # 启动任务
                print(f"[DEBUG] UI Triggering start_task with {len(selected_cases)} cases")
                task_mgr.start_task(
                    selected_cases,
                    api_base=api_base,
                    api_key=api_key,
                    model_id=model_id
                )
                st.success("任务已在后台启动！您可以切换到其他页面查看。")
                st.rerun()
