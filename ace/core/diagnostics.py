from pathlib import Path
from typing import Dict, Any, List
from ace.core.git_ops import GitOps

class GitDiagnostics:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops

    def check_locks(self) -> List[str]:
        """Check for active git lock files that might block operations."""
        git_dir = Path(self.git_ops.working_dir) / ".git"
        locks = []
        if not git_dir.exists():
            return locks
            
        index_lock = git_dir / "index.lock"
        if index_lock.exists():
            locks.append(str(index_lock))
            
        # Check refs locks
        refs_dir = git_dir / "refs"
        if refs_dir.exists():
            for p in refs_dir.rglob("*.lock"):
                locks.append(str(p))
                
        return locks

    def check_large_files(self, threshold_mb: float = 50.0) -> List[Dict[str, Any]]:
        """Identify untracked files exceeding the size threshold."""
        status = self.git_ops.get_status()
        untracked = status.get("untracked", [])
        large_files = []
        
        for file_rel in untracked:
            file_path = Path(self.git_ops.working_dir) / file_rel
            if file_path.exists() and file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb >= threshold_mb:
                    large_files.append({
                        "path": file_rel,
                        "size_mb": round(size_mb, 2)
                    })
        return large_files

    def run_diagnostics(self) -> Dict[str, Any]:
        """Aggregate all repository health checks."""
        locks = self.check_locks()
        large_files = self.check_large_files()
        
        # Branch status
        current_branch = self.git_ops.get_current_branch()
        tracking = self.git_ops.get_upstream_tracking()
        ab = self.git_ops.get_ahead_behind()
        
        # Operation state
        from ace.core.context import RepoContext
        ctx = RepoContext(self.git_ops)
        op_state = ctx.check_merge_rebase_state()
        
        # Workspace status
        status = self.git_ops.get_status()
        
        return {
            "has_issues": bool(locks or large_files or op_state["in_progress"] or not current_branch),
            "locks": locks,
            "large_files": large_files,
            "detached_head": current_branch is None,
            "operation_state": op_state,
            "sync_status": {
                "branch": current_branch or "Detached HEAD",
                "tracking": tracking or "None",
                "ahead": ab["ahead"],
                "behind": ab["behind"]
            },
            "dirty_files": {
                "staged": len(status["staged"]),
                "unstaged": len(status["unstaged"]),
                "untracked": len(status["untracked"])
            }
        }
