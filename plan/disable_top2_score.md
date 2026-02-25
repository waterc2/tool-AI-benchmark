# 禁用 Top2 评分模型计划

## 目标
将评分模型里的 top2 注解掉，不使用 top2 进行评分，不显示 top2 的评分，也不把 top2 的评分计入平均分的计算。

## 当前状态
- 评分系统使用 5 个评委：gem, opus, gpt, top2, top
- 对应数据库字段：eval_score_1 到 eval_score_5
- 映射关系：1=gem, 2=opus, 3=gpt, 4=top2, 5=top
- 平均分计算包含所有有效分数（非 0 分）

## 修改方案

### 1. 修改 [`database.py`](database.py:113) - 平均分计算排除 top2

**位置**: `update_eval_scores` 函数，第 113 行

**当前代码**:
```python
# 计算有效分数（忽略 0 分，即忽略失败的评测）
# 所有评委评分计入平均分 (gem, opus, gpt, top2, top)
scores = [score_1, score_2, score_3, score_4, score_5]
valid_scores = [s for s in scores if s > 0]
```

**修改为**:
```python
# 计算有效分数（忽略 0 分，即忽略失败的评测）
# 排除 top2 (score_4) 的评分计入平均分 (gem, opus, gpt, top)
scores = [score_1, score_2, score_3, score_5]  # 排除 score_4 (top2)
valid_scores = [s for s in scores if s > 0]
```

### 2. 修改 [`llm_client.py`](llm_client.py:516) - 移除 top2 评委调用

**位置**: `call_all_evaluators` 函数，第 516 行

**当前代码**:
```python
levels = ["gem", "opus", "gpt", "top2", "top"]
```

**修改为**:
```python
# top2 已禁用，不参与评分
levels = ["gem", "opus", "gpt", "top"]
```

### 3. 修改 [`database.py`](database.py:253) - 统计查询排除 top2

需要检查 `get_eval_stats` 函数中的平均分统计是否也需要调整。

## 执行步骤

1. 修改 [`database.py`](database.py:113) - 排除 top2 分数参与平均分计算
2. 修改 [`llm_client.py`](llm_client.py:516) - 移除 top2 评委调用
3. 验证修改后逻辑正确性

## 注意事项

- 数据库字段 `eval_score_4` 和 `eval_comment_4` 仍会保留，但不会被使用
- 历史数据中的 top2 评分将不再影响平均分
- 此修改不影响其他评委 (gem, opus, gpt, top) 的评分逻辑
