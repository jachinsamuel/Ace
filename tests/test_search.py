from unittest.mock import MagicMock, patch
from ace.ai.history_analyzer import HistoryAnalyzer
from ace.core.git_ops import GitOps

def test_semantic_search_success(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    # Mock get_log
    commits = [
        {
            "hexsha": "h12345",
            "summary": "fix bug in key validation",
            "message": "fix bug in key validation\n\nResolved nvidia API credential issue.",
            "author": "Author A",
            "date": "2026-06-08T12:00:00",
        }
    ]

    mock_response = MagicMock()
    mock_response.content = '{"matches": [{"hexsha": "h12345", "summary": "fix bug in key validation", "reason": "Mentions key validation and nvidia credentials."}]}'
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    analyzer = HistoryAnalyzer(git_ops)

    with patch.object(GitOps, "get_log", return_value=commits):
        with patch("ace.ai.history_analyzer.get_llm", return_value=mock_llm):
            res = analyzer.semantic_search("nvidia key bug")
            
            assert len(res["matches"]) == 1
            assert res["matches"][0]["hexsha"] == "h12345"
            assert "nvidia credentials" in res["matches"][0]["reason"]
            mock_llm.invoke.assert_called_once()

def test_semantic_search_no_commits(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    analyzer = HistoryAnalyzer(git_ops)

    with patch.object(GitOps, "get_log", return_value=[]):
        res = analyzer.semantic_search("any query")
        assert res == {"matches": []}
