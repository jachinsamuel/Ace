import re
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.core.context import RepoContext
from ace.ai.llm_factory import get_llm
from ace.utils.diff_parser import trim_diff
from ace.ai.prompts.commit import (
    CONVENTIONAL_COMMIT_SYSTEM_PROMPT,
    SIMPLE_COMMIT_SYSTEM_PROMPT,
    DETAILED_COMMIT_SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)

class NoStagedChangesError(Exception):
    """Raised when trying to generate a commit message but no changes are staged."""
    pass

def clean_commit_text(message: str) -> str:
    # 1. Clean markdown code fences (```gitcommit, ```markdown, ```text, ```)
    match = re.search(r"```(?:gitcommit|text|markdown|json|yaml)?\s*(.*?)\s*```", message, re.DOTALL)
    if match:
        message = match.group(1).strip()
    else:
        message = message.replace("```", "").strip()

    # 2. Split lines and strip leading conversational wrappers or markdown headers
    lines = message.splitlines()
    junk_patterns = [
        r"^(#+\s*)?(commit|commit\s*message|suggested\s*commit|proposed\s*commit(\s*message)?|gitcommit|markdown|text|json|yaml|code)\s*:?$",
        r"^(#+\s*)?(summary|overview|key\s*changes|changes|description|notes|details|verification)\s*:?$",
        r"^(subject|title|message)\s*:\s*$",
        r"^(here\s+is|sure|below\s+is|this\s+commit).*",
    ]

    while lines:
        raw_first = lines[0].strip()
        # Strip outer bold/italic markup: **Summary** -> Summary
        raw_first = re.sub(r"^\*+|\*+$", "", raw_first).strip()
        first_lower = raw_first.lower()
        if not raw_first:
            lines.pop(0)
            continue

        if any(re.match(p, first_lower) for p in junk_patterns):
            lines.pop(0)
        else:
            break

    if not lines:
        return ""

    # 3. Clean line prefixes: strip leading markdown header markers (#, ##, ###) and bold wrappers
    cleaned_lines = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        # Strip markdown header prefixes: e.g. "## Key Changes" -> "Key Changes"
        trimmed = re.sub(r"^#+\s*", "", trimmed).strip()

        # If it's the very first line and starts with a bullet point, strip bullet:
        # e.g. "- Update project files" -> "Update project files"
        if not cleaned_lines and re.match(r"^[\*\-\•\+]\s+", trimmed):
            trimmed = re.sub(r"^[\*\-\•\+]\s+", "", trimmed).strip()

        # Strip full bold wrappers: e.g. "**feat(core): fix bug**" -> "feat(core): fix bug"
        match_bold = re.match(r"^\*\*(.+?)\*\*$", trimmed)
        if match_bold:
            trimmed = match_bold.group(1).strip()

        cleaned_lines.append(trimmed)

    # 4. Deduplicate repeating runaway lines or loops (common in smaller local models)
    deduped_lines = []
    seen_lines_count = {}
    for line in cleaned_lines:
        trimmed = line.strip()
        if not trimmed:
            if deduped_lines and deduped_lines[-1] != "":
                deduped_lines.append("")
            continue

        # Normalized version for comparison (strip bullets, numbering, whitespace, punctuation)
        norm = re.sub(r"^[\*\-\•\d\.\s]+", "", trimmed).lower().strip()
        norm = re.sub(r"[^\w\s]", "", norm)
        if norm:
            seen_lines_count[norm] = seen_lines_count.get(norm, 0) + 1
            if seen_lines_count[norm] > 1:
                continue

        deduped_lines.append(line)

    # 5. Cap body length to prevent runaway generation (max 15 lines total)
    if len(deduped_lines) > 15:
        deduped_lines = deduped_lines[:15]

    return "\n".join(deduped_lines).strip()

