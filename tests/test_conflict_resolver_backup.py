import pytest
from pathlib import Path
from unittest.mock import MagicMock
from ace.ai.conflict_resolver import ConflictResolver, ConflictResolverError

def test_apply_resolution_creates_backup_and_atomic_swap(tmp_path):
    # Setup mock git_ops working dir
    mock_git_ops = MagicMock()
    mock_git_ops.working_dir = str(tmp_path)
    
    # Create a test conflicted file
    test_file = tmp_path / "conflict.txt"
    test_content = "<<<<<<< HEAD\nlocal changes\n=======\nincoming changes\n>>>>>>> branch\n"
    test_file.write_text(test_content, encoding="utf-8")
    
    resolver = ConflictResolver(mock_git_ops)
    
    # Replacement block
    block = "<<<<<<< HEAD\nlocal changes\n=======\nincoming changes\n>>>>>>> branch"
    replacement = "resolved changes"
    
    # Run resolution
    resolver.apply_resolution("conflict.txt", [(block, replacement)])
    
    # Assert resolution succeeded
    assert test_file.read_text(encoding="utf-8") == "resolved changes\n"
    
    # Assert backup file was cleaned up (no extra .bak files remain)
    bak_files = list(tmp_path.glob("conflict.txt.bak-*"))
    assert len(bak_files) == 0

def test_apply_resolution_fails_and_restores(tmp_path):
    mock_git_ops = MagicMock()
    mock_git_ops.working_dir = str(tmp_path)
    
    test_file = tmp_path / "conflict.txt"
    test_content = "<<<<<<< HEAD\noriginal content\n>>>>>>> branch"
    test_file.write_text(test_content, encoding="utf-8")
    
    resolver = ConflictResolver(mock_git_ops)
    
    # Block that doesn't exist to force failure
    non_existent_block = "no match"
    
    with pytest.raises(ConflictResolverError, match="Conflict block not found"):
        resolver.apply_resolution("conflict.txt", [(non_existent_block, "bad replacement")])
        
    # Assert original content was preserved/restored
    assert test_file.read_text(encoding="utf-8") == test_content
