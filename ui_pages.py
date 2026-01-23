import json
import time
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from database import (
    get_stats,
    get_all_test_cases,
    delete_test_case,
    save_test_case
)


def render_sidebar(task_mgr):
    with st.sidebar:
        st.title("🚀 LLM Benchmarker")
        menu = st.radio("菜单", ["用例管理", "执行测试", "历史记录", "统计分析"])

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

            st_autorefresh(interval=2000, key="progress_refresh")
        elif task_mgr.status == "全部完成":
            st.divider()
            st.success("✅ 测试任务已完成")
            if st.button("清除状态"):
                task_mgr.status = "空闲"
                task_mgr.pending_evals = 0
                task_mgr.completed_evals = 0
                st.rerun()

        st.divider()
        st.header("📊 全局统计")
        stats = get_stats()
        st.metric("测试用例数", stats['total_cases'])
        st.metric("总评测次数", stats['total_evals'])
        st.metric("平均得分", f"{stats['avg_score']:.2f}/100")
        st.metric("平均速度", f"{stats['avg_tps']:.2f} tps")

    return menu


def render_case_manager():
    st.header("📝 测试用例管理")

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
                    src_obj = json.loads(edit_data['source_code'])
                    default_source = json.dumps(src_obj, indent=2, ensure_ascii=False) if src_obj else ""
                except Exception:
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
                    if not source_code_input.strip():
                        source_dict = {}
                    else:
                        try:
                            source_dict = json.loads(source_code_input)
                        except Exception:
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
                    except Exception:
                        st.code(row['source_code'])

                    st.text_area("Prompt", row['prompt'], disabled=True)
                    st.text_area("参考答案", row['reference_answer'], disabled=True)
    else:
        st.info("暂无用例，请先创建一个。")


def render_test_runner(task_mgr):
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

            st.divider()

            col_btn1, col_btn2 = st.columns([1, 4])
            start_batch = col_btn1.button("🚀 开始批量测试", type="primary", disabled=len(selected_indices) == 0)
            start_all = col_btn2.button("🔥 执行全部用例")

            if start_all:
                selected_indices = list(range(len(df_cases)))

            if start_batch or start_all:
                selected_cases = [df_cases.iloc[i].to_dict() for i in selected_indices]
                task_mgr.start_task(selected_cases)
                st.success("任务已在后台启动！您可以切换到其他页面查看。")
                st.rerun()


def render_history():
    st.header("📜 评测历史记录")

    from database import get_all_models, get_eval_history, delete_eval_record

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
        st.write("---")
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
                btn_col1, btn_col2 = r_col5.columns([1, 1])
                if btn_col1.button(btn_label, key=f"btn_eval_{row['id']}"):
                    st.session_state[f"view_eval_{row['id']}"] = not st.session_state.get(f"view_eval_{row['id']}", False)
                    st.rerun()
                
                if btn_col2.button("🔄", key=f"re_eval_top_{row['id']}", help="重新评分"):
                    task_mgr = st.session_state.task_manager
                    task_mgr.submit_re_evaluate(
                        row['id'],
                        row['case_title'],
                        row['prompt'],
                        row['reference_answer'],
                        row['local_response']
                    )
                    st.success(f"已提交记录 {row['id']} 到异步评分队列！")
                    time.sleep(1)
                    st.rerun()

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

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Super", f"{row.get('eval_score_super', 0)}/100")
                        c2.metric("High", f"{row.get('eval_score_high', 0)}/100")
                        c3.metric("Low", f"{row.get('eval_score_low', 0)}/100")

                        with st.expander("查看详细评语", expanded=True):
                            st.markdown(f"**Super:** {row.get('eval_comment_super', '无')}")
                            st.markdown(f"**High:** {row.get('eval_comment_high', '无')}")
                            st.markdown(f"**Low:** {row.get('eval_comment_low', '无')}")

                        st.write("**性能指标**")
                        st.write(f"- 耗时: {row['total_time_ms']:.2f} ms")
                        st.write(f"- 生成速度: {row['tokens_per_second']:.2f} tps")
                        if 'prompt_tps' in row and row['prompt_tps'] > 0:
                            st.write(f"- 预读速度: {row['prompt_tps']:.2f} tps")
                        if 'max_context' in row and row['max_context'] > 0:
                            st.write(f"- 模型上下文: {row['max_context']} tokens")
                        st.write(f"- Tokens: {row['prompt_tokens']} (in) / {row['completion_tokens']} (out)")

                        st.divider()
                        if st.button("🗑️ 删除此条记录", key=f"del_eval_{row['id']}"):
                            delete_eval_record(row['id'])
                            st.success(f"记录 {row['id']} 已删除")
                            st.rerun()
    else:
        st.info("暂无评测记录。")


