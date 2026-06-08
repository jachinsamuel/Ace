from unittest.mock import MagicMock, patch
from ace.core.git_ops import GitOps
import pytest

@patch("ace.core.git_ops.GitOps.execute")
@patch("ace.core.git_ops.GitOps.get_status")
@patch("ace.ai.llm_factory.get_llm")
def test_smart_undo_commit(mock_get_llm, mock_get_status, mock_execute, temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    # Mock GitOps state
    mock_execute.return_value = "h1 HEAD@{0}: commit: feat: add OAuth\nh2 HEAD@{1}: clone: ..."
    mock_get_status.return_value = {"staged": [], "unstaged": [], "untracked": []}
    
    # Mock LLM and response
    mock_response = MagicMock()
    mock_response.content = """
    {
        "commands": ["git reset --soft HEAD~1"],
        "explanation": "Undo last commit.",
        "risk_level": "moderate",
        "alternatives": null
    }
    """
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm
    
    # We test via CLI command run or direct parser. Since we want to test the prompt construction:
    from ace.ai.prompts.undo import UNDO_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from ace.utils.json_utils import extract_json
    
    usr_prompt = USER_PROMPT_TEMPLATE.format(
        git_state="Normal",
        staged_files="None",
        unstaged_files="None",
        reflog_entries="h1 HEAD@{0}: commit: feat: add OAuth"
    )
    
    # Verify json parser handles this output
    parsed = extract_json(mock_response.content)
    assert parsed["commands"] == ["git reset --soft HEAD~1"]
    assert parsed["risk_level"] == "moderate"
