from unittest.mock import MagicMock, patch
from ace.ai.llm_factory import FallbackChatModel

def test_fallback_chat_model_primary_success():
    primary = MagicMock()
    primary.invoke.return_value = "Primary response"
    fallback = MagicMock()
    
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("test prompt")
    
    assert res == "Primary response"
    primary.invoke.assert_called_once_with("test prompt", config=None)
    fallback.invoke.assert_not_called()

def test_fallback_chat_model_primary_failure_fallback_success():
    primary = MagicMock()
    primary.invoke.side_effect = Exception("Connection refused / 503")
    
    fallback = MagicMock()
    fallback.invoke.return_value = "Fallback response"
    
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("test prompt")
    
    assert res == "Fallback response"
    primary.invoke.assert_called_once()
    fallback.invoke.assert_called_once_with("test prompt", config=None)

def test_fallback_chat_model_both_failures_heuristic_success():
    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")
    
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("conventional_commit staged changes diff")
    
    assert "feat:" in res.content

