# BLUEPRINT: 本地模型串行评测改造

## 1. 问题分析

### 当前架构
- [`BackgroundTaskManager`](background_tasks.py:12) 使用 [`ThreadPoolExecutor`](background_tasks.py:25) (`llm_executor`) 并发执行测试任务
- `max_workers=5` 意味着最多同时执行 5 个 LLM 调用
- 任务通过 [`run_batch_test()`](background_tasks.py:198) 提交到线程池并发执行

### 问题
- **本地模型**（如 llama.cpp）通常资源有限（GPU/CPU），并发请求会导致：
  - 资源竞争，性能下降
  - 内存溢出或服务崩溃
  - 响应超时
- **远端模型** 有服务端负载均衡，可以安全并发

## 2. 解决方案

### 核心思路
根据模型类型动态选择执行策略：
- **本地模型** → 串行执行（一个一个任务测试）
- **远端模型** → 并发执行（保持现有逻辑）

### 判断本地模型的依据
参考 [`llm_client.py:125-126`](llm_client.py:125) 的现有逻辑：
```python
local_keywords = ['localhost', '127.0.0.1', '10.', '192.168.', '0.0.0.0']
is_local = any(kw in api_base for kw in local_keywords)
```

## 3. 修改计划

### 3.1 新增辅助函数

**文件**: `background_tasks.py`

在文件顶部添加判断函数：
```python
def is_local_model(api_base):
    """判断是否为本地模型（基于 API 地址）"""
    if not api_base:
        return True  # 无 API 地址时默认使用本地配置
    
    local_keywords = ['localhost', '127.0.0.1', '10.', '192.168.', '0.0.0.0']
    return any(kw in api_base for kw in local_keywords)
```

### 3.2 修改 `run_batch_test` 方法

**文件**: `background_tasks.py`  
**位置**: [`run_batch_test()`](background_tasks.py:198)

**修改逻辑**:
```python
def run_batch_test(self, selected_cases, api_base=None, api_key=None, model_id=None):
    # ... 现有初始化代码 ...
    
    # 判断是否为本地模型
    local_model = is_local_model(api_base)
    
    if local_model:
        # 本地模型：串行执行
        self.add_log("📍 检测到本地模型，采用串行执行模式")
        for idx, case in enumerate(selected_cases):
            if self.stop_requested:
                self.add_log("🛑 任务被用户停止")
                break
            
            success = self.process_single_case(case, api_base, api_key, model_id)
            if success:
                self.completed_cases += 1
            else:
                self.failed_cases += 1
                self.completed_cases += 1
            
            self.progress = self.completed_cases / self.total_cases
    else:
        # 远端模型：并发执行（保持现有逻辑）
        self.add_log("🌐 检测到远端模型，采用并发执行模式")
        futures = {}
        for idx, case in enumerate(selected_cases):
            # ... 现有并发逻辑 ...
```

### 3.3 完整修改对比

| 区域 | 当前代码 | 修改后 |
|------|----------|--------|
| 第 198-264 行 | 统一并发执行 | 根据模型类型分支 |
| 本地模型路径 | N/A | 串行调用 `process_single_case` |
| 远端模型路径 | 现有并发逻辑 | 保持不变 |

## 4. 详细代码变更

### 4.1 新增函数位置
在 [`BackgroundTaskManager`](background_tasks.py:12) 类定义之前添加：

```python
def is_local_model(api_base):
    """
    判断是否为本地模型（基于 API 地址）
    
    Args:
        api_base: API 基础地址
        
    Returns:
        bool: True 表示本地模型，False 表示远端模型
    """
    if not api_base:
        return True  # 无 API 地址时默认使用本地配置
    
    local_keywords = ['localhost', '127.0.0.1', '10.', '192.168.', '0.0.0.0']
    return any(kw in api_base for kw in local_keywords)
```

### 4.2 `run_batch_test` 方法重构

