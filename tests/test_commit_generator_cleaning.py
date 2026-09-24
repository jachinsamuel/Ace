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
