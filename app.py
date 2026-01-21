import streamlit as st
import json
import threading
import time
from streamlit_autorefresh import st_autorefresh
from database import (
    save_test_case, get_all_test_cases, delete_test_case, delete_eval_record,
    save_eval_record, get_eval_history, get_stats, get_all_models,
    get_model_summary_stats, get_model_detail_stats, get_case_summary_stats, get_case_model_ranking
)
from llm_client import call_local_llm, call_evaluator
from init_db import init_db

# 初始化数据库
init_db()

st.set_page_config(page_title="Local LLM Code Benchmarker", layout="wide")

# --- 后台任务管理器 ---
class BackgroundTaskManager:
    def __init__(self):
        self.is_running = False
        self.progress = 0.0
        self.status = "空闲"
        self.logs = []
        self.current_case = ""
        self.total_cases = 0
        self.completed_cases = 0
        self.thread = None
        self.stop_requested = False

    def add_log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {msg}")
        if len(self.logs) > 100:
            self.logs.pop(0)

    def run_batch_test(self, selected_cases, temperature):
        self.is_running = True
        self.stop_requested = False
        self.progress = 0.0
        self.completed_cases = 0
        self.total_cases = len(selected_cases)
        self.logs = []
        eval_fail_count = 0

        for idx, case in enumerate(selected_cases):
            if self.stop_requested:
                self.add_log("🛑 任务被用户停止")
                break
            
            self.current_case = case['title']
            self.status = f"正在处理 ({idx+1}/{self.total_cases}): {self.current_case}"
            self.add_log(f">>> 开始测试用例: {self.current_case}")
            
            local_res = None
            try:
                # 1. 调用本地模型
                self.add_log(f"正在请求本地模型 (10.0.0.114:8080)...")
                local_res = call_local_llm(case['source_code'], case['prompt'], temperature)
                self.add_log(f"本地模型响应成功 ({local_res['completion_tokens']} tokens)")
                
                # 2. 调用评委模型
                self.add_log(f"正在请求评委模型进行评分...")
                eval_res = call_evaluator(case['reference_answer'], local_res['content'])
                
                if "评委调用在" in eval_res.get('reasoning', ""):
                    eval_fail_count += 1
                    self.add_log(f"⚠️ 评分失败 ({eval_fail_count}/3)")
                else:
                    eval_fail_count = 0
                    self.add_log(f"评分完成: {eval_res.get('score', 0)}分")
                
                if eval_fail_count >= 3:
                    self.add_log("❌ 评分模型连续失败 3 次，停止全部测试。")
                    break

                # 3. 保存结果
                record_data = {
                    "case_id": case['id'],
                    "model_name": local_res['model_name'],
                    "temperature": temperature,
                    "local_response": local_res['content'],
                    "chain_of_thought": local_res['chain_of_thought'],
                    "prompt_tokens": local_res['prompt_tokens'],
                    "completion_tokens": local_res['completion_tokens'],
                    "total_time_ms": local_res['duration_ms'],
                    "tokens_per_second": local_res['tps'],
                    "prompt_tps": local_res.get('prompt_tps', 0),
                    "max_context": local_res.get('max_context', 0),
                    "eval_score": eval_res.get('score', 0),
                    "eval_comment": eval_res.get('reasoning', "")
                }
                save_eval_record(record_data)
                self.add_log(f"✅ 用例 '{self.current_case}' 保存成功")
                
            except Exception as e:
                self.add_log(f"❌ 执行失败: {str(e)}")
            
            self.completed_cases += 1
            self.progress = self.completed_cases / self.total_cases

        self.is_running = False
        self.status = "已完成" if not self.stop_requested else "已停止"
        self.progress = 1.0

    def start_task(self, selected_cases, temperature):
        if not self.is_running:
            self.thread = threading.Thread(target=self.run_batch_test, args=(selected_cases, temperature))
            self.thread.daemon = True
            self.thread.start()

    def stop_task(self):
        self.stop_requested = True

if "task_manager" not in st.session_state:
    st.session_state.task_manager = BackgroundTaskManager()

