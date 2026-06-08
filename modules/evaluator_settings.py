"""评分模型设置页面模块."""

import os
import time
import re
import threading
import streamlit as st
import config
from database import get_evaluator_stats, clear_cache
from llm_client import call_evaluator
from dotenv import dotenv_values, load_dotenv

# 文件锁保护 .env 并发修改
_env_lock = threading.Lock()


# 评分模型配置映射 - 每个模型使用独立的环境变量
EVALUATOR_CONFIG_MAP = [
    {
        'level': 'gem',
        'display_name': 'Gem',
        'url_key': 'EVALUATOR_GEM_BASE_URL',
        'key_key': 'EVALUATOR_GEM_API_KEY',
        'model_key': 'EVALUATOR_MODEL_GEM',
    },
    {
        'level': 'opus',
        'display_name': 'Opus',
        'url_key': 'EVALUATOR_OPUS_BASE_URL',
        'key_key': 'EVALUATOR_OPUS_API_KEY',
        'model_key': 'EVALUATOR_MODEL_OPUS',
    },
    {
        'level': 'gpt',
        'display_name': 'GPT',
        'url_key': 'EVALUATOR_GPT_BASE_URL',
        'key_key': 'EVALUATOR_GPT_API_KEY',
        'model_key': 'EVALUATOR_MODEL_GPT',
    },
    {
        'level': 'top2',
        'display_name': 'Top2',
        'url_key': 'EVALUATOR_TOP2_BASE_URL',
        'key_key': 'EVALUATOR_TOP2_API_KEY',
        'model_key': 'EVALUATOR_MODEL_TOP2',
    },
    {
        'level': 'top',
        'display_name': 'Top',
        'url_key': 'EVALUATOR_TOP_BASE_URL',
        'key_key': 'EVALUATOR_TOP_API_KEY',
        'model_key': 'EVALUATOR_MODEL_TOP',
    },
]


def get_env_value(key):
    """直接从 .env 文件获取值（不依赖进程环境变量）
    
    这样修改 .env 文件后不需要重启服务就能读到新值
    """
    # 直接从 .env 文件读取
    env_values = dotenv_values('.env')
    return env_values.get(key, '') or os.getenv(key, '')


def update_env_file(key, value):
    """更新 .env 文件中的指定变量（线程安全）
    
    Args:
        key: 环境变量名
        value: 新的值
    """
    env_file = '.env'
    
    with _env_lock:
        # 读取现有内容
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # 查找并更新或追加
        found = False
        for i, line in enumerate(lines):
            if line.startswith(key + '='):
                lines[i] = f'{key}="{value}"\n'
                found = True
                break
        
        if not found:
            lines.append(f'{key}="{value}"\n')
        
        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    # 重新加载环境变量使新配置立即生效
    load_dotenv(env_file, override=True)
    config.reload_config()


def test_evaluator_connection(level, api_base, api_key, model_id):
    """测试评分模型连接（直接使用传入的参数，不依赖 config 模块）
    
    Args:
        level: 模型标识 (gem/opus/gpt/top2/top)
        api_base: API 地址
        api_key: API 密钥
        model_id: 模型ID
    
    Returns:
        dict: {'success': bool, 'message': str, 'response_time': float}
    """
    from openai import OpenAI
    import re
    from llm_client import get_evaluator_system_prompt, get_evaluator_user_content
    
    test_prompt = "这是一个测试连接请求。"
    test_reference = "这是参考答案。"
    test_response = "这是本地模型的回答。"
    
    # 使用统一的提示词函数，避免重复定义
    system_prompt = get_evaluator_system_prompt(level)
    user_content = get_evaluator_user_content(test_prompt, test_reference, test_response)
    
    try:
        start_time = time.time()
        client = OpenAI(api_key=api_key, base_url=api_base, timeout=180.0)
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            stream=False
        )
        
        response_time = time.time() - start_time
        content = response.choices[0].message.content
        
        # 提取评分
        score_match = re.search(r'<score>\s*(\d+)\s*</score>', content, re.DOTALL | re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))
            return {
                'success': True,
                'message': f'✓ 连接成功，评分: {score}',
                'response_time': round(response_time, 2)
            }
        else:
            return {
                'success': False,
                'message': f'✗ 响应格式不正确，未找到评分。响应: {content[:100]}',
                'response_time': round(response_time, 2)
            }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            'success': False,
            'message': f'✗ 连接失败: {str(e)[:200]}',
            'response_time': round(response_time, 2)
        }


