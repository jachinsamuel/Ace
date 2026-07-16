from unittest.mock import MagicMock, patch
import sys
from typer.testing import CliRunner
from ace.cli import app

runner = CliRunner()

@patch("ace.core.git_ops.GitOps")
@patch("ace.ai.llm_factory.get_llm")
@patch("ace.ai.intent_parser.IntentParser")
def test_subcommand_interceptor_nl(mock_parser_class, mock_get_llm, mock_git_ops_class):
    # Setup mocks
    mock_git_ops = MagicMock()
    mock_git_ops_class.return_value = mock_git_ops
    
    mock_parser = MagicMock()
    mock_parser.parse_intent.return_value = {"commands": [], "explanation": "NL query matched"}
    mock_parser_class.return_value = mock_parser

    # We mock sys.argv to simulate running: ace add and commit
    with patch.object(sys, "argv", ["ace", "add", "and", "commit"]):
        # Run command without subcommand routing triggering
        result = runner.invoke(app, ["add", "and", "commit"])
        
    assert result.exit_code == 0
    # The IntentParser should have been called with the combined string
    mock_parser.parse_intent.assert_called_once_with("add and commit", offline=False)

@patch("ace.core.git_ops.GitOps")
def test_subcommand_interceptor_normal_subcmd(mock_git_ops_class):
    # Setup mock to fail staging of a non-existent file
    mock_git_ops = MagicMock()
    mock_git_ops.execute.side_effect = Exception("failed to stage")
    mock_git_ops_class.return_value = mock_git_ops

    # Simulate: ace add file1.txt (no NL indicators)
    with patch.object(sys, "argv", ["ace", "add", "file1.txt"]):
        result = runner.invoke(app, ["add", "file1.txt"])

    # Normal execution path: it routes to the add subcommand, tries to run git add, and fails
    assert result.exit_code == 1
    mock_git_ops.execute.assert_called_once_with("add file1.txt")
