from unittest.mock import MagicMock, patch
from ace.ai.history_analyzer import HistoryAnalyzer

def test_analyze_blame():
    mock_git_ops = MagicMock()
    analyzer = HistoryAnalyzer(mock_git_ops)

    commit_info = {
        "hexsha": "12345678",
        "author": "Jachin Samuel",
        "date": "2026-07-14",
        "summary": "Fix login bug",
        "message": "Detailed description of login fix",
    }

    with patch("ace.ai.history_analyzer.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "### Why this line was written\nTo fix the login check."
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        res = analyzer.analyze_blame(
            file="src/auth.py",
            line=45,
            commit_info=commit_info,
            commit_show_output="git show diff output",
            line_content="if not user.is_authenticated:",
        )
        assert "To fix the login check" in res
        assert mock_llm.invoke.call_count == 1
