from unittest.mock import MagicMock, patch
from ace.utils.conflict_parser import parse_conflict_file
from ace.ai.conflict_resolver import ConflictResolver
from ace.core.git_ops import GitOps

def test_parse_conflict_file():
    content = """
Some text
<<<<<<< HEAD
my local changes
=======
their incoming changes
>>>>>>> main
Other text
<<<<<<< HEAD
local changes 2
=======
incoming changes 2
>>>>>>> main
End text
"""
    blocks = parse_conflict_file(content)
    assert len(blocks) == 2
    assert blocks[0]["head"] == "my local changes"
    assert blocks[0]["incoming"] == "their incoming changes"
    assert blocks[0]["head_branch"] == "HEAD"
    assert blocks[0]["incoming_branch"] == "main"
    assert "<<<<<<< HEAD" in blocks[0]["full_block"]
    
    assert blocks[1]["head"] == "local changes 2"
    assert blocks[1]["incoming"] == "incoming changes 2"

def test_conflict_resolver_suggestions(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    # Create a file with conflicts
    conflicted_file = repo_path / "app.py"
    conflict_content = """<<<<<<< HEAD
local_var = 1
=======
incoming_var = 2
>>>>>>> main"""
    conflicted_file.write_text(conflict_content, encoding="utf-8")
    
    mock_response = MagicMock()
    mock_response.content = """
    {
        "merged_content": "merged_var = 3",
        "explanation": "Merged variables."
    }
    """
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    resolver = ConflictResolver(git_ops)
    
    with patch("ace.ai.conflict_resolver.get_llm", return_value=mock_llm):
        suggestions = resolver.get_suggestions("app.py")
        assert len(suggestions) == 1
        assert suggestions[0]["suggested_merged"] == "merged_var = 3"
        assert suggestions[0]["explanation"] == "Merged variables."

def test_conflict_resolver_apply(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    conflicted_file = repo_path / "app.py"
    conflict_content = """line 1
<<<<<<< HEAD
local_var = 1
=======
incoming_var = 2
>>>>>>> main
line 3"""
    conflicted_file.write_text(conflict_content, encoding="utf-8")
    
    resolver = ConflictResolver(git_ops)
    
    replacements = [
        (
            """<<<<<<< HEAD
local_var = 1
=======
incoming_var = 2
>>>>>>> main""",
            "merged_var = 3"
        )
    ]
    
    resolver.apply_resolution("app.py", replacements)
    
    resolved_content = conflicted_file.read_text(encoding="utf-8")
    assert resolved_content == "line 1\nmerged_var = 3\nline 3"
