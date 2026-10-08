from ace.ai.commit_generator import clean_commit_text

def test_clean_commit_prefix():
    raw = "commit\nfeat(components): refactor FuzzyText component"
    assert clean_commit_text(raw) == "feat(components): refactor FuzzyText component"

    raw_markdown_word = "markdown\nfeat: add cyber-snake game component"
    assert clean_commit_text(raw_markdown_word) == "feat: add cyber-snake game component"

    raw_colon = "commit:\nfeat(ui): update styles"
    assert clean_commit_text(raw_colon) == "feat(ui): update styles"

    raw_markdown = "```markdown\nfeat(auth): fix token validation\n```"
    assert clean_commit_text(raw_markdown) == "feat(auth): fix token validation"

    raw_sure = "Sure, here is the suggested commit message:\n\nfeat(nav): update navbar styling"
    assert clean_commit_text(raw_sure) == "feat(nav): update navbar styling"

def test_clean_commit_deduplicates_repetitive_lines():
    repeated_sentence = (
        "The commit also includes a new JavaScript function `updateVideoGeneratingKeyFrameDensity` "
        "that updates the generating key frame density of the video player."
    )
    raw = (
        "feat(markdown): add support for AI Video blocks in markdown parsing\n\n"
        "- Add support for AI Video blocks in markdown parsing.\n"
        f"- {repeated_sentence}\n"
        f"- {repeated_sentence}\n"
        f"- {repeated_sentence}\n"
        f"- {repeated_sentence}\n"
        f"- {repeated_sentence}\n"
    )
    cleaned = clean_commit_text(raw)
    assert cleaned.count("updateVideoGeneratingKeyFrameDensity") == 1
    assert "feat(markdown):" in cleaned

def test_clean_commit_caps_excessive_length():
    lines = ["feat(core): major update\n"]
    for i in range(50):
        lines.append(f"- Unique change item number {i}")
    raw = "\n".join(lines)
    cleaned = clean_commit_text(raw)
    assert len(cleaned.splitlines()) <= 15

def test_generate_message_fallback_type_formatting():
    from unittest.mock import MagicMock, patch
    from ace.ai.commit_generator import CommitGenerator

    mock_git_ops = MagicMock()
    mock_git_ops.get_status.return_value = {"staged": ["app/main.py"], "unstaged": [], "untracked": []}
    mock_git_ops.get_staged_diff.return_value = "+ def hello(): pass"
    mock_git_ops.working_dir = "."
    mock_git_ops.get_log.return_value = []
    mock_git_ops.get_current_branch.return_value = "main"
    mock_git_ops.get_upstream_tracking.return_value = None
    mock_git_ops.get_ahead_behind.return_value = {"ahead": 0, "behind": 0}

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "added new greeting function"
    mock_llm.invoke.return_value = mock_response

    with patch("ace.ai.commit_generator.get_llm", return_value=mock_llm):
        generator = CommitGenerator(mock_git_ops)
        msg = generator.generate_message(format_type="conventional")
        assert msg == "feat: added new greeting function"

def test_clean_commit_strips_markdown_headers_and_pr_templates():
    raw_pr = (
        "## Summary\n\n"
        "- Update video blocks in markdown parsing\n\n"
        "## Key Changes\n\n"
        "- Add parseVideoBlock implementation\n\n"
        "## Verification\n\n"
        "- Verified locally."
    )
    cleaned = clean_commit_text(raw_pr)
    lines = cleaned.splitlines()
    assert lines[0] == "Update video blocks in markdown parsing"
    assert "## Summary" not in cleaned
    assert "## Key Changes" not in cleaned
    assert "Key Changes" in cleaned
    assert "#" not in cleaned

def test_commit_generator_handles_pr_template_and_prevents_header_subjects():
    from unittest.mock import MagicMock, patch
    from ace.ai.commit_generator import CommitGenerator

    mock_git_ops = MagicMock()
    mock_git_ops.get_status.return_value = {
        "staged": ["rag/pipeline.py", "tests/test_rag.py"],
        "unstaged": [],
        "untracked": []
    }
    mock_git_ops.get_staged_diff.return_value = "+ def rag(): pass"
    mock_git_ops.working_dir = "."
    mock_git_ops.get_log.return_value = []
    mock_git_ops.get_current_branch.return_value = "main"
    mock_git_ops.get_upstream_tracking.return_value = None
    mock_git_ops.get_ahead_behind.return_value = {"ahead": 0, "behind": 0}

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = (
        "## Summary\n\n"
        "- Update project files and configuration.\n\n"
        "## Key Changes\n\n"
        "- Core improvements and updates.\n\n"
        "## Verification\n\n"
        "- Verified locally with test suite."
    )
    mock_llm.invoke.return_value = mock_response

    with patch("ace.ai.commit_generator.get_llm", return_value=mock_llm):
        generator = CommitGenerator(mock_git_ops)
        msg = generator.generate_message(format_type="conventional")
        # Must be conventional feat and NOT "test: ## Summary"
        assert msg.startswith("feat: update project files and configuration")
        assert "##" not in msg
        assert "Summary" not in msg.splitlines()[0]

