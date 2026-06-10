import json
from unittest.mock import MagicMock, patch
from ace.ai.llm_factory import ensure_ollama_model, _checked_ollama_models, get_llm

def test_ensure_ollama_model_cached():
    # Setup cache key
    _checked_ollama_models.add(("http://localhost:11434", "test-model"))
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        ensure_ollama_model("http://localhost:11434", "test-model")
        mock_urlopen.assert_not_called()

@patch("urllib.request.urlopen")
def test_ensure_ollama_model_exists(mock_urlopen):
    # Reset cache
    _checked_ollama_models.clear()
    
    # Mock tags response
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "models": [{"name": "llama3:latest"}]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    ensure_ollama_model("http://localhost:11434", "llama3")
    assert ("http://localhost:11434", "llama3") in _checked_ollama_models

@patch("urllib.request.urlopen")
@patch("ace.ui.prompts.confirm", return_value=True)
def test_ensure_ollama_model_pull(mock_confirm, mock_urlopen):
    _checked_ollama_models.clear()
    
    # Mock tags response (not exists) and then pull response
    mock_tags_resp = MagicMock()
    mock_tags_resp.read.return_value = json.dumps({
        "models": [{"name": "other-model:latest"}]
    }).encode("utf-8")
    
    mock_pull_resp = MagicMock()
    mock_pull_resp.read.return_value = json.dumps({
        "status": "success"
    }).encode("utf-8")
    
    # urlopen will be called twice: first for tags, second for pull
    mock_urlopen.return_value.__enter__.side_effect = [mock_tags_resp, mock_pull_resp]
    
    ensure_ollama_model("http://localhost:11434", "llama3")
    
    # Check both calls
    assert mock_urlopen.call_count == 2
    assert mock_confirm.called

def test_get_llm_nvidia():
    import pytest
    from ace.core.config import Config
    mock_config = Config({
        "ai": {
            "provider": "nvidia",
            "nvidia_api_key": "nv-api-key-test",
            "nvidia_model": "meta/llama-3.3-70b-instruct",
        }
    })
    with patch("ace.ai.llm_factory.get_config", return_value=mock_config), \
         patch("langchain_nvidia_ai_endpoints.ChatNVIDIA") as mock_chat:
        get_llm()
        mock_chat.assert_called_once_with(
            model="meta/llama-3.3-70b-instruct",
            api_key="nv-api-key-test",
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            max_tokens=2048,
        )

def test_get_llm_openai():
    from ace.core.config import Config
    mock_config = Config({
        "ai": {
            "provider": "openai",
            "openai_api_key": "openai-key-test",
            "openai_model": "gpt-4o-mini",
        }
    })
    with patch("ace.ai.llm_factory.get_config", return_value=mock_config), \
         patch("langchain_openai.ChatOpenAI") as mock_chat:
        get_llm()
        mock_chat.assert_called_once_with(
            model="gpt-4o-mini",
            api_key="openai-key-test",
            temperature=0.0,
            max_tokens=2048,
        )

def test_get_llm_anthropic():
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

def test_get_llm_custom():
    from ace.core.config import Config
    mock_config = Config({
        "ai": {
            "provider": "custom",
            "custom_api_key": "custom-key-test",
            "custom_api_base": "https://custom-url.com/v1",
            "custom_model": "my-custom-model",
        }
    })
    with patch("ace.ai.llm_factory.get_config", return_value=mock_config), \
         patch("langchain_openai.ChatOpenAI") as mock_chat:
        get_llm()
        mock_chat.assert_called_once_with(
            model="my-custom-model",
            api_key="custom-key-test",
            base_url="https://custom-url.com/v1",
            temperature=0.0,
            max_tokens=2048,
        )

def test_get_llm_missing_keys():
    import pytest
    from ace.core.config import Config
    from ace.ai.llm_factory import LLMConfigurationError

    # Test openai missing key
    mock_config = Config({
        "ai": {
            "provider": "openai",
            "openai_api_key": "",
            "openai_model": "gpt-4o-mini",
        }
    })
    with patch("ace.ai.llm_factory.get_config", return_value=mock_config):
        with pytest.raises(LLMConfigurationError, match="OpenAI API Key not found"):
            get_llm()

    # Test anthropic missing key
    mock_config = Config({
        "ai": {
            "provider": "anthropic",
            "anthropic_api_key": "",
            "anthropic_model": "claude-3-5-sonnet-latest",
        }
    })
    with patch("ace.ai.llm_factory.get_config", return_value=mock_config):
        with pytest.raises(LLMConfigurationError, match="Anthropic API Key not found"):
            get_llm()

    # Test custom missing base url
    mock_config = Config({
        "ai": {
            "provider": "custom",
            "custom_api_key": "some-key",
            "custom_api_base": "",
            "custom_model": "custom-model",
        }
    })
    with patch("ace.ai.llm_factory.get_config", return_value=mock_config):
        with pytest.raises(LLMConfigurationError, match="Custom API Base URL not found"):
            get_llm()
