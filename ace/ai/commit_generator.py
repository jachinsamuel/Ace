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
        if not staged_diff.strip():
            # Sometimes status has staged but diff is empty (e.g. only file permissions or empty files)
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

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # Get LLM and run inference
        llm = get_llm(offline_override=offline)
        response = llm.invoke(messages)
        
        # Clean response (remove extra leading/trailing whitespace or markdown fences)
        message = response.content.strip()
        if message.startswith("```"):
            lines = message.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            message = "\n".join(lines).strip()
            
        return message
