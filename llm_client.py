import os
import time
import json
import re
import requests
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

def call_local_llm(source_code_json, prompt, temperature=0.7):
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
        temperature=temperature,
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
    
    # 估算预读速度 (Prompt TPS)
    # 这是一个近似值，因为我们没有精确的预读结束时间。
    # 实际上 llama.cpp 在 OpenAI 接口的响应中可能包含非标准的 timings 字段，
    # 但 OpenAI Python SDK 会过滤掉它们。
    # 如果需要精确值，通常需要直接用 requests 调用 llama.cpp 原生接口。
    prompt_tps = 0 # 暂时设为 0，除非切换到原生接口
    
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

def call_evaluator(reference_answer, local_response):
    """
    调用评委大模型进行评分，包含重试逻辑
    """
    api_key = os.getenv("EVALUATOR_API_KEY", "123456")
    api_base = os.getenv("EVALUATOR_BASE_URL", "http://127.0.0.1:4000")
    model = os.getenv("EVALUATOR_MODEL", "super")
    max_retries = 3
    retry_delay = 2  # 重试间隔秒数

    print(f"\n[DEBUG] Calling Evaluator at: {api_base}")
    print(f"[DEBUG] Evaluator Model: {model}")

    # 评委模型也设置 5 分钟超时
    client = OpenAI(api_key=api_key, base_url=api_base, timeout=300.0)
    
    system_prompt = """你是一位严谨的编程专家评委。我会给你一个参考答案和一个本地模型的回答。
请对比两者，并给出 0-10 的评分（0分最差，10分完美）。
你的回复必须是严格的 JSON 格式，包含以下字段：
- score: 数字类型，0-10
- reasoning: 字符串类型，简要说明评分理由

注意：如果本地模型生成的代码逻辑正确且符合要求，即使与参考答案不完全一致，也应给予高分。"""

    # 将 system_prompt 合并到 user 消息中，以解决部分模型不支持 system role 的问题
    combined_user_content = f"{system_prompt}\n\n现在请开始评测：\n\n【参考答案】:\n{reference_answer}\n\n【本地模型回答】:\n{local_response}"
    
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
                    {"role": "user", "content": combined_user_content}
                ],
                response_format={"type": "json_object"}
            )
            
            last_response = response  # 保存 response 对象
            raw_content = response.choices[0].message.content
            last_raw_response = raw_content
            
            # 尝试清洗可能存在的 Markdown 标签
            clean_json = raw_content
            if "```json" in raw_content:
                clean_json = re.search(r'```json\s*(.*?)\s*```', raw_content, re.DOTALL).group(1)
            elif "```" in raw_content:
                clean_json = re.search(r'```\s*(.*?)\s*```', raw_content, re.DOTALL).group(1)
            
            result = json.loads(clean_json)
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
