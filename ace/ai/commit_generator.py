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
            staged_diff=trim_diff(staged_diff, max_chars=25000)  # Cap diff to avoid context window limit
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
        
        # Clean response (remove extra leading/trailing whitespace or markdown fences)
        import re
        match = re.search(r"```(?:gitcommit|text|markdown|json)?\s*(.*?)\s*```", message, re.DOTALL)
        if match:
            message = match.group(1).strip()
        else:
            message = message.replace("```", "").strip()

        # Remove leading conversational/markdown prefix lines (e.g., "markdown", "commit", "commit:", "here is...")
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
        message = "\n".join(lines).strip()

        # Ensure Conventional Commit format on subject line (especially for local Ollama models)
        if format_type == "conventional" and message:
            msg_lines = message.splitlines()
            first_line = msg_lines[0].strip()
            
            # Conventional commit regex pattern: <type>(<scope>): <subject> or <type>: <subject>
            conv_pattern = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\([a-zA-Z0-9_\-/\.]+\))?!?: .+"
            if not re.match(conv_pattern, first_line):
                lower_first = first_line.lower()
                staged_files = status.get("staged", [])
                
                if any(f.endswith((".md", ".rst", ".txt")) for f in staged_files):
                    inferred_type = "docs"
                elif any("test" in f.lower() for f in staged_files):
                    inferred_type = "test"
                elif any(f.startswith((".github", "Dockerfile", "pyproject.toml")) for f in staged_files):
                    inferred_type = "build"
                elif any(k in lower_first for k in ("fix", "bug", "error", "repair", "resolve", "correct")):
                    inferred_type = "fix"
                elif any(k in lower_first for k in ("refactor", "clean", "simplify", "restructure", "optimize")):
                    inferred_type = "refactor"
                else:
                    inferred_type = "feat"
                
                # Un-capitalize first letter of subject
                subj = first_line[0].lower() + first_line[1:] if first_line else first_line
                msg_lines[0] = f"{inferred_type}: {subj}"
                message = "\n".join(msg_lines).strip()

        return message