task_mgr = st.session_state.task_manager

# --- 侧边栏导航 ---
with st.sidebar:
    st.title("🚀 LLM Benchmarker")
    menu = st.radio("菜单", ["用例管理", "执行测试", "历史记录", "统计分析"])
    
    # 后台任务进度显示
    if task_mgr.is_running:
        st.divider()
        st.subheader("⏳ 正在执行测试")
        st.info(task_mgr.status)
        st.progress(task_mgr.progress)
        if st.button("🛑 停止任务"):
            task_mgr.stop_task()
        
        # 自动刷新页面以更新进度
        st_autorefresh(interval=2000, key="progress_refresh")
    elif task_mgr.status == "已完成":
        st.divider()
        st.success("✅ 测试任务已完成")
        if st.button("清除状态"):
            task_mgr.status = "空闲"
            st.rerun()

    st.divider()
    st.header("📊 全局统计")
    stats = get_stats()
    st.metric("测试用例数", stats['total_cases'])
    st.metric("总评测次数", stats['total_evals'])
    st.metric("平均得分", f"{stats['avg_score']:.2f}/10")
    st.metric("平均速度", f"{stats['avg_tps']:.2f} tps")

# --- 页面 1：用例管理 ---
if menu == "用例管理":
    st.header("📝 测试用例管理")
    
    # 编辑状态管理
    editing_case_id = st.session_state.get("editing_case_id", None)
    edit_data = None
    if editing_case_id:
        df_cases = get_all_test_cases()
        edit_data = df_cases[df_cases['id'] == editing_case_id].iloc[0]

    form_title = "📝 编辑测试用例" if editing_case_id else "➕ 新建测试用例"
    with st.expander(form_title, expanded=(editing_case_id is not None)):
        with st.form("case_form", clear_on_submit=not editing_case_id):
            title = st.text_input("用例标题*", value=edit_data['title'] if edit_data is not None else "", placeholder="例如：实现 LRU 缓存")
            category = st.text_input("分类", value=edit_data['category'] if edit_data is not None else "", placeholder="算法 / Web / 修复")
            
            st.write("📂 源代码 (支持多文件)")
            st.info("请以 JSON 格式输入，例如：`{\"main.py\": \"...\"}`。如果是单文件，可直接输入代码。**留空则表示从零开始写新功能。**")
            
            default_source = ""
            if edit_data is not None:
                try:
                    # 尝试美化 JSON
                    src_obj = json.loads(edit_data['source_code'])
                    default_source = json.dumps(src_obj, indent=2, ensure_ascii=False) if src_obj else ""
                except:
                    default_source = edit_data['source_code']
            
            source_code_input = st.text_area("源代码内容", value=default_source, height=200, placeholder="留空表示从零开始...")
            
            prompt = st.text_area("修改要求 (Prompt)*", value=edit_data['prompt'] if edit_data is not None else "", height=100)
            reference_answer = st.text_area("参考答案", value=edit_data['reference_answer'] if edit_data is not None else "", height=150)
            
            col_btn1, col_btn2 = st.columns([1, 5])
            submit = col_btn1.form_submit_button("保存")
            cancel = col_btn2.form_submit_button("取消编辑") if editing_case_id else False
            
            if cancel:
                st.session_state.editing_case_id = None
                st.rerun()

            if submit:
                if not title or not prompt:
                    st.error("标题和要求是必填项！")
                else:
                    # 处理源代码：留空、JSON 或纯文本
                    if not source_code_input.strip():
                        source_dict = {}
                    else:
                        try:
                            source_dict = json.loads(source_code_input)
                        except:
                            source_dict = {"source": source_code_input}
                    
                    save_test_case(title, category, source_dict, prompt, reference_answer, case_id=editing_case_id)
                    st.success(f"用例 '{title}' 已保存！")
                    st.session_state.editing_case_id = None
                    st.rerun()

    st.subheader("现有用例列表")
    df_cases = get_all_test_cases()
    if not df_cases.empty:
        for _, row in df_cases.iterrows():
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                col1.write(f"**{row['title']}** ({row['category']})")
                if col2.button("查看", key=f"view_{row['id']}"):
                    st.session_state[f"view_case_{row['id']}"] = not st.session_state.get(f"view_case_{row['id']}", False)
                
                if col3.button("✏️", key=f"edit_{row['id']}"):
                    st.session_state.editing_case_id = row['id']
                    st.rerun()

                if col4.button("🗑️", key=f"del_{row['id']}"):
                    delete_test_case(row['id'])
                    if st.session_state.get("editing_case_id") == row['id']:
                        st.session_state.editing_case_id = None
                    st.rerun()
                
                if st.session_state.get(f"view_case_{row['id']}", False):
                    try:
                        src_data = json.loads(row['source_code'])
                        if not src_data:
                            st.info("💡 此用例为“从零开始”开发，无初始源代码。")
                        else:
                            st.json(src_data)
                    except:
                        st.code(row['source_code'])
                    
                    st.text_area("Prompt", row['prompt'], disabled=True)
                    st.text_area("参考答案", row['reference_answer'], disabled=True)
    else:
        st.info("暂无用例，请先创建一个。")

