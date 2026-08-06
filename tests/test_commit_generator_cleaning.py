import re

def clean_commit_message(message: str) -> str:
    match = re.search(r"```(?:gitcommit|text|markdown|json)?\s*(.*?)\s*```", message, re.DOTALL)
    if match:
        message = match.group(1).strip()
    else:
        message = message.replace("```", "").strip()

    lines = message.splitlines()
    junk_words = {
        "commit", "commit:", "commit message:", "suggested commit:", "proposed commit message:",
        "markdown", "text", "gitcommit", "json", "yaml", "code", "subject:", "title:", "message:"
    }
    while lines:
        first_line = lines[0].strip().lower()
        if (
            first_line in junk_words
            or first_line.startswith("here is")
            or first_line.startswith("sure")
            or first_line.startswith("below is")
        ):
            lines.pop(0)
        else:
            break
    return "\n".join(lines).strip()

def test_clean_commit_prefix():
    raw = "commit\nfeat(components): refactor FuzzyText component"
    assert clean_commit_message(raw) == "feat(components): refactor FuzzyText component"

    raw_markdown_word = "markdown\nfeat: add cyber-snake game component"
    assert clean_commit_message(raw_markdown_word) == "feat: add cyber-snake game component"

    raw_colon = "commit:\nfeat(ui): update styles"
    assert clean_commit_message(raw_colon) == "feat(ui): update styles"

    raw_markdown = "```markdown\nfeat(auth): fix token validation\n```"
    assert clean_commit_message(raw_markdown) == "feat(auth): fix token validation"

    raw_sure = "Sure, here is the suggested commit message:\n\nfeat(nav): update navbar styling"
    assert clean_commit_message(raw_sure) == "feat(nav): update navbar styling"
