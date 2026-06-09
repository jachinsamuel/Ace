from typer.testing import CliRunner
from ace.cli import app

runner = CliRunner()

def test_help_command():
    # Invoke the help command via CliRunner
    result = runner.invoke(app, ["help"])
    
    # Assert successful exit code
    assert result.exit_code == 0
    
    # Assert expected visual cues and sections exist in output
    assert "Ace AI Git Copilot" in result.stdout
    assert "Natural Language Interface" in result.stdout
    assert "Core Ace Commands" in result.stdout
    assert "setup" in result.stdout
    assert "config" in result.stdout
    assert "dash" in result.stdout
    assert "Tips & Tricks" in result.stdout
