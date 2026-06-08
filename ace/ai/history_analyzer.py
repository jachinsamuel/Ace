import collections
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from ace.core.git_ops import GitOps
from ace.ai.llm_factory import get_llm

HISTORY_SUMMARY_SYSTEM_PROMPT = """
You are "Ace", the AI Git Copilot.
The user asked a question about the repository's Git history, and we ran a Git command to fetch the raw data.
Your job is to analyze the raw Git output and summarize it for the user in a beautiful, helpful, and concise format.

User Query: "{query}"
Git Command Run: "{command}"

Analyze the Git output below and write the response. Use markdown, emojis, lists, or tables where helpful. Keep it concise.
""".strip()

class HistoryAnalyzer:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def summarize_query(self, query: str, command: str, command_output: str, offline: bool = False) -> str:
        """
        Summarize raw Git command output in response to a user's question.
        """
        if not command_output.strip():
            return "The Git command returned no output, meaning there is no matching history found."

        llm = get_llm(offline_override=offline)
        
        sys_prompt = HISTORY_SUMMARY_SYSTEM_PROMPT.format(query=query, command=command)
        user_prompt = f"Raw Git Output:\n\"\"\"\n{command_output[:20000]}\n\"\"\""

        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = llm.invoke(messages)
        return response.content.strip()

    def get_repo_stats(self) -> Dict[str, Any]:
        """
        Calculate repository statistics:
        - Total commits
        - Unique contributors
        - Most active authors
        - Recent commit frequency
        """
        try:
            # Get list of all commits (hash|author|date)
            log_data = self.git_ops.execute("log --format=%H|%an|%ad")
        except Exception:
            return {}

        commits = [line.split("|") for line in log_data.splitlines() if "|" in line]
        if not commits:
            return {}

        total_commits = len(commits)
        
        # Contributors count
        authors = [c[1] for c in commits]
        author_counts = collections.Counter(authors)
        contributors = list(author_counts.items())
        # Sort contributors by commit count descending
        contributors.sort(key=lambda x: x[1], reverse=True)

        # Active branches
        branches = self.git_ops.get_branches()

        # Files changed counts (approximate from diff-tree of recent commits)
        # We can run git status as well
        status = self.git_ops.get_status()

        return {
            "total_commits": total_commits,
            "total_branches": len(branches),
            "contributors": contributors,
            "staged_count": len(status["staged"]),
            "unstaged_count": len(status["unstaged"]),
            "untracked_count": len(status["untracked"]),
        }
