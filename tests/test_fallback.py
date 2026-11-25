from unittest.mock import MagicMock, patch
from ace.ai.llm_factory import FallbackChatModel

def test_fallback_chat_model_primary_success():
    primary = MagicMock()
    primary.invoke.return_value = "Primary response"
    fallback = MagicMock()
    
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("test prompt")
    
    assert res == "Primary response"
    primary.invoke.assert_called_once_with("test prompt", config=None)
    fallback.invoke.assert_not_called()

def test_fallback_chat_model_primary_failure_fallback_success():
    primary = MagicMock()
    primary.invoke.side_effect = Exception("Connection refused / 503")
    
    fallback = MagicMock()
    fallback.invoke.return_value = "Fallback response"
    
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("test prompt")
    
    assert res == "Fallback response"
    primary.invoke.assert_called_once()
    fallback.invoke.assert_called_once_with("test prompt", config=None)

def test_fallback_chat_model_both_failures_heuristic_success():
    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")
    
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("conventional_commit staged changes diff")
    
    assert "feat:" in res.content

def test_fallback_chat_model_ignores_system_prompt_for_commit_classification():
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.commit import CONVENTIONAL_COMMIT_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    # System prompt contains "- docs: Documentation changes only" and "docs(readme): ..."
    # User message contains staged code file
    messages = [
        SystemMessage(content=CONVENTIONAL_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content="""
Repository Context:
- Current branch: master
- Sync status: Ahead by 0 commits, Behind by 0 commits.
- Project technology/types: Python
- Git operation state: Normal
- Commit conventions: Conventional Commits format is preferred.
- Staged files: ace/ui/display.py, pyproject.toml, README.md
- Unstaged changes: None
- Untracked files: None

Staged Diff:
\"\"\"
diff --git a/ace/ui/display.py b/ace/ui/display.py
--- a/ace/ui/display.py
+++ b/ace/ui/display.py
@@ -10,2 +10,2 @@
-def show_commit_message():
+def show_commit_message(): # fix styling
\"\"\"

Generate the commit message.
""")
    ]

    res = model.invoke(messages)
    # MUST NOT be docs since ace/ui/display.py is modified!
    assert not res.content.startswith("docs:")
    assert "ui" in res.content

def test_fallback_chat_model_docs_only_classification():
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.commit import CONVENTIONAL_COMMIT_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    messages = [
        SystemMessage(content=CONVENTIONAL_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content="""
Repository Context:
- Staged files: README.md

Staged Diff:
\"\"\"
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,2 @@
-Ace
+Ace CLI
\"\"\"
""")
    ]

    res = model.invoke(messages)
    assert res.content.startswith("docs(readme):")

def test_fallback_chat_model_code_review():
    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    res = model.invoke("Perform a code review and return findings with severity and score")
    assert '"score": 9.0' in res.content
    assert '"findings": []' in res.content

def test_fallback_chat_model_commit_with_pr_in_history():
    """Ensure git commit history containing 'Merge pull request' does NOT hijack commit generation into PR drafting."""
    import json
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.commit import CONVENTIONAL_COMMIT_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    messages = [
        SystemMessage(content=CONVENTIONAL_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content="""
Repository Context:
- Current branch: master
- Staged files: src/rag/pipeline.py, tests/test_rag.py
- Recent history:
  - a1b2c3d4 by dev: Merge pull request #12 from dev/video-parsing
  - e5f6a7b8 by dev: feat(video): add parser

Staged Diff:
\"\"\"
diff --git a/src/rag/pipeline.py b/src/rag/pipeline.py
--- a/src/rag/pipeline.py
+++ b/src/rag/pipeline.py
@@ -10,3 +10,3 @@
-def query(): pass
+def query(): return 42
\"\"\"

Generate the commit message.
""")
    ]

    res = model.invoke(messages)
    # Must NOT return PR template with "## Summary"
    assert "## Summary" not in res.content
    assert "## Key Changes" not in res.content
    assert res.content.startswith("feat")

