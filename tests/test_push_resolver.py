from unittest.mock import MagicMock, patch
from ace.ai.push_resolver import categorize_push_error, handle_push_failure

def test_categorize_push_error_non_fast_forward():
    err = "error: failed to push some refs to 'github.com:repo/app.git'\nhint: Updates were rejected because the remote contains work that you do not have locally."
    cat = categorize_push_error(err)
    assert cat["type"] == "non_fast_forward"
    assert len(cat["actions"]) == 3

def test_categorize_push_error_no_upstream():
    err = "fatal: The current branch master has no upstream branch."
    cat = categorize_push_error(err)
    assert cat["type"] == "no_upstream"
    assert cat["actions"][0]["cmd"] == "set_upstream"

def test_categorize_push_error_permission_denied():
    err = "Permission denied (publickey). fatal: Could not read from remote repository."
    cat = categorize_push_error(err)
    assert cat["type"] == "permission_denied"

@patch("ace.ai.push_resolver.typer.prompt", return_value="1")
def test_handle_push_failure_pull_rebase(mock_prompt):
    mock_git_ops = MagicMock()
    mock_git_ops.get_current_branch.return_value = "master"
    mock_git_ops.push.return_value = "Everything up-to-date"
    
    err = "Updates were rejected because the remote contains work"
    res = handle_push_failure(mock_git_ops, err, remote="origin", branch="master")
    
    assert res is True
    mock_git_ops.execute.assert_called_once_with("pull --rebase origin master")
    mock_git_ops.push.assert_called_once_with(remote="origin", branch="master")
