# 评分模型设置功能 - 实现计划

## 概述
添加一个新菜单"评分模型设置"，用于管理和配置5个评分模型（Gem, Opus, GPT, Top2, Top）的API信息，并显示每个模型的平均评分统计。

## 当前系统架构

### 评分模型配置
目前5个评分模型的定义在 [`config.py`](config.py) 中：

| 模型标识 | 配置变量 | API URL 配置 | API Key 配置 |
|---------|---------|-------------|-------------|
| gem | `EVALUATOR_MODEL_GEM` | `EVALUATOR_BASE_URL` | `EVALUATOR_API_KEY` |
| opus | `EVALUATOR_MODEL_OPUS` | `EVALUATOR_BASE_URL` | `EVALUATOR_API_KEY` |
| gpt | `EVALUATOR_MODEL_GPT` | `EVALUATOR_OPENROUTER_BASE_URL` | `EVALUATOR_OPENROUTER_API_KEY` |
| top2 | `EVALUATOR_MODEL_TOP2` | `EVALUATOR_TOP2_BASE_URL` | `EVALUATOR_TOP2_API_KEY` |
| top | `EVALUATOR_MODEL_TOP` | `EVALUATOR_OPENROUTER_BASE_URL` | `EVALUATOR_OPENROUTER_API_KEY` |

### 评分数据存储
- 数据库表: `eval_records`
- 评分字段: `eval_score_1` 到 `eval_score_5`
- 对应关系: 1=gem, 2=opus, 3=gpt, 4=top2, 5=top

### 模型调用逻辑
在 [`llm_client.py`](llm_client.py:263-302) 中：
- [`get_evaluator_model_name()`](llm_client.py:263) - 根据标识获取模型ID
- [`call_evaluator()`](llm_client.py:280) - 调用单个评委模型
- [`call_all_evaluators()`](llm_client.py:507) - 并行调用所有评委

## 实现步骤

### 1. 数据库层 - 新增函数
**文件**: `database.py`

添加以下函数：

```python
def get_evaluator_stats():
    """获取所有评分模型的统计信息（平均评分）"""
    # 返回每个模型的：
    # - 评分次数（非0评分的记录数）
    # - 平均评分（忽略0分）
    # SQL 示例:
    # SELECT 
    #   COUNT(CASE WHEN eval_score_1 > 0 THEN 1 END) as gem_count,
    #   AVG(CASE WHEN eval_score_1 > 0 THEN eval_score_1 END) as gem_avg,
    #   ... (对其他模型同理)
    # FROM eval_records
```

### 2. 新增 UI 页面模块
**文件**: `modules/evaluator_settings.py` (新建)

实现 `render_evaluator_settings()` 函数，功能包括：

#### 2.1 显示评分模型列表
- 使用 Streamlit 的 `st.dataframe` 或表格显示
- 列包括:
  - 模型标识 (gem/opus/gpt/top2/top)
  - API 地址
  - 模型名称
  - 平均评分（从数据库获取）
  - 评分次数
  - 操作按钮（编辑/测试）

#### 2.2 编辑功能
- 使用 `st.expander` 或弹窗形式
- 可编辑字段:
  - API 地址 (Base URL)
  - API Key
  - 模型 ID (Model ID)
- 保存按钮 - 更新 `.env` 文件或配置

#### 2.3 测试连接功能
- 测试按钮 - 调用 [`call_evaluator()`](llm_client.py:280) 函数
- 发送简单的测试请求验证连接
- 显示测试结果（成功/失败及错误信息）

### 3. 更新侧边栏菜单
**文件**: `modules/sidebar.py`

修改 [`render_sidebar()`](modules/sidebar.py:8) 函数：
```python
menu = st.radio("菜单", ["用例管理", "执行测试", "历史记录", "统计分析", "评分模型设置"])
```

### 4. 更新主应用路由
**文件**: `app.py`

添加新页面的导入和路由：
```python
from ui_pages import ..., render_evaluator_settings

if menu == "评分模型设置":
    render_evaluator_settings()
```

### 5. 更新 UI 导出模块
**文件**: `ui_pages.py`

添加新页面的导出：
```python
from modules.evaluator_settings import render_evaluator_settings
```

## 配置持久化方案

### 方案选择
评分模型配置存储在 `.env` 文件中，通过 `config.py` 读取。

