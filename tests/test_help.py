from unittest.mock import MagicMock, patch
import typer
from typer.testing import CliRunner
from ace.cli import app, review_cmd, commit_cmd

runner = CliRunner()

def test_help_command():
    # Invoke the help command via CliRunner
    result = runner.invoke(app, ["help"])
    
    # Assert successful exit code
    assert result.exit_code == 0
    
    # Assert expected visual cues and sections exist in output
    assert "Ace AI Git Copilot" in result.stdout
    assert "Natural Language Interface" in result.stdout
    assert "Core Ace Commands" in result.stdout
    assert "setup" in result.stdout
    assert "config" in result.stdout
    assert "dash" in result.stdout
    assert "Tips & Tricks" in result.stdout

@patch("ace.core.git_ops.GitOps")
def test_review_cmd_programmatic_invocation(mock_git_ops_class):
    mock_git_ops = MagicMock()
    mock_git_ops.repo.git.diff.return_value = ""
    mock_git_ops.get_staged_diff.return_value = ""
    mock_git_ops.get_status.return_value = {"staged": [], "unstaged": [], "untracked": []}
    mock_git_ops.get_remotes.return_value = []
    mock_git_ops_class.return_value = mock_git_ops

    try:
        review_cmd(all_changes=True, offline=True)
    except typer.Exit as e:
        assert e.exit_code == 0

@patch("ace.core.git_ops.GitOps")
def test_commit_cmd_programmatic_invocation(mock_git_ops_class):
    mock_git_ops = MagicMock()
    mock_git_ops.get_status.return_value = {"staged": []}
    mock_git_ops_class.return_value = mock_git_ops

    try:
        commit_cmd(offline=True)
    except typer.Exit as e:
        assert e.exit_code == 0
