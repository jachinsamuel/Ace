import pytest
from unittest.mock import MagicMock
from ace.core.git_ops import GitOps

def test_git_ops_execute_quoted_args():
    # Setup mock repo
    mock_repo = MagicMock()
    mock_git_func = MagicMock(return_value="commit success")
    mock_repo.git.commit = mock_git_func
    
    git_ops = GitOps.__new__(GitOps)
    git_ops.repo = mock_repo
    
    # Run execute with quotes
    res = git_ops.execute("commit -m 'hello world'")
    
    assert res == "commit success"
    mock_git_func.assert_called_once_with("-m", "hello world")

def test_git_ops_execute_unknown_command():
    mock_repo = MagicMock()
    # Simulate AttributeError when getting direct attribute
    del mock_repo.git.nonexistent
    
    # Mock fallback git.execute
    mock_execute = MagicMock(return_value="executed custom")
    mock_repo.git.execute = mock_execute
    
    git_ops = GitOps.__new__(GitOps)
    git_ops.repo = mock_repo
    
    res = git_ops.execute("nonexistent -a --foo")
    assert res == "executed custom"
    mock_execute.assert_called_once_with(["git", "nonexistent", "-a", "--foo"])

def test_git_ops_execute_empty():
    git_ops = GitOps.__new__(GitOps)
    with pytest.raises(ValueError, match="Empty Git command"):
        git_ops.execute("")
    with pytest.raises(ValueError, match="Empty Git command"):
        git_ops.execute("   ")