def render_evaluator_settings():
    """渲染评分模型设置页面"""
    st.title("⚙️ 评分模型设置")
    st.markdown("管理和配置5个评分模型的API信息，并查看每个模型的平均评分统计。")
    
    # 获取统计数据
    evaluator_stats = get_evaluator_stats()
    
    # 创建统计数据映射
    stats_map = {stat['level']: stat for stat in evaluator_stats}
    
    # 显示模型列表
    st.header("📊 评分模型列表")
    
    # 准备表格数据
    table_data = []
    for cfg in EVALUATOR_CONFIG_MAP:
        level = cfg['level']
        stat = stats_map.get(level, {'avg_score': 0, 'count': 0})
        
        # 获取当前配置值
        api_url = get_env_value(cfg['url_key']) or getattr(config, cfg['url_key'], '')
        api_key = get_env_value(cfg['key_key']) or getattr(config, cfg['key_key'], '')
        model_id = get_env_value(cfg['model_key']) or getattr(config, cfg['model_key'], '')
        
        # 隐藏 API Key
        display_key = '****' + api_key[-4:] if api_key and len(api_key) > 4 else ''
        
        table_data.append({
            '模型': cfg['display_name'],
            '级别': level,
            'API 地址': api_url[:50] + '...' if len(api_url) > 50 else api_url,
            '模型名称': model_id,
            '平均评分': stat['avg_score'],
            '评分次数': stat['count'],
            'has_key': bool(api_key)
        })
    
    # 显示表格 - 按平均分排序
    import pandas as pd
    df = pd.DataFrame(table_data)
    df = df.sort_values('平均评分', ascending=False)
    st.dataframe(df, width='stretch', hide_index=True)
    
    st.divider()
    
    # 编辑功能
    st.header("✏️ 编辑配置")
    
    # 选择要编辑的模型
    selected_level = st.selectbox(
        "选择要编辑的评分模型",
        options=[cfg['level'] for cfg in EVALUATOR_CONFIG_MAP],
        format_func=lambda x: next(cfg['display_name'] for cfg in EVALUATOR_CONFIG_MAP if cfg['level'] == x)
    )
    
    # 获取选中模型的配置
    selected_cfg = next(cfg for cfg in EVALUATOR_CONFIG_MAP if cfg['level'] == selected_level)
    
    # 获取当前值
    current_url = get_env_value(selected_cfg['url_key']) or getattr(config, selected_cfg['url_key'], '')
    current_key = get_env_value(selected_cfg['key_key']) or getattr(config, selected_cfg['key_key'], '')
    current_model = get_env_value(selected_cfg['model_key']) or getattr(config, selected_cfg['model_key'], '')
    
    # 创建编辑表单
    with st.form(key=f"evaluator_form_{selected_level}"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            new_url = st.text_input(
                "API 地址",
                value=current_url,
                help="API 的基础地址，例如: https://openrouter.ai/api/v1"
            )
            new_model = st.text_input(
                "模型名称",
                value=current_model,
                help="模型 ID，例如: gpt-4"
            )
        
        with col2:
            new_key = st.text_input(
                "API Key",
                value=current_key,
                type="password",
                help="API 密钥"
            )
            # 保留原 Key 的选项
            keep_key = st.checkbox("保留原 Key", value=False)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            submitted = st.form_submit_button("💾 保存")
        with col2:
            test_btn = st.form_submit_button("🔌 测试连接")
        with col3:
            reset_btn = st.form_submit_button("↩️ 重置")
        
        # 处理重置
        if reset_btn:
            st.rerun()
        
        # 处理测试连接
        if test_btn:
            test_url = new_url if new_url else current_url
            test_key = new_key if new_key else current_key
            test_model = new_model if new_model else current_model
            
            if not test_url:
                st.error("请输入 API 地址")
            elif not test_key:
                st.error("请输入 API Key")
            elif not test_model:
                st.error("请输入模型名称")
            else:
                with st.spinner("正在测试连接..."):
                    result = test_evaluator_connection(selected_level, test_url, test_key, test_model)
                
                if result['success']:
                    st.success(f"{result['message']} (响应时间: {result['response_time']}s)")
                else:
                    st.error(f"{result['message']} (响应时间: {result['response_time']}s)")
        
        # 处理保存
        if submitted:
            if not new_url:
                st.error("请输入 API 地址")
            elif not new_model:
                st.error("请输入模型名称")
            else:
                # 更新配置
                update_env_file(selected_cfg['url_key'], new_url)
                update_env_file(selected_cfg['model_key'], new_model)
                
                if not keep_key and new_key:
                    update_env_file(selected_cfg['key_key'], new_key)
                
                # 清除缓存
                clear_cache()
                
                st.success(f"✓ {selected_cfg['display_name']} 模型配置已保存！配置已立即生效。")
                clear_cache()
                st.rerun()
    
    st.divider()
    
    # 说明信息
    st.header("📖 说明")
    st.markdown("""
    - **评分模型** 用于对本地模型的输出进行评分
    - **平均评分** 是该模型对所有测试用例打分的平均值（忽略 0 分）
    - **测试连接** 会发送一个测试请求到模型，验证是否可以正常返回数据
    - 配置保存在 `.env` 文件中，修改后**立即生效**，无需重启服务
    - API Key 输入框默认隐藏内容，保护敏感信息
    """)
