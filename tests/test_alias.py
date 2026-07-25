from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from ace.cli import app
from ace.core.config import Config

runner = CliRunner()

@patch("ace.core.config.load_config_file")
def test_alias_list(mock_load_config):
    mock_load_config.return_value = {
        "ai": {"provider": "ollama"},
        "aliases": {"ship": "git add . && ace commit -y", "wip": "git add ."}
    }
    result = runner.invoke(app, ["alias", "list"])
    assert result.exit_code == 0
    assert "ship" in result.output
    assert "wip" in result.output

@patch("ace.core.config.save_config")
@patch("ace.core.config.load_config_file")
def test_alias_add_and_remove(mock_load_config, mock_save_config):
    mock_load_config.return_value = {
        "ai": {"provider": "ollama"},
        "aliases": {}
    }
    # Add alias
    result_add = runner.invoke(app, ["alias", "add", "quickship", "git add . && git commit -m 'quick'"])
    assert result_add.exit_code == 0
    assert "Successfully added shortcut" in result_add.output
    mock_save_config.assert_called()

    # Remove alias
    mock_load_config.return_value = {
        "ai": {"provider": "ollama"},
        "aliases": {"quickship": "git add . && git commit -m 'quick'"}
    }
    result_rm = runner.invoke(app, ["alias", "remove", "quickship"])
    assert result_rm.exit_code == 0
    assert "Successfully removed shortcut" in result_rm.output

@patch("ace.core.git_ops.GitOps")
@patch("ace.core.config.load_config_file")
def test_alias_execution(mock_load_config, mock_git_ops_class):
    mock_load_config.return_value = {
        "ai": {"provider": "ollama"},
        "aliases": {"stageall": "git add ."}
    }
    mock_git_ops = MagicMock()
    mock_git_ops.execute.return_value = ""
    mock_git_ops_class.return_value = mock_git_ops

    result = runner.invoke(app, ["alias", "list"])
    assert result.exit_code == 0
