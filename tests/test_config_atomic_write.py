import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ace.core.config import save_config, Config

@patch("ace.core.config.DEFAULT_CONFIG_DIR")
@patch("ace.core.config.DEFAULT_CONFIG_PATH")
def test_save_config_atomic(mock_config_path, mock_config_dir, tmp_path):
    # Setup tmp directory for config file
    config_dir = tmp_path / ".ace"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    
    mock_config_dir.mkdir = MagicMock()
    mock_config_dir.__truediv__ = MagicMock(return_value=config_file)
    # Configure path patch
    mock_config_path.open = config_file.open
    mock_config_path.parent = config_dir
    mock_config_path.exists = config_file.exists
    
    # We patch DEFAULT_CONFIG_DIR and DEFAULT_CONFIG_PATH directly inside the function
    with patch("ace.core.config.DEFAULT_CONFIG_DIR", config_dir), \
         patch("ace.core.config.DEFAULT_CONFIG_PATH", config_file):
        
        cfg = Config({
            "ai": {
                "provider": "openai",
                "openai_model": "gpt-4o-mini"
            }
        })
        
        save_config(cfg)
        
        # Verify content was written
        assert config_file.exists()
        content = config_file.read_text(encoding="utf-8")
        assert "provider = \"openai\"" in content
        
        # Verify no temp files are left in the directory
        temp_files = list(config_dir.glob("config-*.tmp"))
        assert len(temp_files) == 0
