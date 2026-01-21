📋 项目需求说明书 (PRD) - v2.0
1. 项目概况
名称：Local LLM Code Benchmarker (本地模型编程能力测试工具)

目标：通过管理真实的编程测试用例（Test Cases），自动化测试本地模型的代码生成能力，并使用大模型（评委）进行评分和分析。

技术栈：Python, Streamlit (UI), SQLite (数据库), LiteLLM/OpenAI SDK (API 调用)。

2. 核心功能流程
用例管理：
- 用户可以新建、编辑和管理“测试用例”。
- 每个用例包含：标题、类型、源代码（支持多文件上下文）、修改要求（提示词）、参考答案。

执行环节：
- 用户选择一个或多个用例进行批量测试。
- 调用本地模型 (默认地址: http://10.0.0.114:8080/v1)。
- 捕获：代码回答、思维链内容（Chain of Thought）、Token 数、耗时、生成速度。

评测环节：
- 将“参考答案”与“本地模型回答”发送给评委大模型。
- 评委返回：0-10 的评分和具体的评价意见。

存储与展示：
- 数据持久化至 SQLite。
- 提供历史记录页面，支持按用例查看多次测试的对比。

3. 数据库设计
表 1: test_cases (测试用例表)
- id, title, category, source_code (JSON格式存储多文件), prompt, reference_answer, created_at

表 2: eval_records (评测记录表)
- id, case_id (外键), model_name, local_response, chain_of_thought, prompt_tokens, completion_tokens, total_time_ms, tokens_per_second, eval_score, eval_comment, created_at

🛠️ 分阶段开发计划
第一阶段：数据库架构升级
- [x] 任务 1：更新 init_db.py，创建 test_cases 表并重构 eval_records 表。
- [x] 任务 2：编写 database.py，实现用例的 CRUD 和记录的保存。

第二阶段：API 客户端增强
- [x] 任务 1：更新 llm_client.py，适配新的本地模型 URL (10.0.0.114:8080)。
- [x] 任务 2：实现思维链（CoT）提取逻辑（解析 <think> 标签）。

第三阶段：UI 界面重构
- [x] 任务 1：在 app.py 中实现侧边栏导航（用例管理、执行测试、历史记录）。
- [x] 任务 2：开发用例管理界面，支持多文件代码输入。
- [x] 任务 3：开发批量测试界面，包含进度条 and 实时结果展示。
- [x] 任务 4：实现测试用例的编辑功能。

第四阶段：完善与文档
- [x] 任务 1：补充历史记录的详细对比视图。
- [x] 任务 2：更新 README.md 提供运行指南。

第五阶段：统计与分析 (新增)
- [x] 任务 1：实现以模型为单位的平均分统计及各题详情。
- [x] 任务 2：实现以测试题为单位的全模型平均分统计及模型排名。
