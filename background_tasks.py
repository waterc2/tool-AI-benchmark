import threading
import time
from concurrent.futures import ThreadPoolExecutor
from database import update_eval_scores, get_connection, get_eval_record_by_id
from llm_client import call_llm, call_all_evaluators, call_evaluator


def get_safe_result(res, key, default):
    return res.get(key, default) if isinstance(res, dict) else default


class BackgroundTaskManager:
    def __init__(self):
        self.is_running = False
        self.progress = 0.0
        self.status = "空闲"
        self.logs = []
        self.current_case = ""
        self.total_cases = 0
        self.completed_cases = 0
        self.thread = None
        self.stop_requested = False
        self.eval_executor = ThreadPoolExecutor(max_workers=3)
        self.pending_evals = 0
        self.completed_evals = 0

    def add_log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {msg}")
        if len(self.logs) > 100:
            self.logs.pop(0)

    def async_evaluate_and_save(self, case, local_res, record_id):
        try:
            self.add_log(f"[异步评分] 开始评分用例: {case['title']}")
            eval_results = call_all_evaluators(case['prompt'], case['reference_answer'], local_res['content'])

            any_fail = any("评委调用在" in get_safe_result(res, 'reasoning', "") for res in eval_results.values())

            if any_fail:
                self.add_log(f"[异步评分] ⚠️ 用例 '{case['title']}' 部分评分失败")
            else:
                scores_str = ", ".join([f"{k}: {get_safe_result(v, 'score', 0)}" for k, v in eval_results.items()])
                self.add_log(f"[异步评分] 用例 '{case['title']}' 评分完成: {scores_str}")

            update_eval_scores(record_id, eval_results)
            self.add_log(f"[异步评分] ✅ 用例 '{case['title']}' 评分已更新到数据库")

        except Exception as e:
            self.add_log(f"[异步评分] ❌ 用例 '{case['title']}' 评分失败: {str(e)}")
        finally:
            self.completed_evals += 1

    def async_re_evaluate(self, record_id, case_title, prompt, reference_answer, local_response, target_levels=None):
        try:
            levels_str = ", ".join(target_levels) if target_levels else "全部"
            self.add_log(f"[重新评分] 开始评分记录ID: {record_id} ({case_title}), 目标模型: {levels_str}")
            
            # 如果没有指定目标级别，则评分全部
            if not target_levels:
                eval_results = call_all_evaluators(prompt, reference_answer, local_response)
            else:
                # 获取现有评分记录以合并
                existing_record = get_eval_record_by_id(record_id)
                eval_results = {}
                
                # 初始化现有值（使用新的字段名）
                # 映射: 1=gem, 2=opus, 3=gpt, 4=top2, 5=top
                level_mapping = {
                    'gem': 'eval_score_1',
                    'opus': 'eval_score_2',
                    'gpt': 'eval_score_3',
                    'top2': 'eval_score_4',
                    'top': 'eval_score_5'
                }
                
                for level, db_field in level_mapping.items():
                    eval_results[level] = {
                        "score": existing_record.get(db_field, 0),
                        "reasoning": existing_record.get(db_field.replace('eval_score_', 'eval_comment_'), "")
                    }
                
                # 仅针对指定级别并行调用评委
                from concurrent.futures import ThreadPoolExecutor as EvalExecutor
                with EvalExecutor(max_workers=len(target_levels)) as executor:
                    futures = {level: executor.submit(call_evaluator, prompt, reference_answer, local_response, level) 
                               for level in target_levels}
                    for level, future in futures.items():
                        try:
                            eval_results[level] = future.result()
                        except Exception as e:
                            eval_results[level] = {"score": 0, "reasoning": f"评委调用失败: {str(e)}"}

            any_fail = any("评委调用在" in get_safe_result(res, 'reasoning', "") for res in eval_results.values())

            if any_fail:
                self.add_log(f"[重新评分] ⚠️ 记录 {record_id} 部分评分失败")
            else:
                scores_str = ", ".join([f"{k}: {get_safe_result(v, 'score', 0)}" for k, v in eval_results.items()])
                self.add_log(f"[重新评分] 记录 {record_id} 评分完成: {scores_str}")

            update_eval_scores(record_id, eval_results)
            self.add_log(f"[重新评分] ✅ 记录 {record_id} 评分已更新到数据库")

        except Exception as e:
            self.add_log(f"[重新评分] ❌ 记录 {record_id} 评分失败: {str(e)}")
        finally:
            self.completed_evals += 1

    def submit_re_evaluate(self, record_id, case_title, prompt, reference_answer, local_response, target_levels=None):
        self.pending_evals += 1
        self.eval_executor.submit(self.async_re_evaluate, record_id, case_title, prompt, reference_answer, local_response, target_levels)
        levels_str = ", ".join(target_levels) if target_levels else "全部"
        self.add_log(f"🔄 已提交记录 {record_id} ({case_title}) 到异步重新评分队列 (目标: {levels_str})")

    def run_batch_test(self, selected_cases, api_base=None, api_key=None, model_id=None):
        print(f"\n[DEBUG] BackgroundTaskManager.run_batch_test started with {len(selected_cases)} cases")
        print(f"[DEBUG] Params: base={api_base}, model={model_id}")
        self.is_running = True
        self.stop_requested = False
        self.progress = 0.0
        self.completed_cases = 0
        self.total_cases = len(selected_cases)
        self.logs = []
        # 不重置评分计数器，允许累加（支持并发的重新评分任务）
        # self.pending_evals = 0
        # self.completed_evals = 0

        for idx, case in enumerate(selected_cases):
            if self.stop_requested:
                self.add_log("🛑 任务被用户停止")
                break

            self.current_case = case['title']
            self.status = f"正在处理 ({idx+1}/{self.total_cases}): {self.current_case}"
            self.add_log(f">>> 开始测试用例: {self.current_case}")

            local_res = None
            try:
                # 添加重试逻辑：如果失败则尝试等待 10 秒后重试一次
                max_retries = 1
                for attempt in range(max_retries + 1):
                    try:
                        if attempt > 0:
                            self.add_log(f"正在进行第 {attempt} 次重试...")
                        else:
                            self.add_log("正在请求 LLM...")
                        
                        local_res = call_llm(case['source_code'], case['prompt'], api_base, api_key, model_id)
                        break  # 成功则跳出循环
                    except Exception as e:
                        if attempt < max_retries:
                            self.add_log(f"⚠️ 请求失败: {str(e)}。等待 10 秒后再次尝试...")
                            time.sleep(10)
                        else:
                            raise e  # 最后一次尝试还是失败，抛出异常并由外层 catch

                self.add_log(f"本地模型响应成功 ({local_res['completion_tokens']} tokens)")

                record_data = {
                    "case_id": case['id'],
                    "model_name": local_res['model_name'],
                    "temperature": 0.0,
                    "local_response": local_res['content'],
                    "chain_of_thought": local_res['chain_of_thought'],
                    "prompt_tokens": local_res['prompt_tokens'],
                    "completion_tokens": local_res['completion_tokens'],
                    "total_time_ms": local_res['duration_ms'],
                    "tokens_per_second": local_res['tps'],
                    "prompt_tps": local_res.get('prompt_tps', 0),
                    "max_context": local_res.get('max_context', 0),
                    "eval_score": 0,
                    "eval_comment": "待评分",
                    "eval_score_1": 0,
                    "eval_comment_1": "待评分",
                    "eval_score_2": 0,
                    "eval_comment_2": "待评分",
                    "eval_score_3": 0,
                    "eval_comment_3": "待评分",
                    "eval_score_4": 0,
                    "eval_comment_4": "待评分",
                    "eval_score_5": 0,
                    "eval_comment_5": "待评分"
                }

                from database import save_eval_record
                record_id = save_eval_record(record_data)

                self.add_log(f"✅ 用例 '{self.current_case}' 本地测试完成，已保存 (记录ID: {record_id})")

                self.pending_evals += 1
                self.eval_executor.submit(self.async_evaluate_and_save, case, local_res, record_id)
                self.add_log(f"🚀 已提交用例 '{self.current_case}' 到异步评分队列")

            except Exception as e:
                self.add_log(f"❌ 执行失败: {str(e)}")

            self.completed_cases += 1
            self.progress = self.completed_cases / self.total_cases

        self.is_running = False
        self.status = f"测试完成，等待评分 ({self.completed_evals}/{self.pending_evals})"
        self.progress = 1.0

        self.status = "全部完成"
        self.add_log(f"🎉 所有任务完成！共测试 {self.total_cases} 个用例，评分 {self.completed_evals} 个")

    def start_task(self, selected_cases, api_base=None, api_key=None, model_id=None):
        if not self.is_running:
            self.thread = threading.Thread(target=self.run_batch_test, args=(selected_cases, api_base, api_key, model_id,))
            self.thread.daemon = True
            self.thread.start()

    def stop_task(self):
        self.stop_requested = True
