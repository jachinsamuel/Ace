import sys
from unittest.mock import MagicMock, patch

# Mock langchain modules in sys.modules
sys.modules["langchain_nvidia_ai_endpoints"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["langchain_anthropic"] = MagicMock()
sys.modules["langchain_ollama"] = MagicMock()

# Now import get_llm
from ace.ai.llm_factory import get_llm
from ace.core.config import Config

mock_config = Config({
    "ai": {
        "provider": "anthropic",
        "anthropic_api_key": "anthropic-key-test",
        "anthropic_model": "claude-3-5-sonnet-latest",
    }
})

with patch("ace.ai.llm_factory.get_config", return_value=mock_config), \
     patch("langchain_anthropic.ChatAnthropic") as mock_chat:
    get_llm()
    mock_chat.assert_called_once_with(
        model="claude-3-5-sonnet-latest",
        api_key="anthropic-key-test",
        temperature=0.0,
        max_tokens=2048,
    )
    print("Success: Mocked sys.modules works perfectly!")