def render_stats():
    st.header("📊 统计分析报告")

    from database import (
        get_model_summary_stats,
        get_model_detail_stats,
        get_case_summary_stats,
        get_case_model_ranking,
        get_model_speed_ranking
    )

    tab1, tab2, tab3 = st.tabs(["以模型为单位", "以测试题为单位", "速度排行"])

    with tab1:
        st.subheader("模型性能汇总")
        df_model_summary = get_model_summary_stats()

        if not df_model_summary.empty:
            df_speed = get_model_speed_ranking()

            df_model_summary = pd.merge(
                df_model_summary,
                df_speed[['model_name', 'avg_total_time_ms']],
                on='model_name',
                how='left'
            )

            for _, row in df_model_summary.iterrows():
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
                    col1.write(f"**模型: {row['model_name']}**")
                    col2.write(f"平均分: **{row['avg_score']:.2f}** / 100")
                    col3.write(f"测试次数: {row['test_count']}")

                    avg_time_ms = row['avg_total_time_ms']
                    if pd.notna(avg_time_ms):
                        avg_time_s = avg_time_ms / 1000.0
                        time_str = f"{avg_time_s:.2f} s"
                    else:
                        time_str = "N/A"
                    col4.write(f"**平均总耗时**: {time_str}")

                    if st.button("查看每题平均分", key=f"model_detail_{row['model_name']}"):
                        st.session_state[f"show_detail_{row['model_name']}"] = not st.session_state.get(f"show_detail_{row['model_name']}", False)
                        st.rerun()

                    if st.session_state.get(f"show_detail_{row['model_name']}", False):
                        st.write("---")
                        df_details = get_model_detail_stats(row['model_name'])
                        
                        display_df = df_details.copy()
                        display_df['avg_total_time_s'] = display_df['avg_total_time_ms'].apply(
                            lambda x: f"{x/1000:.2f}" if pd.notna(x) else "N/A"
                        )
                        display_df['avg_completion_tokens'] = display_df['avg_completion_tokens'].apply(
                            lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
                        )
                        display_df['avg_tps'] = display_df['avg_tps'].apply(
                            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                        )
                        display_df['avg_prompt_tps'] = display_df['avg_prompt_tps'].apply(
                            lambda x: f"{x:.2f}" if pd.notna(x) and x > 0 else "N/A"
                        )
                        
                        st.dataframe(
                            display_df[[
                                'case_title', 'avg_score', 'run_count',
                                'avg_score_super', 'avg_score_high', 'avg_score_low',
                                'avg_completion_tokens',
                                'avg_total_time_s', 'avg_tps', 'avg_prompt_tps'
                            ]].rename(columns={
                                'case_title': '测试题',
                                'avg_score': '综合平均分',
                                'run_count': '运行次数',
                                'avg_score_super': 'Super评分',
                                'avg_score_high': 'High评分',
                                'avg_score_low': 'Low评分',
                                'avg_completion_tokens': '输出Tokens',
                                'avg_total_time_s': '平均耗时(s)',
                                'avg_tps': '生成速度(tps)',
                                'avg_prompt_tps': '预读速度(tps)'
                            }),
                            hide_index=True,
                            width='stretch'
                        )
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
                    col2.write(f"全模型平均分: **{row['avg_score']:.2f}** / 100")
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

    with tab3:
        st.subheader("⏱️ 模型平均耗时排行 (毫秒)")
        df_speed = get_model_speed_ranking()
        if not df_speed.empty:
            st.dataframe(
                df_speed.rename(columns={
                    'model_name': '模型名称',
                    'avg_total_time_ms': '平均总耗时 (毫秒)',
                    'avg_tps': '平均生成速度 (TPS)',
                    'avg_prompt_tps': '平均预读速度 (TPS)',
                    'test_count': '测试次数'
                }),
                width='stretch',
                hide_index=True
            )

            st.bar_chart(df_speed.set_index('model_name')['avg_total_time_ms'])
        else:
            st.info("暂无速度统计数据。")