def test_commit_generator_type_inference_not_greedy():
    from unittest.mock import MagicMock, patch
    from ace.ai.commit_generator import CommitGenerator

    mock_git_ops = MagicMock()
    # 2 python files, 1 test file, 1 readme file
    mock_git_ops.get_status.return_value = {
        "staged": ["app/main.py", "app/utils.py", "tests/test_main.py", "README.md"],
        "unstaged": [],
        "untracked": []
    }
    mock_git_ops.get_staged_diff.return_value = "+ def run(): pass"
    mock_git_ops.working_dir = "."
    mock_git_ops.get_log.return_value = []
    mock_git_ops.get_current_branch.return_value = "main"
    mock_git_ops.get_upstream_tracking.return_value = None
    mock_git_ops.get_ahead_behind.return_value = {"ahead": 0, "behind": 0}

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "add authentication service"
    mock_llm.invoke.return_value = mock_response

    with patch("ace.ai.commit_generator.get_llm", return_value=mock_llm):
        generator = CommitGenerator(mock_git_ops)
        msg = generator.generate_message(format_type="conventional")
        # Should be feat, NOT test or docs
        assert msg.startswith("feat: add authentication service")

def test_clean_commit_unpacks_inline_bullets_into_body():
    """Verify that inline bullets joined by ' - ' on a single line are unpacked into subject + body bullets."""
    raw = (
        "refactor(ui): remove unused forensic stylometry and evidence matrix components - "
        "Remove unused JavaScript code for forensic stylometry and evidence matrix - "
        "Remove unused HTML elements for forensic stylometry and evidence matrix - "
        "Update CSS styles to reflect the removal of unused components - "
        "Remove unused data properties for forensic stylometry and evidence matrix"
    )
    cleaned = clean_commit_text(raw)
    lines = cleaned.splitlines()

    # Subject line must be <= 72 characters
    subject = lines[0]
    assert len(subject) <= 72
    assert subject == "refactor(ui): remove unused forensic stylometry"

    # Must have blank line separator before body
    assert lines[1] == ""

    # Subsequent lines must be individual bullet points including overflow clause
    body = "\n".join(lines[2:])
    assert "evidence matrix components" in body.lower()
    assert "- Remove unused JavaScript code" in body
    assert "- Remove unused HTML elements" in body
    assert "- Update CSS styles" in body
    assert "- Remove unused data properties" in body

def test_commit_generator_enforces_strict_72_char_subject():
    """Verify that long subject lines are automatically truncated at clause/word boundaries and overflow is moved to body."""
    from unittest.mock import MagicMock, patch
    from ace.ai.commit_generator import CommitGenerator

    mock_git_ops = MagicMock()
    mock_git_ops.get_status.return_value = {
        "staged": ["auth/service.py"],
        "unstaged": [],
        "untracked": []
    }
    mock_git_ops.get_staged_diff.return_value = "+ def auth(): pass"
    mock_git_ops.working_dir = "."
    mock_git_ops.get_log.return_value = []
    mock_git_ops.get_current_branch.return_value = "main"
    mock_git_ops.get_upstream_tracking.return_value = None
    mock_git_ops.get_ahead_behind.return_value = {"ahead": 0, "behind": 0}

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = (
        "feat(auth): implement advanced multi-factor authentication system with biometric hardware token support and fallback SMS verification"
    )
    mock_llm.invoke.return_value = mock_response

    with patch("ace.ai.commit_generator.get_llm", return_value=mock_llm):
        generator = CommitGenerator(mock_git_ops)
        msg = generator.generate_message(format_type="conventional")
        lines = msg.splitlines()
        subject = lines[0]

        # Subject line must strictly be <= 72 chars
        assert len(subject) <= 72
        assert subject.startswith("feat(auth):")
        # Overflow text must be preserved in the body
        assert len(lines) > 1
        body = "\n".join(lines[1:])
        assert "biometric" in body.lower()


