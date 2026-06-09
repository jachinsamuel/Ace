from unittest.mock import MagicMock, patch
from ace.ai.changelog_generator import ChangelogGenerator
from ace.core.git_ops import GitOps

def test_changelog_generator_empty_log(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    # We mock git_ops.execute to return empty log
    with patch.object(GitOps, "execute", return_value=""):
        generator = ChangelogGenerator(git_ops)
        res = generator.generate_changelog()
        assert res == "No commits found in the specified range."

def test_changelog_generator_success(temp_git_repo):
    repo_path, repo = temp_git_repo
    git_ops = GitOps(repo_path=str(repo_path))
    
    commit_log = (
        "a1b2c3d4e5f6|Mon Jun 8 12:00:00 2026|John Doe|feat: oauth2 implementation\n"
        "added google oauth flow\n"
        "f6e5d4c3b2a1|Mon Jun 8 11:00:00 2026|Jane Doe|fix: token expiry bug\n"
        "tokens expired too quickly"
    )
    
    mock_response = MagicMock()
    mock_response.content = """
    ## v1.1.0 Changelog
    
    ### Features
    - **auth**: Implement Google OAuth2 flow
    
    ### Bug Fixes
    - **auth**: Fix token expiry issue
    """
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    
    generator = ChangelogGenerator(git_ops)
    
    with patch.object(GitOps, "execute", return_value=commit_log):
        with patch("ace.ai.changelog_generator.get_llm", return_value=mock_llm):
            res = generator.generate_changelog()
            assert "## v1.1.0 Changelog" in res
            assert "Google OAuth2 flow" in res
            assert "Fix token expiry issue" in res
            mock_llm.invoke.assert_called_once()
