import collections
import os
import datetime
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

        from ace.utils.string_utils import strip_emojis
        response = llm.invoke(messages)
        return strip_emojis(response.content.strip())

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
        status = self.git_ops.get_status()

        # Lines of code changes per author
        try:
            numstat_data = self.git_ops.execute('log --numstat --format=AUTHOR:%an')
        except Exception:
            numstat_data = ""
        
        author_lines = {}
        current_author = None
        for line in numstat_data.splitlines():
            line = line.strip().replace('"', '')
            if not line:
                continue
            if line.startswith("AUTHOR:"):
                current_author = line[7:]
                if current_author not in author_lines:
                    author_lines[current_author] = {"added": 0, "deleted": 0}
            elif current_author:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        added = int(parts[0])
                        deleted = int(parts[1])
                        author_lines[current_author]["added"] += added
                        author_lines[current_author]["deleted"] += deleted
                    except ValueError:
                        pass

        # File type distribution (extensions)
        try:
            files_list = self.git_ops.execute("ls-files")
        except Exception:
            files_list = ""
            
        extensions = []
        for f in files_list.splitlines():
            f = f.strip()
            if not f:
                continue
            _, ext = os.path.splitext(f)
            if ext:
                extensions.append(ext.lower())
            else:
                extensions.append("(no extension)")
                
        extension_counts = collections.Counter(extensions)

        # Commit timeline (last 14 days)
        try:
            dates_data = self.git_ops.execute("log --format=%ad --date=short")
        except Exception:
            dates_data = ""
            
        date_counts = collections.Counter(dates_data.splitlines())
        today = datetime.date.today()
        last_14_days = [today - datetime.timedelta(days=i) for i in range(13, -1, -1)]
        
        timeline = []
        for d in last_14_days:
            date_str = d.isoformat()
            count = date_counts.get(date_str, 0)
            timeline.append((date_str, count))

        return {
            "total_commits": total_commits,
            "total_branches": len(branches),
            "contributors": contributors,
            "staged_count": len(status["staged"]),
            "unstaged_count": len(status["unstaged"]),
            "untracked_count": len(status["untracked"]),
            "lines_per_author": author_lines,
            "extension_counts": dict(extension_counts.most_common(5)),
            "timeline": timeline,
        }


    def semantic_search(self, query: str, limit: int = 50, offline: bool = False) -> Dict[str, Any]:
        """
        Retrieves the last `limit` commits, sends them to the LLM along with the search query,
        and returns the semantically matching commits.
        """
        commits = self.git_ops.get_log(n=limit)
        if not commits:
            return {"matches": []}

        history_lines = []
        for c in commits:
            history_lines.append(
                f"Commit: {c['hexsha']}\nAuthor: {c['author']}\nDate: {c['date']}\nSummary: {c['summary']}\nMessage: {c['message']}\n---"
            )
        commit_history_text = "\n".join(history_lines)

        from ace.ai.prompts.search import SEARCH_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
        from ace.utils.json_utils import extract_json

        llm = get_llm(offline_override=offline)
        
        if len(commit_history_text) > 25000:
            commit_history_text = commit_history_text[:25000] + "\n\n... (history truncated due to size) ..."

        usr_prompt = USER_PROMPT_TEMPLATE.format(
            query=query,
            commit_history=commit_history_text
        )

        messages = [
            SystemMessage(content=SEARCH_SYSTEM_PROMPT),
            HumanMessage(content=usr_prompt)
        ]

        response = llm.invoke(messages)
        return extract_json(response.content)

    def generate_standup(self, commits: list, offline: bool = False) -> str:
        """
        Analyze recent commits and generate a daily standup markdown report.
        """
        if not commits:
            return "No recent commits found to generate a standup from."

        commit_lines = []
        for c in commits:
            repo_prefix = f"[{c['repo_name']}] " if "repo_name" in c else ""
            commit_lines.append(f"- {repo_prefix}{c['hexsha'][:7]} - {c['summary']} (by {c['author']})")
        commit_list_text = "\n".join(commit_lines)

        from ace.ai.prompts.standup import STANDUP_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
        llm = get_llm(offline_override=offline)
        
        usr_prompt = USER_PROMPT_TEMPLATE.format(commit_list_text=commit_list_text)
        messages = [
            SystemMessage(content=STANDUP_SYSTEM_PROMPT),
            HumanMessage(content=usr_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content.strip()

    def analyze_blame(
        self,
        file: str,
        line: int,
        commit_info: dict,
        commit_show_output: str,
        line_content: str,
        offline: bool = False
    ) -> str:
        """
        Analyze why a specific line was written using LLM and commit patch info.
        """
        from ace.ai.prompts.blame import BLAME_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
        llm = get_llm(offline_override=offline)

        usr_prompt = USER_PROMPT_TEMPLATE.format(
            file=file,
            line=line,
            line_content=line_content,
            commit_hash=commit_info.get("hexsha", ""),
            author=commit_info.get("author", ""),
            date=commit_info.get("date", ""),
            summary=commit_info.get("summary", ""),
            message=commit_info.get("message", ""),
            patch=commit_show_output[:15000]
        )

        messages = [
            SystemMessage(content=BLAME_SYSTEM_PROMPT),
            HumanMessage(content=usr_prompt)
        ]

        response = llm.invoke(messages)
        return response.content.strip()

