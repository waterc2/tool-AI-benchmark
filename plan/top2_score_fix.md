# Top2 评分修复计划

## 问题概述

当前 top2 评分未正确应用，存在以下问题：
1. `call_all_evaluators` 函数排除了 top2 评委调用
2. 平均分计算逻辑排除了 top2 分数
3. 重评映射缺少 top2
4. UI 缺少 top2 单独重评按钮

## 修复内容

### 1. 修复 [`llm_client.py`](llm_client.py:515) - 恢复 top2 评委调用

**位置**: `llm_client.py:515`

**当前代码**:
```python
levels = ["gem", "opus", "gpt", "top"] # 去掉 top2
```

**修改为**:
```python
levels = ["gem", "opus", "gpt", "top2", "top"]
```

### 2. 修复 [`database.py`](database.py:110) - 平均分包含 top2

**位置**: `database.py:110-111`

**当前代码**:
```python
# 去掉 top2 (score_4) 的评分计入平均分
scores = [score_1, score_2, score_3, score_5]
```

**修改为**:
```python
# 所有评委评分计入平均分 (gem, opus, gpt, top2, top)
scores = [score_1, score_2, score_3, score_4, score_5]
```

### 3. 修复 [`background_tasks.py`](background_tasks.py:76) - 重评映射添加 top2

**位置**: `background_tasks.py:76-81`

**当前代码**:
```python
level_mapping = {
    'gem': 'eval_score_1',
    'opus': 'eval_score_2',
    'gpt': 'eval_score_3',
    'top': 'eval_score_5'
}
```

**修改为**:
```python
level_mapping = {
    'gem': 'eval_score_1',
    'opus': 'eval_score_2',
    'gpt': 'eval_score_3',
    'top2': 'eval_score_4',
    'top': 'eval_score_5'
}
```

### 4. 修复 [`modules/history.py`](modules/history.py:44) - 统计 top2 失败数量

**位置**: `modules/history.py:44-53`

**当前代码**:
```python
failed_count = 0
for row in df_history.itertuples():
    if 'eval_score_1' in available_cols and (pd.isna(getattr(row, 'eval_score_1')) or getattr(row, 'eval_score_1') == 0):
        failed_count += 1
    if 'eval_score_2' in available_cols and (pd.isna(getattr(row, 'eval_score_2')) or getattr(row, 'eval_score_2') == 0):
        failed_count += 1
    if 'eval_score_3' in available_cols and (pd.isna(getattr(row, 'eval_score_3')) or getattr(row, 'eval_score_3') == 0):
        failed_count += 1
    if 'eval_score_5' in available_cols and (pd.isna(getattr(row, 'eval_score_5')) or getattr(row, 'eval_score_5') == 0):
        failed_count += 1
```

**修改为**:
```python
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
```

### 5. 修复 [`modules/history.py`](modules/history.py:62) - 自动重评包含 top2

**位置**: `modules/history.py:62-66`

**当前代码**:
```python
target_levels = []
if 'eval_score_1' in available_cols and (pd.isna(getattr(row, 'eval_score_1')) or getattr(row, 'eval_score_1') == 0): target_levels.append('gem')
If 'eval_score_2' in available_cols and (pd.isna(getattr(row, 'eval_score_2')) or getattr(row, 'eval_score_2') == 0): target_levels.append('opus')
If 'eval_score_3' in available_cols and (pd.isna(getattr(row, 'eval_score_3')) or getattr(row, 'eval_score_3') == 0): target_levels.append('gpt')
If 'eval_score_5' in available_cols and (pd.isna(getattr(row, 'eval_score_5')) or getattr(row, 'eval_score_5') == 0): target_levels.append('top')
```

**修改为**:
```python
target_levels = []
if 'eval_score_1' in available_cols and (pd.isna(getattr(row, 'eval_score_1')) or getattr(row, 'eval_score_1') == 0): target_levels.append('gem')
If 'eval_score_2' in available_cols and (pd.isna(getattr(row, 'eval_score_2')) or getattr(row, 'eval_score_2') == 0): target_levels.append('opus')
If 'eval_score_3' in available_cols and (pd.isna(getattr(row, 'eval_score_3')) or getattr(row, 'eval_score_3') == 0): target_levels.append('gpt')
If 'eval_score_4' in available_cols and (pd.isna(getattr(row, 'eval_score_4')) or getattr(row, 'eval_score_4') == 0): target_levels.append('top2')
If 'eval_score_5' in available_cols and (pd.isna(getattr(row, 'eval_score_5')) or getattr(row, 'eval_score_5') == 0): target_levels.append('top')
```

### 6. 新增 [`modules/history.py`](modules/history.py:78) - 强制 TOP2 评分按钮

**位置**: `modules/history.py:78-90`（在"强制 TOP 评分"按钮后添加）

**新增代码**:
```python
# 按钮 3: 强制 TOP2 重新评分 (不管有没有值)
if col_btn3.button("🔝 强制 TOP2 评分", help="对当前筛选出的所有记录，强制使用 TOP2 模型重新评分"):
    task_mgr = st.session_state.task_manager
    count = 0
    for row in df_history.itertuples():
        task_mgr.submit_re_evaluate(
            row.id, row.case_title, row.prompt, row.reference_answer, row.local_response, 
            target_levels=['top2']
        )
        count += 1
    st.success(f"已强制提交 {count} 条记录进行 TOP2 重新评分！")
    time.sleep(1)
    st.rerun()
```

### 7. 修复 [`modules/history.py`](modules/history.py:39) - 调整按钮列布局

**位置**: `modules/history.py:39`

