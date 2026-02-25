"""
验证配置脚本 - 检查所有配置是否正确设置
Configuration Verification Script - Check if all configurations are properly set
"""
import os
import sys
import io

# 修复 Windows PowerShell 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} 不存在: {filepath}")
        return False

def check_env_var(var_name, description, allow_empty=False):
    """检查环境变量是否设置"""
    value = os.getenv(var_name)
    if value:
        if value in ["your_api_key_here", "your_evaluator_api_key_here", "your_openrouter_api_key_here"]:
            print(f"⚠️  {description} ({var_name}): 请替换为实际的 API 密钥")
            return False
        else:
            # 隐藏密钥的大部分内容
            if "KEY" in var_name or "key" in var_name.lower():
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {description} ({var_name}): {display_value}")
            return True
    elif allow_empty:
        print(f"ℹ️  {description} ({var_name}): 未设置（可选）")
        return True
    else:
        print(f"❌ {description} ({var_name}): 未设置")
        return False

def main():
    print("=" * 80)
    print("配置验证脚本 - Configuration Verification")
    print("=" * 80)
    print()
    
    all_ok = True
    
    # 1. 检查必需文件
    print("📁 检查必需文件...")
    all_ok &= check_file_exists(".env", ".env 文件")
    all_ok &= check_file_exists(".env.example", ".env.example 模板文件")
    all_ok &= check_file_exists("config.py", "config.py 配置模块")
    all_ok &= check_file_exists("CONFIG.md", "CONFIG.md 配置文档")
    print()
    
    # 2. 导入配置模块
    print("🔧 加载配置模块...")
    try:
        import config
        print("✅ config.py 模块加载成功")
    except Exception as e:
        print(f"❌ config.py 模块加载失败: {e}")
        all_ok = False
        sys.exit(1)
    print()
    
    # 3. 检查本地模型配置
    print("🤖 检查本地模型配置...")
    if config.LOCAL_MODEL_URL:
        print(f"✅ LOCAL_MODEL_URL: {config.LOCAL_MODEL_URL}")
    else:
        print("❌ LOCAL_MODEL_URL: 未设置")
        all_ok = False
    
    if config.LOCAL_MODEL_KEY:
        display_key = config.LOCAL_MODEL_KEY[:8] + "..." if len(config.LOCAL_MODEL_KEY) > 8 else "***"
        print(f"✅ LOCAL_MODEL_KEY: {display_key}")
    else:
        print("⚠️  LOCAL_MODEL_KEY: 未设置（某些 API 可能需要）")
    
    if config.LOCAL_MODEL_ID:
        print(f"✅ LOCAL_MODEL_ID: {config.LOCAL_MODEL_ID}")
    else:
        print("❌ LOCAL_MODEL_ID: 未设置")
        all_ok = False
    print()
    
    # 4. 检查评委模型配置
    print("👨‍⚖️ 检查评委模型配置...")
    if config.EVALUATOR_BASE_URL:
        print(f"✅ EVALUATOR_BASE_URL: {config.EVALUATOR_BASE_URL}")
    else:
        print("❌ EVALUATOR_BASE_URL: 未设置")
        all_ok = False
    
    if config.EVALUATOR_API_KEY:
        if config.EVALUATOR_API_KEY in ["your_evaluator_api_key_here", "123456"]:
            print(f"⚠️  EVALUATOR_API_KEY: 请替换为实际的 API 密钥")
            all_ok = False
        else:
            display_key = config.EVALUATOR_API_KEY[:8] + "..." if len(config.EVALUATOR_API_KEY) > 8 else "***"
            print(f"✅ EVALUATOR_API_KEY: {display_key}")
    else:
        print("❌ EVALUATOR_API_KEY: 未设置")
        all_ok = False
    
    print(f"✅ EVALUATOR_MODEL_GEM: {config.EVALUATOR_MODEL_GEM}")
    print(f"✅ EVALUATOR_MODEL_OPUS: {config.EVALUATOR_MODEL_OPUS}")
    print(f"✅ EVALUATOR_MODEL_GPT: {config.EVALUATOR_MODEL_GPT}")
    print(f"✅ EVALUATOR_MODEL_TOP: {config.EVALUATOR_MODEL_TOP}")
    print()
    
    # 5. 检查 NVIDIA 配置
    print("🌤️ 检查 NVIDIA 配置...")
    if config.NVIDIA_API_URL:
        print(f"✅ NVIDIA_API_URL: {config.NVIDIA_API_URL}")
    else:
        print("❌ NVIDIA_API_URL: 未设置")
        all_ok = False
        
    if config.NVIDIA_API_KEY:
        display_key = config.NVIDIA_API_KEY[:8] + "..." if len(config.NVIDIA_API_KEY) > 8 else "***"
        print(f"✅ NVIDIA_API_KEY: {display_key}")
    else:
        print("❌ NVIDIA_API_KEY: 未设置")
        all_ok = False
        
    print(f"✅ NVIDIA_MODEL_ID: {config.NVIDIA_MODEL_ID}")
    print()
    
    # 6. 检查 LiteLLM 配置
    print("🚀 检查 LiteLLM 配置...")
    if config.LITELLM_API_URL:
        print(f"✅ LITELLM_API_URL: {config.LITELLM_API_URL}")
    else:
        print("❌ LITELLM_API_URL: 未设置")
        all_ok = False
        
    if config.LITELLM_API_KEY:
        display_key = config.LITELLM_API_KEY[:8] + "..." if len(config.LITELLM_API_KEY) > 8 else "***"
        print(f"✅ LITELLM_API_KEY: {display_key}")
    else:
        print("❌ LITELLM_API_KEY: 未设置")
        all_ok = False
    print()
    
    # 7. 检查 .gitignore 安全设置...
    print("🔒 检查 .gitignore 安全设置...")
    gitignore_ok = True
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r", encoding="utf-8") as f:
            gitignore_content = f.read()
        
        if ".env" in gitignore_content:
            print("✅ .env 已被 .gitignore 排除")
        else:
            print("⚠️  .env 未被 .gitignore 排除（可能会泄露密钥）")
            gitignore_ok = False
        
        if "config.py" in gitignore_content:
            print("✅ config.py 已被 .gitignore 排除")
        else:
            print("⚠️  config.py 未被 .gitignore 排除")
            gitignore_ok = False
        
        if "*_backup_*.db" in gitignore_content or "eval_results_backup" in gitignore_content:
            print("✅ 数据库备份文件已被 .gitignore 排除")
        else:
            print("ℹ️  数据库备份文件未被 .gitignore 排除（建议添加）")
    else:
        print("❌ .gitignore 文件不存在")
        gitignore_ok = False
    
    all_ok &= gitignore_ok
    print()
    
    # 6. 总结
    print("=" * 80)
    if all_ok:
        print("🎉 所有配置检查通过！您可以开始使用应用了。")
        print()
        print("启动应用:")
        print("  streamlit run app.py")
    else:
        print("⚠️  发现一些配置问题，请根据上述提示进行修复。")
        print()
        print("常见问题解决:")
        print("  1. 确保 .env 文件存在并包含正确的 API 密钥")
        print("  2. 检查 CONFIG.md 了解详细配置说明")
        print("  3. 确保所有必需的环境变量都已设置")
    print("=" * 80)
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
