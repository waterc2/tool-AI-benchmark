"""
测试脚本：验证模型类型检测功能
"""
import sys
sys.path.insert(0, '.')

from database import is_remote_model, get_model_summary_stats, get_all_models

print("=" * 80)
print("模型类型检测功能测试")
print("=" * 80)

# 测试 1: is_remote_model 函数
print("\n📋 测试 1: is_remote_model() 函数")
print("-" * 80)

test_cases = [
    # 本地模型（.gguf 结尾）
    ("Qwen3-30B-A3B-Instruct-2507-IQ4_XS-3.87bpw.gguf", False),
    ("GLM-4.7-Flash-PRISM-Q3_K_M.gguf", False),
    ("DeepSeek-Coder-V2-Lite-Instruct-Q5_K_M.gguf", False),
    
    # 远端模型（不以 .gguf 结尾）
    ("meta-llama/llama-3.3-70b-instruct:free", True),
    ("gpt-4", True),
    ("mimo-v2-flash", True),
    ("gemma-3-27b-it", True),
    ("z-ai/glm-4.5-air:free", True),
    
    # 边界情况
    ("", False),
    (None, False),
]

passed = 0
failed = 0

for model_name, expected in test_cases:
    result = is_remote_model(model_name)
    status = "✅" if result == expected else "❌"
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    model_display = f"'{model_name}'" if model_name else "None"
    expected_str = "远端" if expected else "本地"
    result_str = "远端" if result else "本地"
    print(f"{status} {model_display:<60} 期望: {expected_str:<4} 实际: {result_str:<4}")

print(f"\n测试结果: {passed} 通过, {failed} 失败")

# 测试 2: 获取所有模型并分类
print("\n📋 测试 2: 数据库中的模型分类")
print("-" * 80)

all_models = get_all_models()
local_models = [m for m in all_models if not is_remote_model(m)]
remote_models = [m for m in all_models if is_remote_model(m)]

print(f"\n总模型数: {len(all_models)}")
print(f"本地模型数: {len(local_models)}")
print(f"远端模型数: {len(remote_models)}")

print(f"\n本地模型示例（前5个）:")
for model in local_models[:5]:
    print(f"  - {model}")

print(f"\n远端模型示例（前5个）:")
for model in remote_models[:5]:
    print(f"  - {model}")

# 测试 3: 统计查询功能
print("\n📋 测试 3: 统计查询功能（按模型类型筛选）")
print("-" * 80)

for model_type in ["全部", "本地模型", "远端模型"]:
    try:
        df = get_model_summary_stats(model_type)
        print(f"\n{model_type}: {len(df)} 个模型")
        if len(df) > 0:
            print(f"  示例: {df.iloc[0]['model_name']}")
    except Exception as e:
        print(f"\n❌ {model_type}: 查询失败 - {str(e)}")

print("\n" + "=" * 80)
print("✅ 所有测试完成！")
print("=" * 80)
