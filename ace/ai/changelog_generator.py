from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.ai.llm_factory import get_llm
from ace.ai.prompts.changelog import CHANGELOG_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

class ChangelogGeneratorError(Exception):
    """Raised when changelog generation fails."""
    pass

class ChangelogGenerator:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def get_commits_in_range(self, from_ref: Optional[str] = None, to_ref: Optional[str] = None) -> str:
        """
        Retrieve formatted commit log between from_ref and to_ref.
        If from_ref is None, attempts to find the latest tag.
        If no latest tag exists, falls back to the last 30 commits.
        """
        if from_ref:
            try:
                self.git_ops.execute(f"rev-parse --verify {from_ref}")
            except Exception:
                raise ChangelogGeneratorError(f"Invalid starting revision: {from_ref}")

        if to_ref:
            try:
                self.git_ops.execute(f"rev-parse --verify {to_ref}")
            except Exception:
                raise ChangelogGeneratorError(f"Invalid ending revision: {to_ref}")

        # Check if HEAD exists first
        try:
            self.git_ops.execute("rev-parse --verify HEAD")
        except Exception:
            return ""

        to_revision = to_ref or "HEAD"
        from_revision = from_ref
        
        # If from_ref is not provided, try to find the latest tag
        if not from_revision:
            try:
                # git describe --tags --abbrev=0 to get latest tag
                latest_tag = self.git_ops.execute("describe --tags --abbrev=0").strip()
                from_revision = latest_tag
            except Exception:
                # No tags found
                from_revision = None

        log_args = ["log"]
        if from_revision:
            log_args.append(f"{from_revision}..{to_revision}")
        else:
            # Fallback to last 30 commits
            log_args.extend(["-n", "30"])

        # Format: hash|date|author|subject\nbody
        log_args.append('--format=%H|%ad|%an|%s%n%b')
        
        try:
            cmd = " ".join(log_args)
            return self.git_ops.execute(cmd).strip()
        except Exception as e:
            raise ChangelogGeneratorError(f"Failed to fetch commit log: {e}")

    def generate_changelog(self, from_ref: Optional[str] = None, to_ref: Optional[str] = None, offline: bool = False) -> str:
        """
        Retrieve commits and generate a release changelog in Markdown.
        """
        commit_log = self.get_commits_in_range(from_ref, to_ref)
        if not commit_log.strip():
            return "No commits found in the specified range."

        llm = get_llm(offline_override=offline)
        
        user_prompt = USER_PROMPT_TEMPLATE.format(
            commit_log=commit_log[:20000] # Cap log length to respect context window
        )

        messages = [
            SystemMessage(content=CHANGELOG_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        response = llm.invoke(messages)
        return response.content.strip()
