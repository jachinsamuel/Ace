import os
import shutil
import tempfile
from pathlib import Path
import git
import pytest

@pytest.fixture
def temp_git_repo():
    """Create a temporary directory initialized as a git repository."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Initialize repo
    repo = git.Repo.init(repo_path)
    
    # Configure dummy user for committing
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test User")
        cw.set_value("user", "email", "test@example.com")
        
    yield repo_path, repo
    
    # Cleanup after test
    try:
        shutil.rmtree(temp_dir)
    except OSError:
        pass
