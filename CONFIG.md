# 配置说明 (Configuration Guide)

## 快速开始

1. **复制环境变量示例文件**
   ```bash
   cp .env.example .env
   ```

2. **编辑 `.env` 文件，填入您的 API 密钥**
   ```bash
   # 评委模型配置
   EVALUATOR_API_KEY=your_actual_api_key_here
   
   # 本地/远程模型配置
   LOCAL_MODEL_KEY=your_actual_api_key_here
   ```

3. **配置文件说明**
   - `.env` - 您的实际配置文件（包含真实的 API 密钥，已被 git 忽略）
   - `.env.example` - 配置模板文件（不包含真实密钥，可以提交到 git）
   - `config.py` - 配置加载模块（从 .env 读取配置，已被 git 忽略）

## 安全提示

⚠️ **重要**: 请勿将包含真实 API 密钥的文件提交到 git！

以下文件已自动被 `.gitignore` 排除：
- `.env` - 环境变量文件
- `config.py` - 配置文件（如果您修改了它）
- `*_backup_*.db` - 数据库备份文件

## 配置项说明

### 评委模型配置
用于自动评分本地模型的输出质量。

- `EVALUATOR_BASE_URL`: 评委模型的 API 地址
- `EVALUATOR_API_KEY`: 评委模型的 API 密钥
- `EVALUATOR_MODEL_SUPER`: 超级评委模型名称
- `EVALUATOR_MODEL_HIGH`: 高级评委模型名称
- `EVALUATOR_MODEL_LOW`: 低级评委模型名称

### 本地模型配置
默认使用的模型 API 配置。

- `LOCAL_MODEL_URL`: 模型 API 地址（可以是本地 llama.cpp 或远程 API）
- `LOCAL_MODEL_KEY`: 模型 API 密钥
- `LOCAL_MODEL_ID`: 模型名称或 ID

### 示例配置

#### 使用本地 llama.cpp
```bash
LOCAL_MODEL_URL=http://10.0.0.114:8080/v1
LOCAL_MODEL_KEY=any
LOCAL_MODEL_ID=your-model-name.gguf
```

#### 使用 OpenRouter
```bash
LOCAL_MODEL_URL=https://openrouter.ai/api/v1
LOCAL_MODEL_KEY=sk-or-v1-xxxxxxxxxxxxx
LOCAL_MODEL_ID=z-ai/glm-4.5-air:free
```

## 故障排除

### 问题：程序提示找不到 API 密钥
**解决方案**: 确保您已经创建了 `.env` 文件并填入了正确的 API 密钥。

### 问题：config.py 文件不存在
**解决方案**: `config.py` 文件应该已经存在于项目根目录。如果不存在，请检查是否被意外删除。

### 问题：API 调用失败
**解决方案**: 
1. 检查 `.env` 文件中的 API 地址和密钥是否正确
2. 确保网络连接正常
3. 检查 API 服务是否正在运行
