from typing import Optional, Tuple, List

class SafetyChecker:
    @staticmethod
    def _has_flag(parts: List[str], short_char: str, long_name: Optional[str] = None) -> bool:
        """Helper to check if a short flag character or long flag name exists in command parts."""
        for part in parts:
            if long_name and part == long_name:
                return True
            if part.startswith("-") and not part.startswith("--"):
                if short_char in part:
                    return True
        return False

    @classmethod
    def analyze_command(str_cls, command: str) -> Tuple[str, str, Optional[str]]:
        """
        Analyze a git command and return (risk_level, risk_explanation, safer_alternative).
        Risk levels: 'safe', 'moderate', 'destructive'
        """
        # Clean command
        cmd = command.strip()
        if cmd.startswith("git "):
            cmd = cmd[4:]
            
        parts = cmd.split()
        if not parts:
            return "safe", "No command specified.", None
            
        subcommand = parts[0]
        
        # 1. Hard reset
        if subcommand == "reset" and "--hard" in parts:
            return (
                "destructive",
                "This will permanently discard all uncommitted changes and revert your working tree and index to the target commit. Any uncommitted work will be LOST.",
                "git reset --soft"
            )
            
        # 2. Force push
        if subcommand == "push" and (str_cls._has_flag(parts, "f", "--force") or "--force-with-lease" in parts):
            is_lease = "--force-with-lease" in parts
            risk_desc = (
                "This will overwrite the remote branch history with your local history. "
                "If others have pushed to this branch, their commits will be lost."
            )
            alt = "git push" if is_lease else "git push --force-with-lease"
            return "destructive", risk_desc, alt
            
        # 3. Clean
        if subcommand == "clean" and str_cls._has_flag(parts, "f", "--force"):
            return (
                "destructive",
                "This will permanently delete untracked files and/or directories from your working directory. This cannot be undone.",
                "git clean -nd"  # dry-run
            )
            
        # 4. Force branch delete
        is_force_branch_delete = (
            subcommand == "branch" and 
            (str_cls._has_flag(parts, "D") or ("--delete" in parts and str_cls._has_flag(parts, "f", "--force")))
        )
        if is_force_branch_delete:
            return (
                "destructive",
                "This will force-delete a branch even if it contains commits that have not been merged into your current HEAD/upstream. Those commits could be lost.",
                "git branch -d"
            )

        # 5. Stash actions
        if subcommand == "stash":
            # git stash list, git stash show are safe
            safe_stash_subcommands = ["list", "show"]
            if len(parts) > 1 and parts[1] in safe_stash_subcommands:
                return "safe", "Read-only stash operation.", None
            # git stash pop, git stash apply, git stash drop, git stash clear are moderate
            return "moderate", "Modifies stash or working directory files.", None

        # 6. Branch listing vs deleting
        if subcommand == "branch":
            # git branch -d or git branch --delete are moderate
            if str_cls._has_flag(parts, "d", "--delete"):
                return "moderate", "Deletes a merged branch locally.", None
            # Default git branch or git branch -a is safe
            return "safe", "Read-only branch listing.", None
            
        # Moderate risk actions: writing/modifying local files/history
        moderate_commands = ["commit", "push", "merge", "checkout", "rebase", "cherry-pick", "reset", "revert"]
        if subcommand in moderate_commands:
            explanations = {
                "commit": "Creates a new commit with your staged changes.",
                "push": "Uploads your local commits to the remote repository.",
                "merge": "Merges changes from another branch into your current branch. May cause conflicts.",
                "checkout": "Switches branches or restores working tree files. Be careful as checkout of files can overwrite local modifications.",
                "rebase": "Reapplies commits on top of another base tip. Rewrites history locally.",
                "cherry-pick": "Applies the changes introduced by some existing commits.",
                "reset": "Resets current HEAD to the specified state.",
                "revert": "Creates a new commit that reverts the effects of earlier commits."
            }
            return "moderate", explanations.get(subcommand, "Modifies git state or files."), None
            
        # Safe actions: read-only/status queries
        return "safe", "Read-only or non-destructive operation.", None
