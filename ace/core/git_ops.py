import os
import git
from typing import List, Dict, Any, Optional

class NotAGitRepositoryError(Exception):
    """Raised when git operations are attempted outside a git repository."""
    pass

class GitOps:
    def __init__(self, repo_path: Optional[str] = None):
        path = repo_path or os.getcwd()
        try:
            self.repo = git.Repo(path, search_parent_directories=True)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            raise NotAGitRepositoryError("Not a git repository (or any of the parent directories)")

    @property
    def working_dir(self) -> str:
        return self.repo.working_dir

    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name. Returns None if HEAD is detached."""
        try:
            return self.repo.active_branch.name
        except TypeError:
            return None  # Detached HEAD

    def get_status(self) -> Dict[str, List[str]]:
        """Get staged, unstaged, and untracked files."""
        # Refresh index
        try:
            self.repo.index.update()
        except Exception:
            pass
        
        staged = []
        unstaged = []
        
        # Check if HEAD exists/is valid
        head_is_valid = False
        try:
            head_commit = self.repo.head.commit
            head_is_valid = True
        except Exception:
            head_is_valid = False
            
        if head_is_valid:
            # Staged files: diff between HEAD and index
            staged_diff = head_commit.diff()
            for diff in staged_diff:
                path = diff.b_path or diff.a_path
                if path:
                    staged.append(path)
        else:
            # Empty repo: any file in index is staged
            staged = [entry[0] for entry in self.repo.index.entries.keys()]
                
        # Unstaged files: diff between index and working copy
        unstaged_diff = self.repo.index.diff(None)
        for diff in unstaged_diff:
            path = diff.b_path or diff.a_path
            if path:
                unstaged.append(path)
                
        # Untracked files
        untracked = self.repo.untracked_files
        
        return {
            "staged": list(set(staged)),
            "unstaged": list(set(unstaged)),
            "untracked": untracked
        }

    def get_staged_diff(self) -> str:
        """Get the full diff of staged changes."""
        try:
            # Diff between HEAD and index
            return self.repo.git.diff("--staged")
        except git.GitCommandError:
            # Fallback if no commits exist
            try:
                # Diff index against an empty tree hash: 4b825dc642cb6eb9a0ff12e40d46a843d8110151
                return self.repo.git.diff("--cached", "4b825dc642cb6eb9a0ff12e40d46a843d8110151")
            except git.GitCommandError:
                return ""

    def get_branch_diff(self, base: str) -> str:
        """Get the diff between the current branch and a base branch/commit."""
        return self.repo.git.diff(f"{base}..HEAD")

    def get_log(self, n: int = 5, since: Optional[str] = None, author: Optional[str] = None, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get commit log details."""
        kwargs = {"max_count": n}
        if since:
            kwargs["since"] = since
        if author:
            kwargs["author"] = author
        
        args = []
        if path:
            args.append(path)
            
        try:
            commits = self.repo.iter_commits(*args, **kwargs)
            return [
                {
                    "hexsha": commit.hexsha,
                    "summary": commit.summary,
                    "message": commit.message,
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                }
                for commit in commits
            ]
        except (git.GitCommandError, ValueError):
            return []

    def get_branches(self, remote: bool = False) -> List[str]:
        """List local or remote branches."""
        if remote:
            return [b.name for b in self.repo.remotes.origin.refs] if "origin" in self.repo.remotes else []
        return [b.name for b in self.repo.branches]

    def get_conflicts(self) -> List[str]:
        """List files with merge conflicts."""
        conflicts = []
        unmerged_entries = self.repo.index.unmerged_entries()
        for path in unmerged_entries.keys():
            conflicts.append(path)
        return list(set(conflicts))

    def commit(self, message: str, sign: bool = False) -> str:
        """Commit staged changes."""
        args = []
        if sign:
            args.append("-S")
        return self.repo.git.commit(*args, m=message)

    def push(self, remote: str = "origin", branch: Optional[str] = None, force: bool = False, set_upstream: bool = False) -> str:
        """Push changes to remote."""
        args = []
        if force:
            args.append("--force")
        if set_upstream:
            args.append("-u")
            
        current_branch = branch or self.get_current_branch()
        if not current_branch:
            raise ValueError("No current branch to push")
            
        git_args = [remote, current_branch]
        return self.repo.git.push(*args, *git_args)

    def execute(self, command: str) -> str:
        """Run an arbitrary git command safely (the command string shouldn't include 'git ')."""
        # Split command into parts
        parts = command.strip().split()
        if parts and parts[0] == "git":
            parts = parts[1:]
        
        # Use git command runner directly
        git_func = getattr(self.repo.git, parts[0].replace("-", "_"))
        return git_func(*parts[1:])

    def get_upstream_tracking(self) -> Optional[str]:
        """Get the remote tracking branch of the current branch, e.g. 'origin/main'."""
        try:
            curr = self.repo.active_branch
            tracking = curr.tracking_branch()
            if tracking:
                return tracking.name
            return None
        except (TypeError, ValueError):
            return None

    def get_ahead_behind(self) -> Dict[str, int]:
        """Get the number of commits ahead and behind the remote tracking branch."""
        tracking = self.get_upstream_tracking()
        if not tracking:
            return {"ahead": 0, "behind": 0}
        
        try:
            # Count commits between HEAD and tracking branch
            ahead = sum(1 for _ in self.repo.iter_commits(f"{tracking}..HEAD"))
            behind = sum(1 for _ in self.repo.iter_commits(f"HEAD..{tracking}"))
            return {"ahead": ahead, "behind": behind}
        except git.GitCommandError:
            return {"ahead": 0, "behind": 0}

    def get_remotes(self) -> List[str]:
        """List all configured remote names."""
        return [r.name for r in self.repo.remotes]

