"""Evaluation history page for the LLM Benchmarker app."""

import time
import streamlit as st
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
    col_btn, col_page, _ = st.columns([1.5, 2, 2])
    
    # 预计算失败记录（使用向量化操作）
    failed_mask = (
        (df_history.get('eval_score_super', 0) == 0) |
        (df_history.get('eval_score_high', 0) == 0) |
        (df_history.get('eval_score_low', 0) == 0)
    )
    failed_count = failed_mask.sum() if hasattr(failed_mask, 'sum') else len([x for x in failed_mask if x])
    
    if col_btn.button(f"🔄 自动重新评分 ({failed_count}条)", 
                     help="将所有 super/high/low 中分数为 0 的模块重新评分"):
        if failed_count > 0:
            task_mgr = st.session_state.task_manager
            count = 0
            for row in df_history.itertuples():
                target_levels = []
                if getattr(row, 'eval_score_super', 0) == 0: target_levels.append('super')
                if getattr(row, 'eval_score_high', 0) == 0: target_levels.append('high')
                if getattr(row, 'eval_score_low', 0) == 0: target_levels.append('low')
                
                if target_levels:
                    task_mgr.submit_re_evaluate(
                        row.id,
                        row.case_title,
                        row.prompt,
                        row.reference_answer,
                        row.local_response,
                        target_levels=target_levels
                    )
                    count += 1
            st.success(f"已批量提交 {count} 条记录到评分队列！")
            time.sleep(1)
            st.rerun()
        else:
            st.info("没有需要重新评分的记录 (评分项均非0)。")

    # 分页控制
    current_page = col_page.number_input(
        f"页码 (共 {total_pages} 页, {total_records} 条记录)",
        min_value=1, max_value=max(1, total_pages), value=1, step=1
    )
    
    # 计算当前页的数据范围
    start_idx = (current_page - 1) * RECORDS_PER_PAGE
    end_idx = min(start_idx + RECORDS_PER_PAGE, total_records)
    df_page = df_history.iloc[start_idx:end_idx]

    st.write("---")
    h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1, 2, 2, 2, 1.5])
    h_col1.write("**ID**")
    h_col2.write("**测试用例**")
    h_col3.write("**模型**")
    h_col4.write("**得分**")
    h_col5.write("**操作**")

    # 使用 itertuples() 替代 iterrows() 提升性能
    for row in df_page.itertuples():
        record_id = row.id
        view_key = f"view_eval_{record_id}"
        is_expanded = st.session_state.get(view_key, False)
        
        with st.container(border=True):
            r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([1, 2, 2, 2, 1.5])
            r_col1.write(f"{record_id}")
            r_col2.write(f"{row.case_title}")
            r_col3.write(f"{row.model_name}")
            
            total_score = getattr(row, 'eval_score', 0) or 0
            s_score = int(getattr(row, 'eval_score_super', 0) or 0)
            h_score = int(getattr(row, 'eval_score_high', 0) or 0)
            l_score = int(getattr(row, 'eval_score_low', 0) or 0)
            r_col4.write(f"{total_score:.1f} ({s_score},{h_score},{l_score})")

            btn_label = "收起" if is_expanded else "查看详情"
            btn_col1, btn_col2 = r_col5.columns([1, 1])
            if btn_col1.button(btn_label, key=f"btn_eval_{record_id}"):
                st.session_state[view_key] = not is_expanded
                st.rerun()
            
            if btn_col2.button("🔄", key=f"re_eval_top_{record_id}", help="重新评分"):
                target_levels = []
                if s_score == 0: target_levels.append('super')
                if h_score == 0: target_levels.append('high')
                if l_score == 0: target_levels.append('low')
                
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
                    msg += f" (目标: {', '.join(target_levels)})"
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

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Super", f"{s_score}/100")
                    c2.metric("High", f"{h_score}/100")
                    c3.metric("Low", f"{l_score}/100")

                    with st.expander("查看详细评语", expanded=True):
                        st.markdown(f"**Super:** {getattr(row, 'eval_comment_super', '无') or '无'}")
                        st.markdown(f"**High:** {getattr(row, 'eval_comment_high', '无') or '无'}")
                        st.markdown(f"**Low:** {getattr(row, 'eval_comment_low', '无') or '无'}")

                    st.write("**性能指标**")
                    st.write(f"- 耗时: {row.total_time_ms:.2f} ms")
                    st.write(f"- 生成速度: {row.tokens_per_second:.2f} tps")
                    prompt_tps = getattr(row, 'prompt_tps', 0) or 0
                    if prompt_tps > 0:
                        st.write(f"- 预读速度: {prompt_tps:.2f} tps")
                    max_context = getattr(row, 'max_context', 0) or 0
                    if max_context > 0:
                        st.write(f"- 模型上下文: {max_context} tokens")
                    st.write(f"- Tokens: {row.prompt_tokens} (in) / {row.completion_tokens} (out)")

                    st.divider()
                    if st.button("🗑️ 删除此条记录", key=f"del_eval_{record_id}"):
                        delete_eval_record(record_id)
                        st.success(f"记录 {record_id} 已删除")
                        st.rerun()