将现有的并发逻辑包装在 `if not local_model:` 分支中，并添加串行执行分支：

```python
def run_batch_test(self, selected_cases, api_base=None, api_key=None, model_id=None):
    print(f"\n[DEBUG] BackgroundTaskManager.run_batch_test started with {len(selected_cases)} cases")
    print(f"[DEBUG] Params: base={api_base}, model={model_id}")
    
    self.is_running = True
    self.stop_requested = False
    self.progress = 0.0
    self.completed_cases = 0
    self.total_cases = len(selected_cases)
    self.logs = []
    
    # 判断是否为本地模型
    local_model = is_local_model(api_base)
    execution_mode = "串行" if local_model else "并发"
    self.add_log(f"🔧 执行模式: {execution_mode} (模型地址: {api_base or '本地默认'})")
    
    if local_model:
        # ========== 本地模型：串行执行 ==========
        for idx, case in enumerate(selected_cases):
            if self.stop_requested:
                self.add_log("🛑 任务被用户停止")
                break
            
            self.add_log(f"📋 处理用例 {idx + 1}/{self.total_cases}")
            success = self.process_single_case(case, api_base, api_key, model_id)
            
            if success:
                self.completed_cases += 1
            else:
                self.failed_cases += 1
                self.completed_cases += 1
            
            self.progress = self.completed_cases / self.total_cases
        
        self.is_running = False
        self.status = f"测试完成，等待评分 ({self.completed_evals}/{self.pending_evals})"
        self.progress = 1.0
        
    else:
        # ========== 远端模型：并发执行 ==========
        futures = {}
        
        for idx, case in enumerate(selected_cases):
            if self.stop_requested:
                self.add_log("🛑 任务被用户停止")
                break

            future = self.llm_executor.submit(
                self.process_single_case, 
                case, 
                api_base, 
                api_key, 
                model_id
            )
            futures[future] = idx
            
            if idx < len(selected_cases) - 1 and not self.stop_requested:
                time.sleep(2)

        for future in as_completed(futures):
            if self.stop_requested:
                future.cancel()
                break
            
            try:
                success = future.result()
                if success:
                    self.completed_cases += 1
                else:
                    self.failed_cases += 1
                    self.completed_cases += 1
            except Exception as e:
                self.add_log(f"❌ 任务执行异常：{str(e)}")
                self.failed_cases += 1
                self.completed_cases += 1
            
            self.progress = self.completed_cases / self.total_cases

        self.is_running = False
        self.status = f"测试完成，等待评分 ({self.completed_evals}/{self.pending_evals})"
        self.progress = 1.0
    
    # 显示最终统计
    if self.failed_cases > 0:
        self.status = f"部分失败 ({self.failed_cases}/{self.total_cases})"
        self.add_log(f"⚠️  测试完成：{self.total_cases} 个用例，成功 {self.completed_cases - self.failed_cases} 个，失败 {self.failed_cases} 个，评分 {self.completed_evals} 个")
    else:
        self.status = "全部完成"
        self.add_log(f"🎉 所有任务完成！共测试 {self.total_cases} 个用例，评分 {self.completed_evals} 个")
```

## 5. 影响范围

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `background_tasks.py` | 修改 | 添加判断函数，重构 `run_batch_test` |
| `modules/test_runner.py` | 无变更 | 调用接口保持不变 |
| `llm_client.py` | 无变更 | 现有判断逻辑可复用 |

## 6. 测试要点

1. **本地模型测试**：
   - 选择"本地"模型来源
   - 验证日志显示"串行执行模式"
   - 确认任务一个接一个执行

2. **远端模型测试**：
   - 选择 OpenRouter/NVIDIA/Qwen 等远端服务
   - 验证日志显示"并发执行模式"
   - 确认多个任务并发执行

3. **边界情况**：
   - `api_base=None` 时默认为本地模型
   - 停止任务功能在两种模式下都正常工作