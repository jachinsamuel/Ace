import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from ace.core.context import RepoContext
from ace.core.git_ops import GitOps

@pytest.fixture
def mock_git_ops():
    git_ops = MagicMock(spec=GitOps)
    git_ops.working_dir = "/mock/repo"
    mock_repo = MagicMock()
    mock_repo.git_dir = "/mock/repo/.git"
    git_ops.repo = mock_repo
    return git_ops

@patch("pathlib.Path.exists", autospec=True)
def test_no_active_operation(mock_exists, mock_git_ops):
    mock_exists.return_value = False
    context = RepoContext(mock_git_ops)
    state = context.check_merge_rebase_state()
    
    assert state["in_progress"] is False
    assert state["type"] is None
    assert state["detail"] == ""

@patch("pathlib.Path.exists", autospec=True)
def test_merge_active_unresolved(mock_exists, mock_git_ops):
    mock_exists.return_value = True
    mock_git_ops.repo.index.unmerged_files.return_value = {"file1.txt": [None]}
    
    context = RepoContext(mock_git_ops)
    state = context.check_merge_rebase_state()
    
    assert state["in_progress"] is True
    assert state["type"] == "merge"
    assert "Need resolution" in state["detail"]

@patch("pathlib.Path.exists", autospec=True)
def test_merge_active_resolved(mock_exists, mock_git_ops):
    mock_exists.return_value = True
    mock_git_ops.repo.index.unmerged_files.return_value = {}
    
    context = RepoContext(mock_git_ops)
    state = context.check_merge_rebase_state()
    
    assert state["in_progress"] is True
    assert state["type"] == "merge"
    assert "resolved" in state["detail"]
    assert "finalize merge" in state["detail"]

@patch("pathlib.Path.exists", autospec=True)
def test_rebase_active_unresolved(mock_exists, mock_git_ops):
    def exists_check(path_obj):
        if path_obj.name == "MERGE_HEAD":
            return False
        return True
        
    mock_exists.side_effect = exists_check
    mock_git_ops.repo.index.unmerged_files.return_value = {"file2.txt": [None]}
    
    context = RepoContext(mock_git_ops)
    state = context.check_merge_rebase_state()
    
    assert state["in_progress"] is True
    assert state["type"] == "rebase"
    assert "Need resolution" in state["detail"]

@patch("pathlib.Path.exists", autospec=True)
def test_rebase_active_resolved(mock_exists, mock_git_ops):
    def exists_check(path_obj):
        if path_obj.name == "MERGE_HEAD":
            return False
        return True
        
    mock_exists.side_effect = exists_check
    mock_git_ops.repo.index.unmerged_files.return_value = {}
    
    context = RepoContext(mock_git_ops)
    state = context.check_merge_rebase_state()
    
    assert state["in_progress"] is True
    assert state["type"] == "rebase"
    assert "resolved" in state["detail"]
    assert "continue rebase" in state["detail"]