# --- 页面 2：执行测试 ---
elif menu == "执行测试":
    st.header("🧪 执行评测")
    
    if task_mgr.is_running:
        st.warning("🚀 测试任务正在后台运行中...")
        st.subheader(task_mgr.status)
        st.progress(task_mgr.progress)
        
        with st.expander("🔍 查看实时执行日志", expanded=True):
            st.code("\n".join(task_mgr.logs))
        
        if st.button("🛑 停止当前任务"):
            task_mgr.stop_task()
            st.rerun()
    else:
        df_cases = get_all_test_cases()
        if df_cases.empty:
            st.warning("请先在'用例管理'中创建测试用例。")
        else:
            st.write("选择要测试的用例：")
            selected_indices = []
            for i, row in df_cases.iterrows():
                if st.checkbox(f"{row['title']} ({row['category']})", key=f"check_{row['id']}"):
                    selected_indices.append(i)
            
            st.divider()
            col_p1, col_p2 = st.columns(2)
            temperature = col_p1.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
            
            col_btn1, col_btn2 = st.columns([1, 4])
            start_batch = col_btn1.button("🚀 开始批量测试", type="primary", disabled=len(selected_indices)==0)
            start_all = col_btn2.button("🔥 执行全部用例")

            if start_all:
                selected_indices = list(range(len(df_cases)))

            if start_batch or start_all:
                selected_cases = [df_cases.iloc[i].to_dict() for i in selected_indices]
                task_mgr.start_task(selected_cases, temperature)
                st.success("任务已在后台启动！您可以切换到其他页面查看。")
                st.rerun()

