import json
from unittest.mock import MagicMock, patch
import llm_client

def test_markdown_json_cleaning():
    print("Testing Markdown JSON cleaning...")
    mock_local_response = "Mock response with JSON in markdown"
    with patch('llm_client.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # 模拟返回带有 Markdown 标签的内容
        markdown_content = "```json\n{\"score\": 9, \"reasoning\": \"Excellent work!\"}\n```"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=markdown_content))]
        )
        
        result = llm_client.call_evaluator("ref", "ref_ans", mock_local_response)
        print(f"Result with Markdown: {result}")
        assert result['score'] == 9
        assert result['reasoning'] == "Excellent work!"
        print("Test passed: Markdown JSON cleaning works.")

def test_invalid_json_error_capture():
    print("\nTesting invalid JSON error capture...")
    mock_local_response = "Mock response that fails JSON parsing"
    with patch('llm_client.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # 模拟返回完全不是 JSON 的内容
        invalid_content = "Sorry, I cannot evaluate this because of some reason."
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=invalid_content))]
        )
        
        # 减小重试延迟
        with patch('time.sleep', return_value=None):
            result = llm_client.call_evaluator("ref", "ref_ans", mock_local_response)
            
        print(f"Result with invalid JSON: {result}")
        assert result['score'] == 0
        assert "API返回详情" in result['reasoning']
        assert invalid_content in result['reasoning']
        print("Test passed: Invalid JSON content is captured in reasoning.")

def test_fallback_text_extraction():
    print("\nTesting fallback text extraction...")
    mock_local_response = "Mock response requiring fallback extraction"
    with patch('llm_client.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # 模拟返回包含评分的自然语言文本
        text_content = "我来分析这个编程任务和参考答案。经过仔细评估，我给出 85 分。"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=text_content))]
        )

        # 减小重试延迟
        with patch('time.sleep', return_value=None):
            result = llm_client.call_evaluator("ref", "ref_ans", mock_local_response)

        print(f"Result with fallback extraction: {result}")
        assert result['score'] == 85
        assert text_content in result['reasoning']
        print("Test passed: Fallback text extraction works.")

if __name__ == "__main__":
    test_markdown_json_cleaning()
    test_invalid_json_error_capture()
