import os
import time
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def extract_cot(text):
    """
    尝试从文本中提取思维链内容 (CoT)
    通常思维链被包裹在 <think> 标签中
    """
    cot_match = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
    if cot_match:
        cot_content = cot_match.group(1).strip()
        # 移除原文中的 <think> 部分作为最终回答
        clean_content = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        return cot_content, clean_content
    return None, text

def extract_score_from_text(text):
    """从自然语言文本中尝试提取评分，作为 JSON 格式失败时的后备方案"""
    # 尝试匹配 "score: 85" 或 "评分: 85" 等模式
    patterns = [
        r'["\']?score["\']?\s*[:：]\s*(\d+)',
        r'评分\s*[:：]\s*(\d+)',
        r'给出\s*(\d+)\s*分',
        r'(\d+)\s*分',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return {"score": score, "reasoning": text}
    return None

def get_llama_props(api_base):
    """尝试从 llama.cpp 获取模型属性"""
    try:
        # 假设 api_base 是 http://.../v1，我们需要去掉 /v1
        base_url = api_base.replace("/v1", "")
        resp = requests.get(f"{base_url}/props", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

def call_local_llm(source_code_json, prompt):
    """
    调用本地模型 (使用标准 OpenAI 格式)
    source_code_json: 可能是单文件字符串，也可能是多文件 JSON
    """
    api_base = os.getenv("LOCAL_MODEL_URL", "http://10.0.0.114:8080/v1")
    api_key = os.getenv("LOCAL_MODEL_KEY", "123456")
    model_id = os.getenv("LOCAL_MODEL_ID", "super")

    print(f"\n[DEBUG] Calling Local LLM at: {api_base}")
    print(f"[DEBUG] Model ID: {model_id}")
    
    # 设置较长的超时时间（例如 10 分钟），以应对大模型加载或长文本生成
    client = OpenAI(api_key=api_key, base_url=api_base, timeout=600.0)

    # 处理多文件上下文
    context = ""
    is_empty_context = False
    
    try:
        source_dict = json.loads(source_code_json)
        if isinstance(source_dict, dict) and source_dict:
            for filename, content in source_dict.items():
                context += f"--- FILE: {filename} ---\n{content}\n\n"
        elif isinstance(source_dict, dict) and not source_dict:
            is_empty_context = True
        else:
            context = str(source_dict)
    except:
        if not source_code_json or not source_code_json.strip():
            is_empty_context = True
        else:
            context = source_code_json

    if is_empty_context:
        full_prompt = f"Task:\n{prompt}\n\nNote: No existing code provided. Please implement this feature from scratch."
    else:
        full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"
    
    start_time = time.time()
    first_token_time = None
    full_content = ""
    actual_model_name = model_id  # 默认使用配置的模型名
    
    # 使用流式输出以精确计算生成速度 (TPS)
    response_stream = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": full_prompt}],
        stream=True,
        stream_options={"include_usage": True}
    )
    
    prompt_tokens = 0
    completion_tokens = 0

    for chunk in response_stream:
        # 尝试从第一个 chunk 获取实际的模型名称
        if hasattr(chunk, 'model') and chunk.model:
            actual_model_name = chunk.model
            
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta.content
            if delta:
                if first_token_time is None:
                    first_token_time = time.time()
                full_content += delta
        
        if hasattr(chunk, 'usage') and chunk.usage is not None:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens

    end_time = time.time()
    
    # 如果没有获取到 usage (部分后端不支持 stream_options)，则手动估算
    if completion_tokens == 0:
        completion_tokens = len(full_content) // 3 

    print(f"[DEBUG] Local LLM Response received. Status: Success")
    
    duration_ms = (end_time - start_time) * 1000
    # 生成耗时 = 结束时间 - 首字时间
    gen_duration_s = (end_time - first_token_time) if first_token_time else (duration_ms / 1000)
    
    raw_content = full_content
    cot, clean_content = extract_cot(raw_content)
    
    # 尝试获取 llama.cpp 的额外指标
    props = get_llama_props(api_base)
    max_context = props.get("n_ctx", 0)
    
    # 计算 TPS (Tokens Per Second)
    # 真正的生成速度应该排除掉 Prompt Processing (预读) 的时间
    tps = completion_tokens / gen_duration_s if gen_duration_s > 0 else 0
    
    # 计算预读速度 (Prompt TPS)
    # 预读时间 = 从开始到第一个token的时间
    if first_token_time and prompt_tokens > 0:
        prompt_processing_time = first_token_time - start_time
        prompt_tps = prompt_tokens / prompt_processing_time if prompt_processing_time > 0 else 0
    else:
        prompt_tps = 0
    
    return {
        "content": clean_content,
        "chain_of_thought": cot,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "duration_ms": duration_ms,
        "tps": tps,
        "prompt_tps": prompt_tps,
        "max_context": max_context,
        "model_name": actual_model_name
    }

def call_evaluator(original_prompt, reference_answer, local_response, evaluator_level="high"):
    """
    调用评委大模型进行评分，包含重试逻辑
    original_prompt: 原始的编程任务描述
    reference_answer: 参考答案
    local_response: 本地模型的回答
    evaluator_level: "super" | "high" | "low"
    """
    api_key = os.getenv("EVALUATOR_API_KEY", "123456")
    api_base = os.getenv("EVALUATOR_BASE_URL", "http://127.0.0.1:4000")
    model = os.getenv(f"EVALUATOR_MODEL_{evaluator_level.upper()}", evaluator_level)
    max_retries = 3
    retry_delay = 2  # 重试间隔秒数

    print(f"\n[DEBUG] Calling Evaluator ({evaluator_level}) at: {api_base}")
    print(f"[DEBUG] Evaluator Model: {model}")

    # 评委模型也设置 5 分钟超时
    client = OpenAI(api_key=api_key, base_url=api_base, timeout=300.0)
    
    system_prompt = f"""你是一位严谨的编程专家评委（级别：{evaluator_level}）。

【重要】你必须且只能返回一个 JSON 对象，格式如下：
{{"score": 数字(0-100), "reasoning": "评分理由"}}

禁止输出任何其他内容，禁止使用 Markdown 代码块，直接输出纯 JSON。

【评测任务说明】
本地模型收到了一个编程任务，需要根据任务要求生成代码解决方案。
你的任务是评估本地模型的回答是否正确解决了原始问题。

【评分标准】
- 主要评估本地模型的回答是否正确解决了原始任务
- 参考答案仅作为参考，本地模型的方案不必与参考答案完全一致
- 如果本地模型的方案逻辑正确、能解决问题，即使实现方式不同也应给高分"""

    user_content = f"""【原始编程任务】:
{original_prompt}

【参考答案】:
{reference_answer}

【本地模型回答】:
{local_response}"""
    
    last_error = ""
    last_raw_response = ""
    last_response = None  # 保存最后一次的 response 对象
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"[DEBUG] Evaluator retry attempt {attempt}/{max_retries}...")
                time.sleep(retry_delay)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_content}"}
                ],
                response_format={"type": "json_object"}
            )
            
            last_response = response  # 保存 response 对象
            raw_content = response.choices[0].message.content
            last_raw_response = raw_content
            
            if not raw_content:
                raise ValueError("API returned empty content (None or empty string)")
            
            # 尝试清洗可能存在的 Markdown 标签
            clean_json = raw_content
            if "```json" in raw_content:
                clean_json = re.search(r'```json\s*(.*?)\s*```', raw_content, re.DOTALL).group(1)
            elif "```" in raw_content:
                clean_json = re.search(r'```\s*(.*?)\s*```', raw_content, re.DOTALL).group(1)
            
            # 修复JSON中的控制字符问题：替换未转义的换行符和制表符
            # 先尝试直接解析，如果失败则进行修复
            try:
                result = json.loads(clean_json)
            except json.JSONDecodeError as json_err:
                # 如果是控制字符问题，尝试修复
                if "control character" in str(json_err).lower():
                    print(f"[DEBUG] Detected control character issue, attempting to fix...")
                    # 使用正则表达式修复：将reasoning字段中的换行符转义
                    # 方法1：直接替换所有控制字符
                    clean_json_fixed = clean_json.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    result = json.loads(clean_json_fixed)
                else:
                    raise
            
            # 确保返回的是字典，如果返回的是列表，取第一个元素
            if isinstance(result, list):
                if len(result) > 0:
                    result = result[0]
                else:
                    raise ValueError("API返回了空列表")
            
            # 验证返回的字典包含必要的字段
            if not isinstance(result, dict):
                # 如果不是字典，尝试用后备函数解析
                fallback_result = extract_score_from_text(raw_content)
                if fallback_result:
                    print("[DEBUG] Fallback to text extraction successful.")
                    return fallback_result
                raise ValueError(f"API返回了非字典类型: {type(result)}")
            
            if 'score' not in result or 'reasoning' not in result:
                # 如果是字典但字段缺失，尝试用后备函数解析
                fallback_result = extract_score_from_text(raw_content)
                if fallback_result:
                    print("[DEBUG] Fallback to text extraction successful.")
                    return fallback_result
                raise ValueError(f"API返回的字典缺少必要字段: {result}")
            
            # 确保 score 是整数类型
            try:
                result['score'] = int(result['score'])
            except (ValueError, TypeError):
                print(f"[DEBUG] Score type conversion failed: {result['score']}")
                fallback_result = extract_score_from_text(raw_content)
                if fallback_result:
                    print("[DEBUG] Fallback to text extraction successful.")
                    return fallback_result
                raise ValueError(f"无法将 score 转换为整数: {result['score']}")
            
            # 验证分数范围
            if not (0 <= result['score'] <= 100):
                print(f"[DEBUG] Score out of range: {result['score']}")
                result['score'] = max(0, min(100, result['score']))
            
            return result
        except Exception as e:
            last_error = str(e)
            print(f"[DEBUG] Evaluator attempt {attempt} failed: {last_error}")
            if last_response and hasattr(last_response, 'choices'):
                print(f"[DEBUG] Raw response content: {last_response.choices[0].message.content}")
            continue
            
    error_msg = f"评委调用在 {max_retries} 次重试后仍然失败: {last_error}"
    if last_raw_response:
        error_msg += f"\nAPI返回详情: {last_raw_response}"
        
    return {"score": 0, "reasoning": error_msg}

def call_all_evaluators(original_prompt, reference_answer, local_response):
    """
    并行调用所有三个评委模型进行评分
    返回: {"super": {...}, "high": {...}, "low": {...}}
    """
    results = {}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for level in ["super", "high", "low"]:
            print(f">>> 正在并行提交评委 [{level}]...")
            future = executor.submit(call_evaluator, original_prompt, reference_answer, local_response, level)
            futures[level] = future
        
        for level, future in futures.items():
            try:
                results[level] = future.result()
                print(f">>> 评委 [{level}] 完成评分")
            except Exception as e:
                print(f">>> 评委 [{level}] 失败: {str(e)}")
                results[level] = {"score": 0, "reasoning": f"评委调用失败: {str(e)}"}
    
    return results
