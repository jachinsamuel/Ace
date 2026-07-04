import pytest
from pathlib import Path
from unittest.mock import MagicMock
from ace.core.context import RepoContext

def test_check_merge_rebase_state_with_git_dir_resolution(tmp_path):
    # Create mock git_dir (which in real git might be inside worktrees/submodules)
    mock_git_dir = tmp_path / "worktree_gitdir"
    mock_git_dir.mkdir()
    
    # Simulate a merge in progress
    merge_head = mock_git_dir / "MERGE_HEAD"
    merge_head.write_text("commit123", encoding="utf-8")
    
    # Setup mock git_ops and repo
    mock_git_ops = MagicMock()
    mock_git_ops.repo.git_dir = str(mock_git_dir)
    mock_git_ops.working_dir = str(tmp_path)
    
    context_builder = RepoContext(mock_git_ops)
    state = context_builder.check_merge_rebase_state()
    
    assert state["in_progress"] is True
    assert state["type"] == "merge"
    assert "Merge conflict" in state["detail"]

def test_check_merge_rebase_state_fallback(tmp_path):
    # Setup mock git_ops that raises error when accessing git_dir
    mock_git_ops = MagicMock()
    # Delete git_dir attribute to force AttributeError on access
    del mock_git_ops.repo.git_dir
    mock_git_ops.working_dir = str(tmp_path)
    
    # Setup local fallback .git directory
    fallback_git = tmp_path / ".git"
    fallback_git.mkdir()
    
    rebase_apply = fallback_git / "rebase-apply"
    rebase_apply.mkdir()
    
    context_builder = RepoContext(mock_git_ops)
    state = context_builder.check_merge_rebase_state()
    
    assert state["in_progress"] is True
    assert state["type"] == "rebase"
