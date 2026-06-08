from unittest.mock import MagicMock, patch
import pytest
import os
from ace.ai.gitignore_generator import GitignoreGenerator
from ace.core.git_ops import GitOps

def test_gitignore_generator_success(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    mock_response = MagicMock()
    mock_response.content = '{"rules": "# Ignore log files\\n*.log", "explanation": "Ignores all log files."}'
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    generator = GitignoreGenerator(git_ops)

    with patch("ace.ai.gitignore_generator.get_llm", return_value=mock_llm):
        res = generator.generate_rules("ignore log files")
        
        assert "*.log" in res["rules"]
        assert "Ignores all log files" in res["explanation"]
        mock_llm.invoke.assert_called_once()

def test_gitignore_generator_missing_keys(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    mock_response = MagicMock()
    # Missing 'explanation'
    mock_response.content = '{"rules": "# Ignore log files\\n*.log"}'
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    generator = GitignoreGenerator(git_ops)

    with patch("ace.ai.gitignore_generator.get_llm", return_value=mock_llm):
        with pytest.raises(Exception, match="missing 'rules' or 'explanation' keys"):
            generator.generate_rules("ignore log files")
