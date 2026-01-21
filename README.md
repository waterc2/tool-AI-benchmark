# Local LLM Code Benchmarker (本地模型编程能力测试工具)

这是一个用于自动化测试和评估本地大语言模型（LLM）编程能力的工具。它支持多文件上下文管理、思维链（CoT）提取，并利用评委大模型进行自动评分。

## 🚀 核心功能

- **用例管理**：支持多文件代码上下文，方便管理复杂的编程测试任务。
- **自动化评测**：批量调用本地模型，捕获生成代码、思维链、Token 消耗及生成速度。
- **智能评分**：集成评委大模型（如 GPT-4），根据参考答案对模型输出进行 0-10 分的量化评估。
- **历史对比**：详尽的评测记录，支持按用例查看多次测试的性能指标和评分反馈。

## 🛠️ 技术栈

- **UI**: Streamlit
- **数据库**: SQLite
- **API 调用**: LiteLLM / OpenAI SDK
- **语言**: Python

## 📦 安装与运行

### 1. 克隆项目
```bash
git clone <repository-url>
cd tool-AI-benchmark
```

### 2. 安装依赖
建议使用虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Windows 使用: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量
复制 `.env.example` 并重命名为 `.env`，填入您的配置：
```bash
cp .env.example .env
```
主要配置项：
- `LOCAL_MODEL_URL`: 本地模型的 API 地址（默认：http://10.0.0.114:8080/v1）。
- `EVALUATOR_API_KEY`: 评委大模型（如 OpenAI）的 API Key。
- `EVALUATOR_BASE_URL`: 评委模型的 API 代理地址（可选）。

### 4. 启动应用
```bash
streamlit run app.py
```

## 📖 使用指南

1. **用例管理**：在侧边栏选择“用例管理”，可以新建测试用例。支持输入 JSON 格式的多文件字典或纯文本代码。
2. **执行测试**：勾选想要测试的用例，设置生成温度（Temperature），点击“开始批量测试”。
3. **历史记录**：查看所有评测的统计数据，点击特定记录可查看本地模型的完整回答、思维链以及评委的具体评语。

## 📂 项目结构

- `app.py`: Streamlit 主程序，负责 UI 交互。
- `database.py`: 数据库操作逻辑（CRUD）。
- `llm_client.py`: 封装本地模型和评委模型的 API 调用。
- `init_db.py`: 数据库初始化脚本。
- `AI_AGENTS.md`: 项目需求说明书与开发进度跟踪。
