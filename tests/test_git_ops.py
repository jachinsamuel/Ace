from ace.core.git_ops import GitOps, NotAGitRepositoryError
import pytest

def test_git_ops_outside_repo(tmp_path):
    """Test that GitOps raises NotAGitRepositoryError when outside a git repo."""
    with pytest.raises(NotAGitRepositoryError):
        GitOps(repo_path=str(tmp_path))

def test_git_ops_basic_operations(temp_git_repo):
    """Test basic Git operations using a temporary repository."""
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    # Check current branch
    assert git_ops.get_current_branch() in ("master", "main")
    
    # Check status of empty repo
    status = git_ops.get_status()
    assert not status["staged"]
    assert not status["unstaged"]
    assert not status["untracked"]
    
    # Create an untracked file
    test_file = repo_path / "test.txt"
    test_file.write_text("Hello World", encoding="utf-8")
    
    status = git_ops.get_status()
    assert "test.txt" in status["untracked"]
    
    # Stage the file
    repo.index.add(["test.txt"])
    
    status = git_ops.get_status()
    assert "test.txt" in status["staged"]
    assert "test.txt" not in status["untracked"]
    
    # Verify staged diff
    diff = git_ops.get_staged_diff()
    assert "Hello World" in diff
    
    # Commit
    commit_res = git_ops.commit("initial commit")
    assert commit_res is not None
    
    status = git_ops.get_status()
    assert not status["staged"]
    
    # Check log
    log = git_ops.get_log(n=1)
    assert len(log) == 1
    assert log[0]["summary"] == "initial commit"
    assert log[0]["author"] == "Test User"

def test_git_ops_get_remotes(temp_git_repo):
    """Test remote list querying."""
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    assert git_ops.get_remotes() == []

    # Add a remote and check again
    repo.create_remote("origin", "https://github.com/example/repo.git")
    assert git_ops.get_remotes() == ["origin"]

