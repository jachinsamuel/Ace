from unittest.mock import MagicMock, patch
from ace.ai.history_analyzer import HistoryAnalyzer
from ace.core.git_ops import GitOps

def test_history_analyzer_summarize(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    mock_response = MagicMock()
    mock_response.content = "Summary of commits: feature A added."
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    
    analyzer = HistoryAnalyzer(git_ops)
    
    with patch("ace.ai.history_analyzer.get_llm", return_value=mock_llm):
        res = analyzer.summarize_query("what did I work on", "git log", "commit details")
        assert res == "Summary of commits: feature A added."
        mock_llm.invoke.assert_called_once()

def test_history_analyzer_repo_stats(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    # Mock git_ops.execute for log data
    log_data = (
        "h1|Author A|Mon Jun 8 12:00:00 2026\n"
        "h2|Author A|Mon Jun 8 11:00:00 2026\n"
        "h3|Author B|Mon Jun 8 10:00:00 2026\n"
    )
    
    analyzer = HistoryAnalyzer(git_ops)
    
    with patch.object(GitOps, "execute", return_value=log_data):
        stats = analyzer.get_repo_stats()
        
        assert stats["total_commits"] == 3
        assert stats["contributors"][0] == ("Author A", 2)
        assert stats["contributors"][1] == ("Author B", 1)
        assert "total_branches" in stats
        assert "staged_count" in stats

def test_history_analyzer_numstat_parsing(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    analyzer = HistoryAnalyzer(git_ops)
    
    mock_execute = MagicMock()
    mock_execute.side_effect = [
        "h1|Author A|Mon Jun 8 12:00:00 2026\n",  # 1st call: log commits
        "\"AUTHOR:Author A\"\n\n8\t0\tfile1.py\n\"AUTHOR:Author B\"\n\n12\t4\tfile2.py",  # 2nd call: log --numstat
        "file1.py\nfile2.py",                     # 3rd call: ls-files
        "2026-06-08"                              # 4th call: log dates
    ]
    
    with patch.object(GitOps, "execute", mock_execute):
        stats = analyzer.get_repo_stats()
        lines_info = stats.get("lines_per_author", {})
        
        assert "Author A" in lines_info
        assert lines_info["Author A"]["added"] == 8
        assert lines_info["Author A"]["deleted"] == 0
        
        assert "Author B" in lines_info
        assert lines_info["Author B"]["added"] == 12
        assert lines_info["Author B"]["deleted"] == 4