**当前代码**:
```python
col_btn1, col_btn2, col_btn3, col_page, _ = st.columns([1.5, 1.5, 1.5, 2, 1])
```

**修改为**:
```python
col_btn1, col_btn2, col_btn3, col_btn4, col_page, _ = st.columns([1.5, 1.5, 1.5, 1.5, 2, 1])
```

**按钮对应关系**:
- `col_btn1`: 自动重新评分
- `col_btn2`: 强制 TOP 评分
- `col_btn3`: 强制 TOP2 评分（新增）
- `col_btn4`: （原 col_page 移到这里）

### 8. 修复 [`modules/history.py`](modules/history.py:141) - 显示 top2 分数

**位置**: `modules/history.py:141-145`

**当前代码**:
```python
gem_s = safe_int(getattr(row, 'eval_score_1', 0))
opus_s = safe_int(getattr(row, 'eval_score_2', 0))
gpt_s = safe_int(getattr(row, 'eval_score_3', 0))
top_s = safe_int(getattr(row, 'eval_score_5', 0))
r_col4.write(f"{total_score:.1f} ({gem_s},{opus_s},{gpt_s},{top_s})")
```

**修改为**:
```python
gem_s = safe_int(getattr(row, 'eval_score_1', 0))
opus_s = safe_int(getattr(row, 'eval_score_2', 0))
gpt_s = safe_int(getattr(row, 'eval_score_3', 0))
top2_s = safe_int(getattr(row, 'eval_score_4', 0))
top_s = safe_int(getattr(row, 'eval_score_5', 0))
r_col4.write(f"{total_score:.1f} ({gem_s},{opus_s},{gpt_s},{top2_s},{top_s})")
```

### 9. 修复 [`modules/history.py`](modules/history.py:153) - 单条重评包含 top2

**位置**: `modules/history.py:153-158`

**当前代码**:
```python
if btn_col2.button("🔄", key=f"re_eval_top_{record_id}", help="重新评分"):
    target_levels = []
    if gem_s == 0: target_levels.append('gem')
    if opus_s == 0: target_levels.append('opus')
    if gpt_s == 0: target_levels.append('gpt')
    if top_s == 0: target_levels.append('top')
```

**修改为**:
```python
if btn_col2.button("🔄", key=f"re_eval_top_{record_id}", help="重新评分"):
    target_levels = []
    if gem_s == 0: target_levels.append('gem')
    if opus_s == 0: target_levels.append('opus')
    if gpt_s == 0: target_levels.append('gpt')
    if top2_s == 0: target_levels.append('top2')
    if top_s == 0: target_levels.append('top')
```

### 10. 修复 [`modules/history.py`](modules/history.py:192) - 详细评语显示 top2

**位置**: `modules/history.py:192-196`

**当前代码**:
```python
c1, c2, c3, c5 = st.columns(4)
c1.metric("Gem", f"{gem_s}/100")
c2.metric("Opus", f"{opus_s}/100")
c3.metric("GPT", f"{gpt_s}/100")
c5.metric("Top", f"{top_s}/100")
```

**修改为**:
```python
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Gem", f"{gem_s}/100")
c2.metric("Opus", f"{opus_s}/100")
c3.metric("GPT", f"{gpt_s}/100")
c4.metric("TOP2", f"{top2_s}/100")
c5.metric("Top", f"{top_s}/100")
```

### 11. 修复 [`modules/history.py`](modules/history.py:198) - 评语内容显示 top2

**位置**: `modules/history.py:198-202`

**当前代码**:
```python
with st.expander("查看详细评语", expanded=True):
    st.markdown(f"**Gem:** {getattr(row, 'eval_comment_1', '无') or '无'}")
    st.markdown(f"**Opus:** {getattr(row, 'eval_comment_2', '无') or '无'}")
    st.markdown(f"**GPT:** {getattr(row, 'eval_comment_3', '无') or '无'}")
    st.markdown(f"**Top:** {getattr(row, 'eval_comment_5', '无') or '无'}")
```

**修改为**:
```python
with st.expander("查看详细评语", expanded=True):
    st.markdown(f"**Gem:** {getattr(row, 'eval_comment_1', '无') or '无'}")
    st.markdown(f"**Opus:** {getattr(row, 'eval_comment_2', '无') or '无'}")
    st.markdown(f"**GPT:** {getattr(row, 'eval_comment_3', '无') or '无'}")
    st.markdown(f"**TOP2:** {getattr(row, 'eval_comment_4', '无') or '无'}")
    st.markdown(f"**Top:** {getattr(row, 'eval_comment_5', '无') or '无'}")
```

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| [`llm_client.py`](llm_client.py:515) | 恢复 top2 到 levels 列表 |
| [`database.py`](database.py:110) | 平均分计算包含 score_4 |
| [`background_tasks.py`](background_tasks.py:76) | level_mapping 添加 top2 |
| [`modules/history.py`](modules/history.py:44) | 统计失败数量包含 eval_score_4 |
| [`modules/history.py`](modules/history.py:62) | 自动重评包含 top2 |
| [`modules/history.py`](modules/history.py:39) | 按钮列布局调整 |
| [`modules/history.py`](modules/history.py:78) | 新增强制 TOP2 评分按钮 |
| [`modules/history.py`](modules/history.py:141) | 显示 top2 分数 |
| [`modules/history.py`](modules/history.py:153) | 单条重评包含 top2 |
| [`modules/history.py`](modules/history.py:192) | 详细评语显示 top2 |
| [`modules/history.py`](modules/history.py:198) | 评语内容包含 top2 |

## 执行步骤

1. 切换到 **Code** 模式
2. 按顺序修改上述文件
3. 测试验证 top2 评分功能
