"""
简单测试脚本：验证 is_remote_model 函数
"""

def is_remote_model(model_name):
    """判断是否为远端模型（基于模型名称）"""
    if not model_name:
        return False
    return not model_name.endswith('.gguf')

print("=" * 80)
print("模型类型检测功能测试")
print("=" * 80)

print("\n📋 测试 is_remote_model() 函数")
print("-" * 80)

test_cases = [
    # 本地模型（.gguf 结尾）
    ("Qwen3-30B-A3B-Instruct-2507-IQ4_XS-3.87bpw.gguf", False, "本地"),
    ("GLM-4.7-Flash-PRISM-Q3_K_M.gguf", False, "本地"),
    ("DeepSeek-Coder-V2-Lite-Instruct-Q5_K_M.gguf", False, "本地"),
    ("phi-4-Q6_K.gguf", False, "本地"),
    
    # 远端模型（不以 .gguf 结尾）
    ("meta-llama/llama-3.3-70b-instruct:free", True, "远端"),
    ("gpt-4", True, "远端"),
    ("mimo-v2-flash", True, "远端"),
    ("gemma-3-27b-it", True, "远端"),
    ("z-ai/glm-4.5-air:free", True, "远端"),
    ("openai/gpt-oss-120b:free", True, "远端"),
    ("minimaxai/minimax-m2.1", True, "远端"),
    
    # 边界情况
    ("", False, "本地(空字符串)"),
]

passed = 0
failed = 0

for model_name, expected, description in test_cases:
    result = is_remote_model(model_name)
    status = "✅" if result == expected else "❌"
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    model_display = f"'{model_name}'" if model_name else "''"
    expected_str = "远端" if expected else "本地"
    result_str = "远端" if result else "本地"
    print(f"{status} {model_display:<55} | 期望: {expected_str:<4} | 实际: {result_str:<4} | {description}")

print("\n" + "=" * 80)
print(f"测试结果: ✅ {passed} 通过, ❌ {failed} 失败")
print("=" * 80)

if failed == 0:
    print("\n🎉 所有测试通过！is_remote_model() 函数工作正常。")
else:
    print(f"\n⚠️  有 {failed} 个测试失败，请检查实现。")
