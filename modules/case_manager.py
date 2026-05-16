"""Test case manager page for the LLM Benchmarker app."""

import json
import streamlit as st
from database import get_all_test_cases, delete_test_case, save_test_case


def render_case_manager():
    """Render the test case management page."""
    st.header("📝 测试用例管理")

    # 仅调用一次获取所有用例（已缓存）
    df_cases = get_all_test_cases()
    
    editing_case_id = st.session_state.get("editing_case_id", None)
    edit_data = None
    if editing_case_id and not df_cases.empty:
        matching = df_cases[df_cases['id'] == editing_case_id]
        if not matching.empty:
            edit_data = matching.iloc[0]

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
    # 复用开头已获取的 df_cases（已缓存），无需再次调用
    if not df_cases.empty:
        # 添加分页显示
        page_size = 15
        total_items = len(df_cases)
        total_pages = (total_items + page_size - 1) // page_size
        
        if 'case_page' not in st.session_state:
            st.session_state.case_page = 0
        
        current_page = st.session_state.case_page
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, total_items)
        
        st.caption(f"显示 {start_idx + 1}-{end_idx} / 共 {total_items} 个用例")
        
        for idx in range(start_idx, end_idx):
            row = df_cases.iloc[idx]
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                col1.write(f"**{row['title']}** ({row['category']})")
                if col2.button("查看", key=f"view_{row['id']}"):
                    st.session_state[f"view_case_{row['id']}"] = not st.session_state.get(f"view_case_{row['id']}", False)

                if col3.button("✏️", key=f"edit_{row['id']}"):
                    st.session_state.editing_case_id = int(row['id'])
                    st.rerun()

                if col4.button("🗑️", key=f"del_{row['id']}"):
                    delete_test_case(int(row['id']))
                    if st.session_state.get("editing_case_id") == row['id']:
                        st.session_state.editing_case_id = None
                    st.rerun()

                if st.session_state.get(f"view_case_{row['id']}", False):
                    try:
                        src_data = json.loads(row['source_code'])
                        if not src_data:
                            st.info('💡 此用例为"从零开始"开发，无初始源代码。')
                        else:
                            st.json(src_data)
                    except Exception:
                        st.code(row['source_code'])

                    st.text_area("Prompt", row['prompt'], disabled=True)
                    st.text_area("参考答案", row['reference_answer'], disabled=True)
        
        # 分页导航
        if total_pages > 1:
            nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
            if nav_col1.button("⬅️ 上一页", disabled=(current_page == 0)):
                st.session_state.case_page = current_page - 1
                st.rerun()
            nav_col2.markdown(f"<div style='text-align: center'>第 {current_page + 1} / {total_pages} 页</div>", unsafe_allow_html=True)
            if nav_col3.button("下一页 ➡️", disabled=(current_page >= total_pages - 1)):
                st.session_state.case_page = current_page + 1
                st.rerun()
    else:
        st.info("暂无用例，请先创建一个。")
