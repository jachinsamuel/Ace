from pathlib import Path
from typing import Dict, Any, List
from ace.core.git_ops import GitOps

class RepoContext:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def detect_project_type(self) -> List[str]:
        """Detect active programming languages and frameworks in the repository."""
        working_dir = Path(self.git_ops.working_dir)
        types = []

        # File presence detection
        indicators = {
            "package.json": "JavaScript/Node.js",
            "tsconfig.json": "TypeScript",
            "pyproject.toml": "Python (Hatch/Poetry/Pipenv)",
            "requirements.txt": "Python",
            "setup.py": "Python",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "pom.xml": "Java (Maven)",
            "build.gradle": "Java/Kotlin (Gradle)",
            "Gemfile": "Ruby",
            "Composer.json": "PHP",
            "Makefile": "C/C++ or Makefile based build",
            "CMakeLists.txt": "C/C++ (CMake)",
            "docker-compose.yml": "Docker Compose",
            "Dockerfile": "Docker",
        }

        for file, lang in indicators.items():
            if (working_dir / file).exists():
                types.append(lang)

        # Extension detection in root
        extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".sh": "Shell Script",
            ".ps1": "PowerShell",
        }

        root_files = [f for f in working_dir.iterdir() if f.is_file()]
        for file in root_files:
            ext = file.suffix
            if ext in extensions and extensions[ext] not in types:
                types.append(extensions[ext])

        if not types:
            types.append("Unknown/Text")
            
        return types

    def check_merge_rebase_state(self) -> Dict[str, Any]:
        """Check if the repository is currently in a merge, rebase, or cherry-pick state."""
        git_dir = Path(self.git_ops.working_dir) / ".git"
        state = {
            "in_progress": False,
            "type": None,  # 'merge', 'rebase', 'cherry-pick', 'revert'
            "detail": ""
        }

        if not git_dir.exists():
            return state

        if (git_dir / "MERGE_HEAD").exists():
            state["in_progress"] = True
            state["type"] = "merge"
            state["detail"] = "Merge conflict/resolution in progress."
        elif (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
            state["in_progress"] = True
            state["type"] = "rebase"
            state["detail"] = "Rebase operation in progress."
        elif (git_dir / "CHERRY_PICK_HEAD").exists():
            state["in_progress"] = True
            state["type"] = "cherry-pick"
            state["detail"] = "Cherry-pick operation in progress."
        elif (git_dir / "REVERT_HEAD").exists():
            state["in_progress"] = True
            state["type"] = "revert"
            state["detail"] = "Revert operation in progress."

        return state

    def get_commit_conventions(self) -> str:
        """Attempt to read contributing files or commit message templates to find conventions."""
        working_dir = Path(self.git_ops.working_dir)
        conventions = []

        files_to_check = [
            "CONTRIBUTING.md",
            "CONTRIBUTING",
            ".github/CONTRIBUTING.md",
            ".gitmessage",
        ]

        for file_name in files_to_check:
            path = working_dir / file_name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    if "conventional commit" in content.lower() or "semantic commit" in content.lower():
                        conventions.append("Conventional Commits format is preferred.")
                    if "gpg" in content.lower() or "signing" in content.lower():
                        conventions.append("Signed commits are preferred.")
                except Exception:
                    pass

        return " ".join(conventions) if conventions else "No specific commit conventions detected."

    def build_context(self) -> Dict[str, Any]:
        """Compile a dictionary representation of repository context."""
        status = self.git_ops.get_status()
        recent_commits = self.git_ops.get_log(n=5)
        current_branch = self.git_ops.get_current_branch()
        upstream = self.git_ops.get_upstream_tracking()
        ab = self.git_ops.get_ahead_behind()
        project_types = self.detect_project_type()
        state = self.check_merge_rebase_state()
        conventions = self.get_commit_conventions()

        return {
            "current_branch": current_branch or "Detached HEAD",
            "upstream_branch": upstream or "None",
            "ahead_commits": ab.get("ahead", 0),
            "behind_commits": ab.get("behind", 0),
            "project_types": project_types,
            "git_state": state,
            "commit_conventions": conventions,
            "staged_files": status.get("staged", []),
            "unstaged_files": status.get("unstaged", []),
            "untracked_files": status.get("untracked", []),
            "recent_commits": recent_commits
        }

    def format_context_for_prompt(self) -> str:
        """Format repository context into a descriptive text block for LLMs."""
        ctx = self.build_context()
        
        commits_str = ""
        for i, commit in enumerate(ctx["recent_commits"]):
            commits_str += f"  - {commit['hexsha'][:8]} by {commit['author']}: {commit['summary']}\n"
            
        staged_files = ", ".join(ctx["staged_files"]) or "None"
        unstaged_files = ", ".join(ctx["unstaged_files"]) or "None"
        untracked_files = ", ".join(ctx["untracked_files"]) or "None"
        
        git_state_desc = "Normal"
        if ctx["git_state"]["in_progress"]:
            git_state_desc = f"{ctx['git_state']['type'].upper()} ({ctx['git_state']['detail']})"
            
        return f"""
Repository Context:
- Current branch: {ctx['current_branch']} (Tracking: {ctx['upstream_branch']})
- Sync status: Ahead by {ctx['ahead_commits']} commits, Behind by {ctx['behind_commits']} commits.
- Project technology/types: {', '.join(ctx['project_types'])}
- Git operation state: {git_state_desc}
- Commit conventions: {ctx['commit_conventions']}
- Staged files: {staged_files}
- Unstaged changes: {unstaged_files}
- Untracked files: {untracked_files}
- Recent history:
{commits_str if commits_str else '  - No commits yet'}
""".strip()
