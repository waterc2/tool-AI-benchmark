import json
from unittest.mock import MagicMock, patch
import llm_client

def test_markdown_json_cleaning():
    print("Testing Markdown JSON cleaning...")
    with patch('llm_client.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # 模拟返回带有 Markdown 标签的内容
        markdown_content = "```json\n{\"score\": 9, \"reasoning\": \"Excellent work!\"}\n```"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=markdown_content))]
        )
        
        result = llm_client.call_evaluator("ref", "resp")
        print(f"Result with Markdown: {result}")
        assert result['score'] == 9
        assert result['reasoning'] == "Excellent work!"
        print("Test passed: Markdown JSON cleaning works.")

def test_invalid_json_error_capture():
    print("\nTesting invalid JSON error capture...")
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
            result = llm_client.call_evaluator("ref", "resp")
            
        print(f"Result with invalid JSON: {result}")
        assert result['score'] == 0
        assert "API返回详情" in result['reasoning']
        assert invalid_content in result['reasoning']
        print("Test passed: Invalid JSON content is captured in reasoning.")

if __name__ == "__main__":
    test_markdown_json_cleaning()
    test_invalid_json_error_capture()