# --- 页面 3：历史记录 ---
elif menu == "历史记录":
    st.header("📜 评测历史记录")
    
    df_cases = get_all_test_cases()
    col_f1, col_f2 = st.columns(2)
    
    case_options = ["全部"] + df_cases['title'].tolist()
    selected_case_title = col_f1.selectbox("按用例筛选", case_options)
    
    model_options = ["全部"] + get_all_models()
    selected_model = col_f2.selectbox("按模型筛选", model_options)
    
    case_id = None
    if selected_case_title != "全部":
        case_id = df_cases[df_cases['title'] == selected_case_title]['id'].iloc[0]
    
    df_history = get_eval_history(case_id, selected_model)
    
    if not df_history.empty:
        # 使用容器列表代替 st.dataframe 以支持点击查看
        st.write("---")
        # 表头
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1, 3, 2, 1, 2])
        h_col1.write("**ID**")
        h_col2.write("**测试用例**")
        h_col3.write("**模型**")
        h_col4.write("**得分**")
        h_col5.write("**操作**")

        for _, row in df_history.iterrows():
            with st.container(border=True):
                r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([1, 3, 2, 1, 2])
                r_col1.write(f"{row['id']}")
                r_col2.write(f"{row['case_title']}")
                r_col3.write(f"{row['model_name']}")
                r_col4.write(f"{row['eval_score']}")
                
                btn_label = "收起" if st.session_state.get(f"view_eval_{row['id']}", False) else "查看详情"
                if r_col5.button(btn_label, key=f"btn_eval_{row['id']}"):
                    st.session_state[f"view_eval_{row['id']}"] = not st.session_state.get(f"view_eval_{row['id']}", False)
                    st.rerun()

                # 详情展示
                if st.session_state.get(f"view_eval_{row['id']}", False):
                    st.divider()
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write("**本地模型回答**")
                        st.code(row['local_response'])
                        if row['chain_of_thought']:
                            with st.expander("💭 查看思维链 (CoT)", expanded=True):
                                st.write(row['chain_of_thought'])
                    
                    with col_b:
                        st.write("**评委评分与理由**")
                        st.metric("得分", f"{row['eval_score']}/10")
                        st.info(row['eval_comment'])
                        
                        st.write("**性能指标**")
                        st.write(f"- 耗时: {row['total_time_ms']:.2f} ms")
                        st.write(f"- 生成速度: {row['tokens_per_second']:.2f} tps")
                        if 'prompt_tps' in row and row['prompt_tps'] > 0:
                            st.write(f"- 预读速度: {row['prompt_tps']:.2f} tps")
                        if 'max_context' in row and row['max_context'] > 0:
                            st.write(f"- 模型上下文: {row['max_context']} tokens")
                        st.write(f"- Tokens: {row['prompt_tokens']} (in) / {row['completion_tokens']} (out)")
                        
                        if st.button("🗑️ 删除此条记录", key=f"del_eval_{row['id']}"):
                            delete_eval_record(row['id'])
                            st.success(f"记录 {row['id']} 已删除")
                            st.rerun()
    else:
        st.info("暂无评测记录。")

# --- 页面 4：统计分析 ---
elif menu == "统计分析":
    st.header("📊 统计分析报告")
    
    tab1, tab2 = st.tabs(["以模型为单位", "以测试题为单位"])
    
    with tab1:
        st.subheader("模型性能汇总")
        df_model_summary = get_model_summary_stats()
        if not df_model_summary.empty:
            for _, row in df_model_summary.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    col1.write(f"**模型: {row['model_name']}**")
                    col2.write(f"平均分: **{row['avg_score']:.2f}** / 10")
                    col3.write(f"测试次数: {row['test_count']}")
                    
                    if st.button("查看每题平均分", key=f"model_detail_{row['model_name']}"):
                        st.session_state[f"show_detail_{row['model_name']}"] = not st.session_state.get(f"show_detail_{row['model_name']}", False)
                        st.rerun()
                    
                    if st.session_state.get(f"show_detail_{row['model_name']}", False):
                        st.write("---")
                        df_details = get_model_detail_stats(row['model_name'])
                        st.table(df_details.rename(columns={
                            'case_title': '测试题',
                            'avg_score': '平均分',
                            'run_count': '运行次数'
                        }))
        else:
            st.info("暂无模型统计数据。")

    with tab2:
        st.subheader("测试题汇总")
        df_case_summary = get_case_summary_stats()
        if not df_case_summary.empty:
            for _, row in df_case_summary.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    col1.write(f"**测试题: {row['case_title']}**")
                    col2.write(f"全模型平均分: **{row['avg_score']:.2f}** / 10")
                    col3.write(f"总运行次数: {row['total_runs']}")
                    
                    if st.button("查看模型排名", key=f"case_rank_{row['case_id']}"):
                        st.session_state[f"show_rank_{row['case_id']}"] = not st.session_state.get(f"show_rank_{row['case_id']}", False)
                        st.rerun()
                    
                    if st.session_state.get(f"show_rank_{row['case_id']}", False):
                        st.write("---")
                        df_ranking = get_case_model_ranking(row['case_id'])
                        st.table(df_ranking.rename(columns={
                            'model_name': '模型名称',
                            'avg_score': '平均分',
                            'run_count': '运行次数'
                        }))
        else:
            st.info("暂无测试题统计数据。")
