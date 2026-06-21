import os
import stat
from pathlib import Path
from ace.core.git_ops import GitOps

class GitHooksManager:
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops
        self.hooks_dir = Path(git_ops.working_dir) / ".git" / "hooks"

    def install_pre_commit(self) -> str:
        """Install pre-commit hook that runs code review."""
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = self.hooks_dir / "pre-commit"
        
        content = """#!/bin/sh
echo "🧠 Running Ace pre-commit code review..."
python -m ace review --strict
if [ $? -ne 0 ]; then
  echo "❌ Ace Code Review detected critical issues. Commit aborted."
  exit 1
fi
"""
        hook_path.write_text(content, encoding="utf-8")
        
        # Make executable
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return str(hook_path)

    def install_prepare_commit_msg(self) -> str:
        """Install prepare-commit-msg hook that populates AI commit message."""
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = self.hooks_dir / "prepare-commit-msg"
        
        content = """#!/bin/sh
# Do not generate if commit message is already provided (e.g. git commit -m)
if [ -z "$2" ]; then
  echo "🧠 Ace is drafting commit message..."
  python -m ace commit --prepare "$1"
fi
"""
        hook_path.write_text(content, encoding="utf-8")
        
        # Make executable
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return str(hook_path)

    def uninstall_all(self) -> None:
        """Remove installed Ace hooks."""
        for hook_name in ["pre-commit", "prepare-commit-msg"]:
            hook_path = self.hooks_dir / hook_name
            if hook_path.exists():
                try:
                    content = hook_path.read_text(encoding="utf-8")
                    if "Ace" in content:
                        hook_path.unlink()
                except Exception:
                    pass
