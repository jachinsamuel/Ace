import re

def clean_commit_message(message: str) -> str:
    match = re.search(r"```(?:gitcommit|text)?\s*(.*?)\s*```", message, re.DOTALL)
    if match:
        message = match.group(1).strip()
    else:
        message = message.replace("```", "").strip()

    lines = message.splitlines()
    while lines:
        first_line = lines[0].strip().lower()
        if first_line in ("commit", "commit:", "commit message:", "suggested commit:", "proposed commit message:") or first_line.startswith("here is the commit"):
            lines.pop(0)
        else:
            break
    return "\n".join(lines).strip()

def test_clean_commit_prefix():
    raw = "commit\nfeat(components): refactor FuzzyText component"
    assert clean_commit_message(raw) == "feat(components): refactor FuzzyText component"

    raw_colon = "commit:\nfeat(ui): update styles"
    assert clean_commit_message(raw_colon) == "feat(ui): update styles"

    raw_markdown = "```text\ncommit\nfix(auth): fix token validation\n```"
    assert clean_commit_message(raw_markdown) == "fix(auth): fix token validation"
