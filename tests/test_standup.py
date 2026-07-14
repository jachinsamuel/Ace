from unittest.mock import MagicMock, patch
from ace.ai.history_analyzer import HistoryAnalyzer

def test_generate_standup():
    mock_git_ops = MagicMock()
    analyzer = HistoryAnalyzer(mock_git_ops)

    commits = [
        {"hexsha": "1234567890", "summary": "Initial Commit", "author": "Jachin Samuel"},
        {"hexsha": "abcdef0123", "summary": "Fix login bug", "author": "Jachin Samuel"}
    ]

    with patch("ace.ai.history_analyzer.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Yesterday:\n- Fixed bug\n- Initial commit\n\nToday:\n- Add features"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        res = analyzer.generate_standup(commits)
        assert "Fixed bug" in res
        assert mock_llm.invoke.call_count == 1

def test_generate_standup_empty():
    mock_git_ops = MagicMock()
    analyzer = HistoryAnalyzer(mock_git_ops)
    res = analyzer.generate_standup([])
    assert "No recent commits found" in res
