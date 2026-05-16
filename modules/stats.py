"""Statistics page for the LLM Benchmarker app."""

import pandas as pd
import streamlit as st
from database import (
    get_model_summary_stats,
    get_model_detail_stats,
    get_case_summary_stats,
    get_case_model_ranking,
    get_model_speed_ranking
)


def render_stats():
    """Render the statistics analysis page."""
    st.header("📊 统计分析报告")

    # 在右上角添加筛选器
    col_header, col_filter = st.columns([3, 1])
    with col_filter:
        model_type_filter = st.selectbox(
            "📍 模型类型筛选",
            ["全部", "本地模型", "远端模型"],
            index=0,
            key="model_type_filter"
        )
    
    # 添加颜色图例
    st.markdown("**图例:** :green[🖥️ 本地模型 (.gguf)] | :blue[☁️ 远端模型]")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["以模型为单位", "以测试题为单位", "速度排行"])

    with tab1:
        st.subheader("模型性能汇总")
        df_model_summary = get_model_summary_stats(model_type_filter)

        if not df_model_summary.empty:
            df_speed = get_model_speed_ranking(model_type_filter)

            df_model_summary = pd.merge(
                df_model_summary,
                df_speed[['model_name', 'avg_total_time_ms']],
                on='model_name',
                how='left'
            )

            for _, row in df_model_summary.iterrows():
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 2, 1.5])
                    
                    # 判断是本地模型还是远端模型，使用不同颜色
                    model_name = row['model_name']
                    if model_name.endswith('.gguf'):
                        # 本地模型 - 绿色
                        col1.markdown(f"**模型:** :green[**{model_name}**] 🖥️")
                    else:
                        # 远端模型 - 蓝色
                        col1.markdown(f"**模型:** :blue[**{model_name}**] ☁️")
                    
                    avg_score = row['avg_score']
                    col2.write(f"平均分：**{avg_score:.2f}** / 100" if avg_score is not None else "平均分：**N/A** / 100")
                    col3.write(f"测试次数：{row['test_count']}")

                    avg_time_ms = row['avg_total_time_ms']
                    if pd.notna(avg_time_ms):
                        avg_time_s = avg_time_ms / 1000.0
                        time_str = f"{avg_time_s:.2f} s"
                    else:
                        time_str = "N/A"
                    col4.write(f"**平均总耗时**: {time_str}")

                    # 将按钮放到最右边的列
                    if col5.button("查看每题平均分", key=f"model_detail_{row['model_name']}"):
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
                                'avg_score_1', 'avg_score_2', 'avg_score_3', 'avg_score_4', 'avg_score_5',
                                'avg_completion_tokens',
                                'avg_total_time_s', 'avg_tps', 'avg_prompt_tps'
                            ]].rename(columns={
                                'case_title': '测试题',
                                'avg_score': '综合平均分',
                                'run_count': '运行次数',
                                'avg_score_1': '评委 1(gem)',
                                'avg_score_2': '评委 2(opus)',
                                'avg_score_3': '评委 3(gpt)',
                                'avg_score_4': '评委 4(top2)',
                                'avg_score_5': '评委 5(top)',
                                'avg_completion_tokens': '输出 Tokens',
                                'avg_total_time_s': '平均耗时 (s)',
                                'avg_tps': '生成速度 (tps)',
                                'avg_prompt_tps': '预读速度 (tps)'
                            }),
                            hide_index=True,
                            width='stretch'
                        )
        else:
            st.info("暂无模型统计数据。")

    with tab2:
        st.subheader("测试题汇总")
        df_case_summary = get_case_summary_stats(model_type_filter)
        if not df_case_summary.empty:
            for _, row in df_case_summary.iterrows():
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1.5])
                    col1.write(f"**测试题：{row['case_title']}**")
                    avg_score = row['avg_score']
                    col2.write(f"全模型平均分：**{avg_score:.2f}** / 100" if avg_score is not None else "全模型平均分：**N/A** / 100")
                    col3.write(f"总运行次数：{row['total_runs']}")

                    # 将按钮放到最右边的列
                    if col4.button("查看模型排名", key=f"case_rank_{row['case_id']}"):
                        st.session_state[f"show_rank_{row['case_id']}"] = not st.session_state.get(f"show_rank_{row['case_id']}", False)
                        st.rerun()

                    if st.session_state.get(f"show_rank_{row['case_id']}", False):
                        st.write("---")
                        df_ranking = get_case_model_ranking(row['case_id'], model_type_filter)
                        
                        # Format the display dataframe
                        display_df = df_ranking.copy()
                        
                        # Add color and icon to model names
                        def format_model_name(name):
                            if name.endswith('.gguf'):
                                return f"🖥️ {name}"
                            else:
                                return f"☁️ {name}"
                        
                        display_df['模型名称'] = display_df['model_name'].apply(format_model_name)
                        
                        # Create individual score columns for all 5 judges
                        display_df['评委 1(gem)'] = display_df['avg_score_1'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
                        display_df['评委 2(opus)'] = display_df['avg_score_2'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
                        display_df['评委 3(gpt)'] = display_df['avg_score_3'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
                        display_df['评委 4(top2)'] = display_df['avg_score_4'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
                        display_df['评委 5(top)'] = display_df['avg_score_5'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
                        
                        # Format execution time
                        display_df['平均执行时间'] = display_df['avg_total_time_ms'].apply(
                            lambda x: f"{x/1000:.2f}s" if pd.notna(x) else "N/A"
                        )
                        
                        st.dataframe(display_df[[ 
                            '模型名称',
                            '评委 1(gem)',
                            '评委 2(opus)',
                            '评委 3(gpt)',
                            '评委 4(top2)',
                            '评委 5(top)',
                            'avg_score',
                            '平均执行时间',
                            'run_count'
                        ]].rename(columns={
                            'avg_score': '综合平均分',
                            'run_count': '运行次数'
                        }), hide_index=True, width='stretch')
        else:
            st.info("暂无测试题统计数据。")

    with tab3:
        st.subheader("⏱️ 模型平均耗时排行 (毫秒)")
        df_speed = get_model_speed_ranking(model_type_filter)
        if not df_speed.empty:
            # Add icon to model names
            df_speed_display = df_speed.copy()
            df_speed_display['模型名称'] = df_speed_display['model_name'].apply(
                lambda name: f"🖥️ {name}" if name.endswith('.gguf') else f"☁️ {name}"
            )
            
            st.dataframe(
                df_speed_display[[
                    '模型名称',
                    'avg_total_time_ms',
                    'avg_tps',
                    'avg_prompt_tps',
                    'test_count'
                ]].rename(columns={
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