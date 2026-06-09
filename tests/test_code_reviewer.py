from unittest.mock import MagicMock, patch
from ace.ai.code_reviewer import CodeReviewer
from ace.core.git_ops import GitOps

def test_code_reviewer_empty_diff(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    reviewer = CodeReviewer(git_ops)
    
    findings, score = reviewer.review_diff("")
    assert findings == []
    assert score == 10.0

def test_code_reviewer_success(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    # Mock LLM and response
    mock_response = MagicMock()
    mock_response.content = """
    {
        "score": 6.5,
        "findings": [
            {
                "category": "security",
                "severity": "critical",
                "line": 12,
                "description": "Hardcoded secret key found.",
                "fix": "SECRET_KEY = os.getenv('SECRET_KEY')"
            }
        ]
    }
    """
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    reviewer = CodeReviewer(git_ops)
    
    # Create a mock diff
    diff_text = """diff --git a/auth.py b/auth.py
index 12345..67890 100644
--- a/auth.py
+++ b/auth.py
@@ -10,5 +10,5 @@
-SECRET_KEY = "super-secret"
+SECRET_KEY = "super-secret-still"
"""

    with patch("ace.ai.code_reviewer.get_llm", return_value=mock_llm):
        findings, score = reviewer.review_diff(diff_text)
        
        assert score == 6.5
        assert len(findings) == 1
        assert findings[0]["file"] == "auth.py"
        assert findings[0]["category"] == "security"
        assert findings[0]["severity"] == "critical"
        assert findings[0]["line"] == 12
        assert "Hardcoded secret key found" in findings[0]["description"]
        assert "os.getenv" in findings[0]["fix"]

def test_code_reviewer_invalid_json(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    mock_response = MagicMock()
    mock_response.content = "Invalid non-JSON response"
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    reviewer = CodeReviewer(git_ops)
    
    diff_text = """diff --git a/auth.py b/auth.py
index 12345..67890 100644
--- a/auth.py
+++ b/auth.py
@@ -10,5 +10,5 @@
-SECRET_KEY = "super-secret"
+SECRET_KEY = "super-secret-still"
"""

    with patch("ace.ai.code_reviewer.get_llm", return_value=mock_llm):
        findings, score = reviewer.review_diff(diff_text)
        
        # Should gracefully return failure finding rather than crashing
        assert len(findings) == 1
        assert findings[0]["file"] == "auth.py"
        assert "AI review failed" in findings[0]["description"]
        assert score == 10.0