class CommitGenerator:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops
        self.context_builder = RepoContext(git_ops)

    def generate_message(self, format_type: str = "conventional", offline: bool = False) -> str:
        """
        Analyze staged changes and generate a commit message using the configured AI.
        """
        # Ensure we have staged changes
        status = self.git_ops.get_status()
        if not status["staged"]:
            raise NoStagedChangesError("No changes are staged for commit. Stage files first using 'git add'.")

        staged_diff = self.git_ops.get_staged_diff()
        has_content_changes = False
        for line in staged_diff.splitlines():
            if (line.startswith("+") and not line.startswith("+++")) or (line.startswith("-") and not line.startswith("---")):
                has_content_changes = True
                break

        if not has_content_changes:
            raise NoStagedChangesError("Staged diff is empty. Cannot generate commit message.")

        # Format context
        repo_context = self.context_builder.format_context_for_prompt()

        # Select system prompt based on format
        if format_type == "conventional":
            system_prompt = CONVENTIONAL_COMMIT_SYSTEM_PROMPT
        elif format_type == "simple":
            system_prompt = SIMPLE_COMMIT_SYSTEM_PROMPT
        elif format_type == "detailed":
            system_prompt = DETAILED_COMMIT_SYSTEM_PROMPT
        else:
            system_prompt = CONVENTIONAL_COMMIT_SYSTEM_PROMPT

        user_prompt = USER_PROMPT_TEMPLATE.format(
            repo_context=repo_context,
            staged_diff=trim_diff(staged_diff, max_chars=15000)  # Cap diff to avoid context window limit and timeout
        )

        from ace.core.config import get_config
        from ace.utils.i18n import get_language_instruction

        lang_inst = get_language_instruction(get_config().ai.language)

        messages = [
            SystemMessage(content=system_prompt + lang_inst),
            HumanMessage(content=user_prompt)
        ]

        # Get LLM and run inference
        llm = get_llm(offline_override=offline)
        try:
            response = llm.invoke(messages)
            message = response.content.strip()
        except Exception as e:
            raise Exception(f"AI commit message generation failed: {e}")
        
        # Clean response and filter runaway repetition loops
        message = clean_commit_text(message)

        staged_files = status.get("staged", [])
        total_files = len(staged_files)
        main_file = staged_files[0].replace("\\", "/").split("/")[-1] if staged_files else "project files"

        if not message:
            return f"feat: update {main_file} and related files"

        # Ensure Conventional Commit format on subject line (especially for local Ollama models)
        if format_type == "conventional":
            msg_lines = message.splitlines()
            first_line = msg_lines[0].strip()

            def infer_commit_type(text: str) -> str:
                t_lower = text.lower()
                if any(k in t_lower for k in ("fix", "bug", "error", "repair", "resolve", "correct", "patch")):
                    return "fix"
                if any(k in t_lower for k in ("refactor", "clean", "simplify", "restructure", "optimize")):
                    return "refactor"
                if any(k in t_lower for k in ("perf", "performance", "speed")):
                    return "perf"
                if any(k in t_lower for k in ("doc", "readme", "guide")):
                    return "docs"
                if any(k in t_lower for k in ("test", "spec", "coverage")):
                    return "test"
                if any(k in t_lower for k in ("build", "dep", "dependency", "ci", "docker")):
                    return "build"

                doc_count = sum(1 for f in staged_files if f.lower().endswith((".md", ".rst", ".txt")) or "docs/" in f.lower())
                test_count = sum(1 for f in staged_files if "test" in f.lower() or f.lower().startswith("tests/"))
                build_count = sum(1 for f in staged_files if f.lower().startswith((".github", "dockerfile")) or f.lower().endswith((".toml", ".json", ".lock", ".yaml", ".yml")))

                if total_files > 0 and doc_count == total_files:
                    return "docs"
                if total_files > 0 and (test_count == total_files or (test_count > 0 and test_count + doc_count == total_files)):
                    return "test"
                if total_files > 0 and build_count == total_files:
                    return "build"
                return "feat"

            conv_match = re.match(
                r"^((?:feat|fix|docs|style|refactor|perf|test|build|ci|chore)(?:\([a-zA-Z0-9_\-/\.]+\))?!?:?)\s*(.*)$",
                first_line,
                re.IGNORECASE,
            )

            generic_words = {"summary", "key changes", "changes", "overview", "verification", "details", "update", "updates"}

            if conv_match:
                prefix = conv_match.group(1).lower().rstrip(":") + ":"
                subj = conv_match.group(2).strip()
                subj = re.sub(r"^[#\*\-\•\+\s:]+", "", subj).strip()

                if subj.lower() in generic_words or len(subj) < 3:
                    candidate = None
                    for line in msg_lines[1:]:
                        cleaned_candidate = re.sub(r"^[#\*\-\•\+\s:]+", "", line).strip()
                        if cleaned_candidate and cleaned_candidate.lower() not in generic_words and len(cleaned_candidate) >= 3:
                            candidate = cleaned_candidate
                            break
                    if candidate:
                        subj = candidate[0].lower() + candidate[1:]
                    else:
                        subj = f"update {main_file} and related files"
                else:
                    subj = subj[0].lower() + subj[1:]

                subj = subj.rstrip(".")
                msg_lines[0] = f"{prefix} {subj}"
                message = "\n".join(msg_lines).strip()
            else:
                inferred_type = infer_commit_type(first_line)
                subj = re.sub(r"^[#\*\-\•\+\s:]+", "", first_line).strip()

                if subj.lower() in generic_words or len(subj) < 3:
                    candidate = None
                    for line in msg_lines[1:]:
                        cleaned_candidate = re.sub(r"^[#\*\-\•\+\s:]+", "", line).strip()
                        if cleaned_candidate and cleaned_candidate.lower() not in generic_words and len(cleaned_candidate) >= 3:
                            candidate = cleaned_candidate
                            break
                    if candidate:
                        subj = candidate[0].lower() + candidate[1:]
                    else:
                        subj = f"update {main_file} and related files"
                else:
                    subj = subj[0].lower() + subj[1:]

                subj = subj.rstrip(".")
                msg_lines[0] = f"{inferred_type}: {subj}"
                message = "\n".join(msg_lines).strip()

        return message
