import pytest
from unittest.mock import MagicMock, patch
from ace.ai.rebase_helper import RebaseHelper

@pytest.fixture
def mock_git_ops():
    git_ops = MagicMock()
    git_ops.working_dir = "/tmp/fake_repo"
    return git_ops

def test_get_local_commits(mock_git_ops):
    mock_git_ops.execute.return_value = (
        "a1b2c3d4e5f6g7h8|alice|feat: add dashboard login\n"
        "h8g7f6e5d4c3b2a1|alice|fix typo in config"
    )
    
    helper = RebaseHelper(mock_git_ops)
    commits = helper.get_local_commits("main")
    
    assert len(commits) == 2
    assert commits[0]["hexsha"] == "a1b2c3d4e5f6g7h8"
    assert commits[0]["author"] == "alice"
    assert commits[0]["summary"] == "feat: add dashboard login"
    assert commits[1]["summary"] == "fix typo in config"
    mock_git_ops.execute.assert_called_with("log main..HEAD --reverse --format=%H|%an|%s")

def test_run_auto_rebase(mock_git_ops):
    helper = RebaseHelper(mock_git_ops)
    
    mock_git_ops.repo.git.rebase.return_value = "Successfully rebased."
    
    recommendations = [
        {"hexsha": "a1b2c3d", "summary": "feat: add login", "action": "pick"},
        {"hexsha": "h8g7f6e", "summary": "fix typo", "action": "squash"}
    ]
    
    with patch("ace.ai.rebase_helper.tempfile.mkstemp", return_value=(999, "/tmp/fake_map")), \
         patch("ace.ai.rebase_helper.os.fdopen", MagicMock()), \
         patch("ace.ai.rebase_helper.os.unlink", MagicMock()):
         
        res = helper.run_auto_rebase("main", recommendations)
        
        assert res == "Successfully rebased."
        mock_git_ops.repo.git.rebase.assert_called_once()
        args, kwargs = mock_git_ops.repo.git.rebase.call_args
        assert "env" in kwargs
        assert "GIT_SEQUENCE_EDITOR" in kwargs["env"]
        assert "GIT_EDITOR" in kwargs["env"]
