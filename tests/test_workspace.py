import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from ace.cli import workspace_cmd

@patch("ace.core.git_ops.GitOps")
@patch("pathlib.Path.iterdir")
@patch("pathlib.Path.is_dir")
@patch("pathlib.Path.exists")
@patch("ace.ui.prompts.prompt_select")
@patch("ace.ui.prompts.prompt_action")
@patch("subprocess.run")
def test_workspace_cmd_select_dashboard(
    mock_sub_run,
    mock_action,
    mock_select,
    mock_exists,
    mock_is_dir,
    mock_iterdir,
    mock_gitops
):
    # Setup directories
    repo_path = MagicMock(spec=Path)
    repo_path.name = "my-test-project"
    repo_path.__str__.return_value = "/mock/workspace/my-test-project"
    
    # Mock checks
    mock_is_dir.return_value = True
    # mock exists to simulate that (child / ".git") exists
    mock_exists.side_effect = lambda: True
    mock_iterdir.return_value = [repo_path]
    
    # Mock GitOps response
    mock_git = MagicMock()
    mock_git.get_current_branch.return_value = "main"
    mock_git.get_status.return_value = {"staged": ["file1.txt"], "unstaged": [], "untracked": []}
    mock_git.get_ahead_behind.return_value = {"ahead": 2, "behind": 0}
    mock_git.get_upstream_tracking.return_value = "origin/main"
    mock_gitops.return_value = mock_git
    
    # Selection: idx 0 (my-test-project)
    mock_select.return_value = 0
    # Action: 'd' (Dashboard)
    mock_action.return_value = "d"
    
    # Run
    workspace_cmd("/mock/workspace")
    
    # Assert dashboard was spawned in the subdirectory via subprocess
    mock_sub_run.assert_called_once()
    args, kwargs = mock_sub_run.call_args
    assert "dash" in args[0]
    assert kwargs["cwd"] == "/mock/workspace/my-test-project"

@patch("ace.core.git_ops.GitOps")
@patch("pathlib.Path.iterdir")
@patch("pathlib.Path.is_dir")
@patch("pathlib.Path.exists")
@patch("ace.ui.prompts.prompt_select")
def test_workspace_cmd_quit_early(
    mock_select,
    mock_exists,
    mock_is_dir,
    mock_iterdir,
    mock_gitops
):
    repo_path = MagicMock(spec=Path)
    repo_path.name = "my-test-project"
    repo_path.__str__.return_value = "/mock/workspace/my-test-project"
    
    mock_is_dir.return_value = True
    mock_exists.side_effect = lambda: True
    mock_iterdir.return_value = [repo_path]
    
    mock_git = MagicMock()
    mock_git.get_current_branch.return_value = "main"
    mock_git.get_status.return_value = {"staged": [], "unstaged": [], "untracked": []}
    mock_git.get_ahead_behind.return_value = {"ahead": 0, "behind": 0}
    mock_git.get_upstream_tracking.return_value = "origin/main"
    mock_gitops.return_value = mock_git
    
    # Selection: -1 (Quit/Skip)
    mock_select.return_value = -1
    
    # Run
    workspace_cmd("/mock/workspace")
    
    # Verify no action prompt or subprocess was triggered
    mock_select.assert_called_once()