编辑配置时，需要更新 `.env` 文件中的对应环境变量：
- `EVALUATOR_BASE_URL`
- `EVALUATOR_API_KEY`
- `EVALUATOR_MODEL_GEM`
- `EVALUATOR_MODEL_OPUS`
- `EVALUATOR_OPENROUTER_BASE_URL`
- `EVALUATOR_OPENROUTER_API_KEY`
- `EVALUATOR_MODEL_GPT`
- `EVALUATOR_MODEL_TOP`
- `EVALUATOR_TOP2_BASE_URL`
- `EVALUATOR_TOP2_API_KEY`
- `EVALUATOR_MODEL_TOP2`

### 更新 .env 文件的函数
在 `database.py` 或新建 `config_manager.py` 中添加：
```python
def update_env_variable(key, value):
    """更新 .env 文件中的指定变量"""
    # 读取 .env 文件
    # 查找并更新对应键的值
    # 如果键不存在，则追加
    # 写回文件
```

## 测试连接实现

```python
def test_evaluator_connection(level, api_base, api_key, model_id):
    """
    测试评分模型连接
    
    Args:
        level: 模型标识 (gem/opus/gpt/top2/top)
        api_base: API 地址
        api_key: API 密钥
        model_id: 模型ID
    
    Returns:
        dict: {'success': bool, 'message': str, 'response_time': float}
    """
    # 使用 call_evaluator 发送测试请求
    # 简单的测试 prompt
    test_prompt = "测试连接"
    test_reference = "测试参考"
    test_response = "测试响应"
    
    try:
        start_time = time.time()
        result = call_evaluator(test_prompt, test_reference, test_response, level)
        response_time = time.time() - start_time
        
        return {
            'success': True,
            'message': f'连接成功，评分: {result.get("score", "N/A")}',
            'response_time': response_time
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'连接失败: {str(e)}',
            'response_time': 0
        }
```

## 文件修改清单

| 文件 | 操作 | 说明 |
|-----|------|------|
| `database.py` | 修改 | 添加 `get_evaluator_stats()` 函数 |
| `modules/evaluator_settings.py` | 新建 | 评分模型设置页面 |
| `modules/sidebar.py` | 修改 | 添加新菜单项 |
| `app.py` | 修改 | 添加新页面路由 |
| `ui_pages.py` | 修改 | 导出新页面函数 |
| `config.py` | 可选修改 | 添加配置更新函数 |

## UI 设计草图

```
┌─────────────────────────────────────────────────────────────┐
│  评分模型设置                                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────┬─────────────┬──────────┬────────┬────────┬──────┐ │
│  │ 模型 │ API 地址    │ 模型名称  │ 平均分  │ 评分次数 │ 操作 │ │
│  ├─────┼─────────────┼──────────┼────────┼────────┼──────┤ │
│  │ gem │ http://...  │ Gem      │ 85.5   │ 120    │ 编辑 │ │
│  │opus │ http://...  │ Opus     │ 82.3   │ 118    │ 编辑 │ │
│  │ gpt │ https://... │ poolside │ 78.9   │ 115    │ 编辑 │ │
│  │top2 │ https://... │ mimo-v2  │ 80.1   │ 119    │ 编辑 │ │
│  │ top │ https://... │ hy3-prev │ 76.4   │ 117    │ 编辑 │ │
│  └─────┴─────────────┴──────────┴────────┴────────┴──────┘ │
│                                                             │
│  ── 编辑 gem 模型 ──                                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ API 地址: [http://127.0.0.1:4000_____________]          ││
│  │ API Key:  [sk-xxxxxxxxxxxxxxxxxxxxxxxx________]         ││
│  │ 模型名称:  [Gem_______________________________]          ││
│  │                                                     [测试]││
│  │ 测试结果: ✓ 连接成功 (响应时间: 1.2s)                   ││
│  │                                              [保存] [取消]││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 注意事项

1. **安全性**: API Key 应使用 `type="password"` 的输入框
2. **配置热更新**: 修改配置后需要重新加载 `config.py` 或使用新的值
3. **错误处理**: 测试连接时需要有合理的超时和错误提示
4. **数据验证**: 保存前验证 API 地址格式
5. **排序**: 默认按平均分降序排列

## 依赖关系

- 无新增外部依赖
- 使用现有 Streamlit 组件
- 复用 `llm_client.py` 中的调用逻辑
