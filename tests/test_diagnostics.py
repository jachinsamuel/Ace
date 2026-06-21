import pytest
from unittest.mock import MagicMock, patch
from ace.core.diagnostics import GitDiagnostics

@pytest.fixture
def mock_git_ops():
    git_ops = MagicMock()
    git_ops.working_dir = "/tmp/fake_repo"
    git_ops.get_current_branch.return_value = "main"
    git_ops.get_upstream_tracking.return_value = "origin/main"
    git_ops.get_ahead_behind.return_value = {"ahead": 1, "behind": 0}
    git_ops.get_status.return_value = {"staged": [], "unstaged": [], "untracked": []}
    return git_ops

def test_check_locks_empty(mock_git_ops):
    with patch("ace.core.diagnostics.Path.exists", return_value=False):
        diagnostics = GitDiagnostics(mock_git_ops)
        assert diagnostics.check_locks() == []

def test_check_locks_detected(mock_git_ops):
    def exists_mock(path_obj):
        # Return True for index.lock
        return str(path_obj).endswith("index.lock") or str(path_obj).endswith(".git")

    with patch("pathlib.Path.exists", new=exists_mock):
        diagnostics = GitDiagnostics(mock_git_ops)
        locks = diagnostics.check_locks()
        assert len(locks) == 1
        assert locks[0].endswith("index.lock")

def test_check_large_files(mock_git_ops):
    mock_git_ops.get_status.return_value = {
        "untracked": ["large_file.zip", "small_file.txt"]
    }
    
    def exists_mock(self):
        return True
    
    def is_file_mock(self):
        return True
        
    class FakeStat:
        def __init__(self, size):
            self.st_size = size
            
    def stat_mock(self):
        if "large_file.zip" in str(self):
            return FakeStat(60 * 1024 * 1024)  # 60 MB
        return FakeStat(1 * 1024 * 1024)   # 1 MB

    with patch("pathlib.Path.exists", exists_mock), \
         patch("pathlib.Path.is_file", is_file_mock), \
         patch("pathlib.Path.stat", stat_mock):
         
        diagnostics = GitDiagnostics(mock_git_ops)
        large_files = diagnostics.check_large_files(threshold_mb=50.0)
        assert len(large_files) == 1
        assert large_files[0]["path"] == "large_file.zip"
        assert large_files[0]["size_mb"] == 60.0

def test_run_diagnostics(mock_git_ops):
    diagnostics = GitDiagnostics(mock_git_ops)
    with patch.object(diagnostics, "check_locks", return_value=[]), \
         patch.object(diagnostics, "check_large_files", return_value=[]), \
         patch("ace.core.context.RepoContext.check_merge_rebase_state", return_value={"in_progress": False, "type": None, "detail": ""}):
         
        report = diagnostics.run_diagnostics()
        assert report["has_issues"] is False
        assert report["detached_head"] is False
        assert report["sync_status"]["branch"] == "main"
        assert report["dirty_files"]["staged"] == 0
