import pytest
from unittest.mock import MagicMock, patch
from ace.core.hooks import GitHooksManager

@pytest.fixture
def mock_git_ops():
    git_ops = MagicMock()
    git_ops.working_dir = "/tmp/fake_repo"
    return git_ops

def test_install_pre_commit(mock_git_ops):
    manager = GitHooksManager(mock_git_ops)
    
    mock_path = MagicMock()
    
    with patch("ace.core.hooks.Path.mkdir"), \
         patch("ace.core.hooks.Path.__truediv__", return_value=mock_path), \
         patch("ace.core.hooks.os.stat"), \
         patch("ace.core.hooks.os.chmod") as mock_chmod:
         
        manager.install_pre_commit()
        
        mock_path.write_text.assert_called_once()
        args, kwargs = mock_path.write_text.call_args
        assert "Ace pre-commit" in args[0]
        mock_chmod.assert_called_once()

def test_install_prepare_commit_msg(mock_git_ops):
    manager = GitHooksManager(mock_git_ops)
    
    mock_path = MagicMock()
    
    with patch("ace.core.hooks.Path.mkdir"), \
         patch("ace.core.hooks.Path.__truediv__", return_value=mock_path), \
         patch("ace.core.hooks.os.stat"), \
         patch("ace.core.hooks.os.chmod") as mock_chmod:
         
        manager.install_prepare_commit_msg()
        
        mock_path.write_text.assert_called_once()
        args, kwargs = mock_path.write_text.call_args
        assert "Ace is drafting commit message" in args[0]
        mock_chmod.assert_called_once()

def test_uninstall_all(mock_git_ops):
    manager = GitHooksManager(mock_git_ops)
    
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "This hook contains Ace scripts"
    
    with patch("ace.core.hooks.Path.__truediv__", return_value=mock_path):
        manager.uninstall_all()
        assert mock_path.unlink.call_count == 2

def test_uninstall_skip_non_ace_hooks(mock_git_ops):
    manager = GitHooksManager(mock_git_ops)
    
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "This is a custom user script"
    
    with patch("ace.core.hooks.Path.__truediv__", return_value=mock_path):
        manager.uninstall_all()
        mock_path.unlink.assert_not_called()
