import pytest
import json
from unittest.mock import patch, MagicMock
from ace.ai.llm_factory import ensure_ollama_model, _checked_ollama_models

@pytest.fixture(autouse=True)
def clear_ollama_cache():
    _checked_ollama_models.clear()

@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_ensure_ollama_model_streaming_success(mock_request, mock_urlopen):
    # First response: GET /api/tags (model list doesn't contain test-model)
    mock_response_tags = MagicMock()
    mock_response_tags.__enter__.return_value = mock_response_tags
    mock_response_tags.read.return_value = b'{"models": []}'
    
    # Second response: POST /api/pull (streaming download chunks)
    mock_response_pull = MagicMock()
    mock_response_pull.__enter__.return_value = mock_response_pull
    mock_response_pull.__iter__.return_value = [
        b'{"status": "pulling manifest"}\n',
        b'{"status": "downloading digest", "completed": 50, "total": 100}\n',
        b'{"status": "success"}\n'
    ]
    
    mock_urlopen.side_effect = [mock_response_tags, mock_response_pull]
    
    # Mock user input to confirm pulling
    with patch("ace.ui.prompts.confirm", return_value=True):
        ensure_ollama_model("http://localhost:11434", "test-model")
        
    assert mock_urlopen.call_count == 2

@patch("urllib.request.urlopen")
@patch("urllib.request.Request")
def test_ensure_ollama_model_already_exists(mock_request, mock_urlopen):
    # Model is listed in local models, so no pull should be requested
    mock_response_tags = MagicMock()
    mock_response_tags.__enter__.return_value = mock_response_tags
    mock_response_tags.read.return_value = b'{"models": [{"name": "test-model:latest"}]}'
    mock_urlopen.return_value = mock_response_tags
    
    with patch("ace.ui.prompts.confirm", return_value=True) as mock_confirm:
        ensure_ollama_model("http://localhost:11434", "test-model")
        mock_confirm.assert_not_called()
        
    assert mock_urlopen.call_count == 1
