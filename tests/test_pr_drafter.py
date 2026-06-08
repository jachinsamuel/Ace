from unittest.mock import MagicMock, patch
import pytest
from ace.ai.pr_drafter import PRDrafter
from ace.core.git_ops import GitOps

def test_pr_drafter_success(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    # Create dummy commit to draft against (base_branch is master or main)
    # We will create a file, commit it, then create another commit on branch
    file_path = repo_path / "test.txt"
    file_path.write_text("initial content")
    repo.index.add([str(file_path)])
    repo.index.commit("initial commit")

    # Create new branch
    new_branch = repo.create_head("feature-branch")
    new_branch.checkout()

    file_path.write_text("updated content")
    repo.index.add([str(file_path)])
    repo.index.commit("updated file")

    # Mock the LLM to return a valid JSON response
    mock_response = MagicMock()
    mock_response.content = '{"title": "feat: update test file", "body": "This PR updates the test file."}'
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    drafter = PRDrafter(git_ops)

    with patch("ace.ai.pr_drafter.get_llm", return_value=mock_llm):
        # We use master or main depending on repo init default
        base_branch = "master" if "master" in git_ops.get_branches() else "main"
        res = drafter.draft_pr(base_branch)
        
        assert res["title"] == "feat: update test file"
        assert res["body"] == "This PR updates the test file."
        mock_llm.invoke.assert_called_once()

def test_pr_drafter_no_commits(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    # Create dummy commit to start
    file_path = repo_path / "test.txt"
    file_path.write_text("initial content")
    repo.index.add([str(file_path)])
    repo.index.commit("initial commit")

    drafter = PRDrafter(git_ops)
    base_branch = "master" if "master" in git_ops.get_branches() else "main"

    with pytest.raises(Exception, match="No commits found"):
        drafter.draft_pr(base_branch)

def test_pr_drafter_missing_keys(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))

    file_path = repo_path / "test.txt"
    file_path.write_text("initial content")
    repo.index.add([str(file_path)])
    repo.index.commit("initial commit")

    new_branch = repo.create_head("feature-branch")
    new_branch.checkout()

    file_path.write_text("updated content")
    repo.index.add([str(file_path)])
    repo.index.commit("updated file")

    mock_response = MagicMock()
    # Missing 'body' key
    mock_response.content = '{"title": "feat: update test file"}'
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    drafter = PRDrafter(git_ops)
    base_branch = "master" if "master" in git_ops.get_branches() else "main"

    with patch("ace.ai.pr_drafter.get_llm", return_value=mock_llm):
        with pytest.raises(Exception, match="missing 'title' or 'body' keys"):
            drafter.draft_pr(base_branch)
