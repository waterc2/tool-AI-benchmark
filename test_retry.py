import os
import json
from unittest.mock import MagicMock, patch
import llm_client

def test_call_evaluator_retry():
    print("Starting test_call_evaluator_retry...")
    # 模拟 OpenAI 客户端
    with patch('llm_client.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # 模拟前两次调用失败，第三次成功 (attempt 0, 1 失败, attempt 2 成功)
        mock_client.chat.completions.create.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"score": 8, "reasoning": "Good"}'))])
        ]
        
        # 减小重试延迟以便快速测试
        with patch('time.sleep', return_value=None):
            result = llm_client.call_evaluator("ref", "resp")
            
        print(f"Final Result: {result}")
        assert result['score'] == 8
        assert mock_client.chat.completions.create.call_count == 3
        print("Test passed: Successfully retried and succeeded on 3rd attempt.")

def test_call_evaluator_all_fail():
    print("\nStarting test_call_evaluator_all_fail...")
    with patch('llm_client.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # 模拟所有尝试都失败 (0, 1, 2, 3)
        mock_client.chat.completions.create.side_effect = Exception("Permanent failure")
        
        with patch('time.sleep', return_value=None):
            result = llm_client.call_evaluator("ref", "resp")
            
        print(f"Final Result: {result}")
        assert result['score'] == 0
        assert "仍然失败" in result['reasoning']
        assert mock_client.chat.completions.create.call_count == 4 # 0, 1, 2, 3
        print("Test passed: Correctly handled permanent failure after 3 retries.")

if __name__ == "__main__":
    try:
        test_call_evaluator_retry()
        test_call_evaluator_all_fail()
    except Exception as e:
        print(f"Test failed with error: {e}")
        exit(1)
