from unittest.mock import MagicMock, patch
from ace.ai.intent_parser import IntentParser
from ace.core.git_ops import GitOps
import pytest

def test_intent_parser_success(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    mock_response = MagicMock()
    mock_response.content = """
    {
        "commands": ["git status"],
        "explanation": "Show current working tree status.",
        "risk_level": "safe",
        "alternatives": null
    }
    """
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    
    parser = IntentParser(git_ops)
    
    with patch("ace.ai.intent_parser.get_llm", return_value=mock_llm):
        result = parser.parse_intent("show status")
        
        assert result["commands"] == ["git status"]
        assert result["explanation"] == "Show current working tree status."
        assert result["risk_level"] == "safe"
        assert result["alternatives"] is None
        
        mock_llm.invoke.assert_called_once()

def test_intent_parser_with_markdown_wrapper(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    mock_response = MagicMock()
    mock_response.content = """
    Here is the plan:
    ```json
    {
        "commands": ["git reset --soft HEAD~1"],
        "explanation": "Undo last commit.",
        "risk_level": "moderate",
        "alternatives": null
    }
    ```
    """
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    parser = IntentParser(git_ops)
    
    with patch("ace.ai.intent_parser.get_llm", return_value=mock_llm):
        result = parser.parse_intent("undo last commit")
        assert result["commands"] == ["git reset --soft HEAD~1"]
        assert result["risk_level"] == "moderate"

def test_intent_parser_invalid_json(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    mock_response = MagicMock()
    mock_response.content = "Not a JSON output at all"
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    parser = IntentParser(git_ops)
    
    with patch("ace.ai.intent_parser.get_llm", return_value=mock_llm):
        from ace.ai.intent_parser import IntentParserError
        with pytest.raises(IntentParserError):
            parser.parse_intent("undo last commit")
