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

