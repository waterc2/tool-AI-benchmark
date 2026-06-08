"""Evaluation history page for the LLM Benchmarker app."""

import time
import streamlit as st
import pandas as pd
from openai import OpenAI
import config
from database import get_all_test_cases, get_all_models, get_eval_history, delete_eval_record

# 每页显示的记录数
RECORDS_PER_PAGE = 20


def render_history():
    """Render the evaluation history page."""
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

    if df_history.empty:
        st.info("暂无评测记录。")
        return

    total_records = len(df_history)
    total_pages = (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE

    # --- 自动重新评分逻辑 --- 
    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5, col_page, _ = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 2, 1])
    
    available_cols = df_history.columns
    # 统计所有评分为 0 的评委总数（而不是记录数）
    # 映射：1=gem, 2=opus, 3=gpt, 4=top2, 5=top
    failed_count = 0
    for row in df_history.itertuples():
        if 'eval_score_1' in available_cols and (pd.isna(getattr(row, 'eval_score_1')) or getattr(row, 'eval_score_1') == 0):
            failed_count += 1
        if 'eval_score_2' in available_cols and (pd.isna(getattr(row, 'eval_score_2')) or getattr(row, 'eval_score_2') == 0):
            failed_count += 1
        if 'eval_score_3' in available_cols and (pd.isna(getattr(row, 'eval_score_3')) or getattr(row, 'eval_score_3') == 0):
            failed_count += 1
        if 'eval_score_4' in available_cols and (pd.isna(getattr(row, 'eval_score_4')) or getattr(row, 'eval_score_4') == 0):
            failed_count += 1
        if 'eval_score_5' in available_cols and (pd.isna(getattr(row, 'eval_score_5')) or getattr(row, 'eval_score_5') == 0):
            failed_count += 1
    
    # 按钮 1: 自动补齐评分 (分数为 0 的项)
    if col_btn1.button(f"🔄 自动重新评分 ({failed_count}条)", 
                      help="将所有分数为 0 的评委模型重新评分"):
        if failed_count > 0:
            task_mgr = st.session_state.task_manager
            count = 0
            for row in df_history.itertuples():
                target_levels = []
                if 'eval_score_1' in available_cols and (pd.isna(getattr(row, 'eval_score_1')) or getattr(row, 'eval_score_1') == 0): target_levels.append('gem')
                if 'eval_score_2' in available_cols and (pd.isna(getattr(row, 'eval_score_2')) or getattr(row, 'eval_score_2') == 0): target_levels.append('opus')
                if 'eval_score_3' in available_cols and (pd.isna(getattr(row, 'eval_score_3')) or getattr(row, 'eval_score_3') == 0): target_levels.append('gpt')
                if 'eval_score_4' in available_cols and (pd.isna(getattr(row, 'eval_score_4')) or getattr(row, 'eval_score_4') == 0): target_levels.append('top2')
                if 'eval_score_5' in available_cols and (pd.isna(getattr(row, 'eval_score_5')) or getattr(row, 'eval_score_5') == 0): target_levels.append('top')
                
                if target_levels:
                    task_mgr.submit_re_evaluate(
                        row.id, row.case_title, row.prompt, row.reference_answer, row.local_response, 
                        target_levels=target_levels
                    )
                    count += 1
            st.success(f"已提交 {count} 条记录进行补齐评分！")
            time.sleep(1)
            st.rerun()

    # 按钮 2: 强制 TOP 重新评分 (不管有没有值)
    if col_btn2.button("🔝 强制 TOP 评分", help="对当前筛选出的所有记录，强制使用 TOP 模型重新评分"):
        task_mgr = st.session_state.task_manager
        count = 0
        for row in df_history.itertuples():
            task_mgr.submit_re_evaluate(
                row.id, row.case_title, row.prompt, row.reference_answer, row.local_response,
                target_levels=['top']
            )
            count += 1
        st.success(f"已强制提交 {count} 条记录进行 TOP 重新评分！")
        time.sleep(1)
        st.rerun()

    # 按钮 3: 测试全部评分模型
    if col_btn3.button("🧪 测试评分模型", help="对所有评分模型发送'你是谁'，测试响应"):
        st.session_state.show_test_model_dialog = True
    
    # 弹窗：测试评分模型结果
    if st.session_state.get('show_test_model_dialog', False):
        with st.container(border=True):
            col_close, _ = st.columns([1, 5])
            if col_close.button("❌ 关闭", key="close_test_dialog"):
                st.session_state.show_test_model_dialog = False
                st.rerun()
            
            st.subheader("测试评分模型")
            st.write("正在对所有评分模型发送测试消息 **'你是谁'** ...")
            
            # 定义所有评分模型
            evaluator_configs = [
                ("Gem", config.EVALUATOR_MODEL_GEM),
                ("Opus", config.EVALUATOR_MODEL_OPUS),
                ("GPT", config.EVALUATOR_MODEL_GPT),
                ("Top2", config.EVALUATOR_MODEL_TOP2),
                ("Top", config.EVALUATOR_MODEL_TOP),
            ]
            
            # 创建进度条并立即显示
            progress_bar = st.progress(0, text="正在测试...")
            
            # 逐个测试并显示结果
            for idx, (name, model_id) in enumerate(evaluator_configs):
                status_area = st.empty()
                status_area.info(f"🔄 正在测试 {name} ({model_id})...")

                try:
                    # 每个评分模型使用独立的 API 配置
                    if name == "Gem":
                        api_key = config.EVALUATOR_GEM_API_KEY
                        api_base = config.EVALUATOR_GEM_BASE_URL
                    elif name == "Opus":
                        api_key = config.EVALUATOR_OPUS_API_KEY
                        api_base = config.EVALUATOR_OPUS_BASE_URL
                    elif name == "GPT":
                        api_key = config.EVALUATOR_GPT_API_KEY
                        api_base = config.EVALUATOR_GPT_BASE_URL
                    elif name == "Top2":
                        api_key = config.EVALUATOR_TOP2_API_KEY
                        api_base = config.EVALUATOR_TOP2_BASE_URL
                    elif name == "Top":
                        api_key = config.EVALUATOR_TOP_API_KEY
                        api_base = config.EVALUATOR_TOP_BASE_URL
                    else:
                        api_key = config.EVALUATOR_GEM_API_KEY
                        api_base = config.EVALUATOR_GEM_BASE_URL

                    client = OpenAI(
                        api_key=api_key,
                        base_url=api_base,
                        timeout=180.0
                    )
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": "你是谁"}],
                        max_tokens=200
                    )
                    
                    content = response.choices[0].message.content if response.choices else "无响应"
                    status_area.success(f"✅ {name} ({model_id}): 测试成功")
                    st.write(f"**{name} 的回复：**")
                    st.write(content)
                    st.divider()
                
                except Exception as e:
                    error_msg = str(e)
                    status_area.error(f"❌ {name} ({model_id}): {error_msg}")
                    st.divider()
                
                # 更新进度条
                progress_bar.progress((idx + 1) / len(evaluator_configs), text=f"已完成 {idx+1}/{len(evaluator_configs)}")
            
            progress_bar.empty()
            
            if st.button("完成，关闭对话框", key="finish_test_dialog"):
                st.session_state.show_test_model_dialog = False
                st.rerun()

    # 分页控制
    current_page = col_page.number_input(
        f"页码 (共 {total_pages} 页，{total_records} 条记录)",
        min_value=1, max_value=max(1, total_pages), value=1, step=1
    )
    
    # 计算当前页的数据范围
    start_idx = (current_page - 1) * RECORDS_PER_PAGE
    end_idx = min(start_idx + RECORDS_PER_PAGE, total_records)
    df_page = df_history.iloc[start_idx:end_idx]

    st.write("---")
    h_col1, h_col2, h_col3, h_col_time, h_col4, h_col5 = st.columns([0.6, 2.5, 2, 1.2, 2, 1.5])
    h_col1.write("**ID**")
    h_col2.write("**测试用例**")
    h_col3.write("**模型**")
    h_col_time.write("**耗时**")
    h_col4.write("**得分**")
    h_col5.write("**操作**")

    # 使用 itertuples() 替代 iterrows() 提升性能
    for row in df_page.itertuples():
        record_id = row.id
        view_key = f"view_eval_{record_id}"
        is_expanded = st.session_state.get(view_key, False)
        
        with st.container(border=True):
            r_col1, r_col2, r_col3, r_col_time, r_col4, r_col5 = st.columns([0.6, 2.5, 2, 1.2, 2, 1.5])
            r_col1.write(f"{record_id}")
            r_col2.write(f"{row.case_title}")
            r_col3.write(f"{row.model_name}")
            
            # 耗时显示
            total_time_ms = getattr(row, 'total_time_ms', 0) or 0
            if total_time_ms >= 1000:
                r_col_time.write(f"{total_time_ms/1000:.2f}s")
            else:
                r_col_time.write(f"{total_time_ms:.0f}ms")

            total_score = getattr(row, 'eval_score', 0) or 0
            def safe_int(val):
                if pd.isna(val) or val is None:
                    return 0
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return 0

            gem_s = safe_int(getattr(row, 'eval_score_1', 0))
            opus_s = safe_int(getattr(row, 'eval_score_2', 0))
            gpt_s = safe_int(getattr(row, 'eval_score_3', 0))
            top2_s = safe_int(getattr(row, 'eval_score_4', 0))
            top_s = safe_int(getattr(row, 'eval_score_5', 0))
            r_col4.write(f"{total_score:.1f} ({gem_s},{opus_s},{gpt_s},{top2_s},{top_s})")

            btn_label = "收起" if is_expanded else "查看详情"
            btn_col1, btn_col2 = r_col5.columns([1, 1])
            if btn_col1.button(btn_label, key=f"btn_eval_{record_id}"):
                st.session_state[view_key] = not is_expanded
                st.rerun()
            
            if btn_col2.button("🔄", key=f"re_eval_top_{record_id}", help="重新评分"):
                target_levels = []
                if gem_s == 0: target_levels.append('gem')
                if opus_s == 0: target_levels.append('opus')
                if gpt_s == 0: target_levels.append('gpt')
                if top2_s == 0: target_levels.append('top2')
                if top_s == 0: target_levels.append('top')
                
                if not target_levels:
                    target_levels = None
                    
                task_mgr = st.session_state.task_manager
                task_mgr.submit_re_evaluate(
                    record_id,
                    row.case_title,
                    row.prompt,
                    row.reference_answer,
                    row.local_response,
                    target_levels=target_levels
                )
                msg = f"已提交记录 {record_id} 到异步评分队列"
                if target_levels:
                    msg += f" (目标：{', '.join(target_levels)})"
                st.success(f"{msg}！")
                time.sleep(1)
                st.rerun()

            if is_expanded:
                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**本地模型回答**")
                    st.code(row.local_response)
                    if row.chain_of_thought:
                        with st.expander("💭 查看思维链 (CoT)", expanded=True):
                            st.write(row.chain_of_thought)

                with col_b:
                    st.write("**评委评分与理由**")

                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Gem", f"{gem_s}/100")
                    c2.metric("Opus", f"{opus_s}/100")
                    c3.metric("GPT", f"{gpt_s}/100")
                    c4.metric("Top2", f"{top2_s}/100")
                    c5.metric("Top", f"{top_s}/100")

                    with st.expander("查看详细评语", expanded=True):
                        st.markdown(f"**Gem:** {getattr(row, 'eval_comment_1', '无') or '无'}")
                        st.markdown(f"**Opus:** {getattr(row, 'eval_comment_2', '无') or '无'}")
                        st.markdown(f"**GPT:** {getattr(row, 'eval_comment_3', '无') or '无'}")
                        st.markdown(f"**Top2:** {getattr(row, 'eval_comment_4', '无') or '无'}")
                        st.markdown(f"**Top:** {getattr(row, 'eval_comment_5', '无') or '无'}")

                    st.write("**性能指标**")
                    st.write(f"- 耗时：{row.total_time_ms:.2f} ms")
                    st.write(f"- 生成速度：{row.tokens_per_second:.2f} tps")
                    prompt_tps = getattr(row, 'prompt_tps', 0) or 0
                    if prompt_tps > 0:
                        st.write(f"- 预读速度：{prompt_tps:.2f} tps")
                    max_context = getattr(row, 'max_context', 0) or 0
                    if max_context > 0:
                        st.write(f"- 模型上下文：{max_context} tokens")
                    st.write(f"- Tokens: {row.prompt_tokens} (in) / {row.completion_tokens} (out)")

                    st.divider()
                    if st.button("🗑️ 删除此条记录", key=f"del_eval_{record_id}"):
                        delete_eval_record(record_id)
                        st.success(f"记录 {record_id} 已删除")
                        st.rerun()