def test_fallback_chat_model_pr_json_output():
    """Ensure PR drafting fallback returns valid JSON with title and body keys for PRDrafter."""
    import json
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.pr import PR_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    messages = [
        SystemMessage(content=PR_SYSTEM_PROMPT),
        HumanMessage(content="Current Branch: feat-pr\nBase Branch: master\nDiff: ...")
    ]

    res = model.invoke(messages)
    data = json.loads(res.content)
    assert "title" in data
    assert "body" in data
    assert "## Summary" in data["body"]

def test_fallback_chat_model_root_code_file_scope_no_extension():
    """Verify that root-level code files (e.g. web_verifier.py) do not have .py in scope or duplicate words."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.commit import CONVENTIONAL_COMMIT_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    user_prompt = (
        "Repository Context:\n"
        "- Staged files: web_verifier.py\n\n"
        "Staged Diff:\n"
        "diff --git a/web_verifier.py b/web_verifier.py\n"
        "--- a/web_verifier.py\n"
        "+++ b/web_verifier.py\n"
        "@@ -1,2 +1,3 @@\n"
        "+def verify_news(text): return True\n\n"
        "Generate the commit message."
    )
    messages = [
        SystemMessage(content=CONVENTIONAL_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]

    res = model.invoke(messages)
    assert ".py" not in res.content
    assert res.content == "feat(web_verifier): update implementation"


def test_fallback_chat_model_root_code_file_fix_action():
    """Verify that root-level code files with fix keywords produce clean fix scope and message."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.commit import CONVENTIONAL_COMMIT_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    user_prompt = (
        "Repository Context:\n"
        "- Staged files: web_verifier.py\n\n"
        "Staged Diff:\n"
        "diff --git a/web_verifier.py b/web_verifier.py\n"
        "--- a/web_verifier.py\n"
        "+++ b/web_verifier.py\n"
        "@@ -1,2 +1,3 @@\n"
        "-def verify(): error\n"
        "+def verify(): return fix_bug()\n\n"
        "Generate the commit message for bug fix."
    )
    messages = [
        SystemMessage(content=CONVENTIONAL_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]

    res = model.invoke(messages)
    assert ".py" not in res.content
    assert res.content == "fix(web_verifier): resolve issues in implementation"


def test_fallback_chat_model_latest_file_not_misclassified_as_test():
    """Verify filenames containing 'test' as a substring (e.g. latest.py) are treated as code, not tests."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.commit import CONVENTIONAL_COMMIT_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Read timed out")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama connection refused")

    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)
    messages = [
        SystemMessage(content=CONVENTIONAL_COMMIT_SYSTEM_PROMPT),
        HumanMessage(content="Repository Context:\n- Staged files: latest.py\n\nGenerate the commit message."),
    ]

    res = model.invoke(messages)
    assert not res.content.startswith("test:")
    assert res.content == "feat(latest): update implementation"


def test_fallback_chat_model_undo_and_ignore_return_valid_json():
    """Verify undo and ignore prompts receive valid JSON from heuristic fallback."""
    import json
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.ai.prompts.undo import UNDO_SYSTEM_PROMPT
    from ace.ai.prompts.ignore import IGNORE_SYSTEM_PROMPT

    primary = MagicMock()
    primary.invoke.side_effect = Exception("Offline")
    fallback = MagicMock()
    fallback.invoke.side_effect = Exception("Ollama down")
    model = FallbackChatModel(primary_llm=primary, fallback_llm=fallback)

    undo_res = model.invoke([SystemMessage(content=UNDO_SYSTEM_PROMPT), HumanMessage(content="Undo last")])
    undo_data = json.loads(undo_res.content)
    assert "commands" in undo_data and "explanation" in undo_data

    ignore_res = model.invoke([SystemMessage(content=IGNORE_SYSTEM_PROMPT), HumanMessage(content="Ignore logs")])
    ignore_data = json.loads(ignore_res.content)
    assert "rules" in ignore_data and "explanation" in ignore_data
