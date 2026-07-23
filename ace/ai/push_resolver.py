from typing import Dict, Any, List, Optional
from rich.panel import Panel
from rich.text import Text
from rich import box
import typer

from ace.core.git_ops import GitOps
from ace.ui.display import console, spinner, print_success, print_warning, show_error_panel

def categorize_push_error(error_msg: str) -> Dict[str, Any]:
    """Categorize git push error into actionable problem types and remedies."""
    err_lower = error_msg.lower()
    
    if any(pattern in err_lower for pattern in ["fetch first", "non-fast-forward", "behind", "rejected", "updates were rejected because the remote contains work"]):
        return {
            "type": "non_fast_forward",
            "title": "Remote Branch Has New Commits (Non-Fast-Forward)",
            "description": "The remote branch contains commits that you do not have locally. You must pull remote changes before pushing.",
            "actions": [
                {"key": "1", "label": "Pull & Rebase remote changes (git pull --rebase)", "cmd": "pull_rebase"},
                {"key": "2", "label": "Pull & Merge remote changes (git pull)", "cmd": "pull_merge"},
                {"key": "3", "label": "Force push safely with lease (git push --force-with-lease)", "cmd": "force_lease"},
            ]
        }
    elif any(pattern in err_lower for pattern in ["no upstream", "has no upstream", "set-upstream"]):
        return {
            "type": "no_upstream",
            "title": "Missing Upstream Tracking Branch",
            "description": "Your local branch does not have an upstream tracking branch on the remote.",
            "actions": [
                {"key": "1", "label": "Set upstream and push (git push -u)", "cmd": "set_upstream"},
            ]
        }
    elif any(pattern in err_lower for pattern in ["permission denied", "authentication failed", "could not read from remote", "publickey"]):
        return {
            "type": "permission_denied",
            "title": "Authentication / Access Permission Denied",
            "description": "Git could not authenticate with the remote repository. Check your SSH keys or HTTPS access token.",
            "actions": [
                {"key": "1", "label": "Show SSH / Token troubleshooting guide", "cmd": "help_auth"},
            ]
        }
    else:
        return {
            "type": "unknown",
            "title": "Git Push Error",
            "description": error_msg.strip()[:200],
            "actions": [
                {"key": "1", "label": "Pull & Rebase remote changes (git pull --rebase)", "cmd": "pull_rebase"},
                {"key": "2", "label": "Force push safely with lease (git push --force-with-lease)", "cmd": "force_lease"},
            ]
        }

def handle_push_failure(git_ops: GitOps, error_msg: str, remote: str = "origin", branch: Optional[str] = None, offline: bool = False) -> bool:
    """
    Interactively diagnose a git push failure and prompt the user with recovery options.
    Returns True if the push was resolved successfully, False otherwise.
    """
    curr_branch = branch or git_ops.get_current_branch() or "master"
    category = categorize_push_error(error_msg)
    
    console.print()
    diag_text = Text()
    diag_text.append(f"Problem: {category['description']}\n", style="white")
    diag_text.append(f"Target Branch: {remote}/{curr_branch}\n", style="dim #9E9E9E")
    
    console.print(Panel(
        diag_text,
        title=f"[bold #FF1744]✘ {category['title']}[/bold #FF1744]",
        border_style="#FF1744",
        padding=(1, 2)
    ))
    
    console.print("[bold cyan]Choose resolution action:[/bold cyan]")
    for act in category["actions"]:
        console.print(f"  [{act['key']}] {act['label']}")
    console.print("  [s] Skip / Cancel push")
    
    choice = typer.prompt("Select option", default="1").lower().strip()
    
    if choice == "s":
        print_warning("Push resolution cancelled.")
        return False
        
    selected_act = None
    for act in category["actions"]:
        if act["key"] == choice:
            selected_act = act
            break
            
    if not selected_act and category["actions"]:
        selected_act = category["actions"][0]
        
    if not selected_act:
        return False

    cmd_type = selected_act["cmd"]

    if cmd_type == "pull_rebase":
        try:
            with spinner(f"Pulling and rebasing from {remote}/{curr_branch}..."):
                git_ops.execute(f"pull --rebase {remote} {curr_branch}")
            print_success("Successfully pulled and rebased remote changes!")
            
            # Retry push
            with spinner(f"Retrying push to {remote}/{curr_branch}..."):
                push_res = git_ops.push(remote=remote, branch=curr_branch)
            print_success("Pushed to remote successfully!")
            if push_res.strip():
                console.print(f"[dim]{push_res}[/dim]")
            return True
        except Exception as e:
            show_error_panel(f"Failed during pull & rebase or retry push: {e}", "Resolution Error")
            return False

    elif cmd_type == "pull_merge":
        try:
            with spinner(f"Pulling and merging from {remote}/{curr_branch}..."):
                git_ops.execute(f"pull {remote} {curr_branch}")
            print_success("Successfully merged remote changes!")
            
            # Retry push
            with spinner(f"Retrying push to {remote}/{curr_branch}..."):
                push_res = git_ops.push(remote=remote, branch=curr_branch)
            print_success("Pushed to remote successfully!")
            if push_res.strip():
                console.print(f"[dim]{push_res}[/dim]")
            return True
        except Exception as e:
            show_error_panel(f"Failed during pull or retry push: {e}", "Resolution Error")
            return False

    elif cmd_type == "force_lease":
        from ace.ui.prompts import confirm
        if confirm("Force push with lease will overwrite remote commits if your local branch is out of sync. Continue?", default=False):
            try:
                with spinner(f"Force pushing (--force-with-lease) to {remote}/{curr_branch}..."):
                    push_res = git_ops.execute(f"push --force-with-lease {remote} {curr_branch}")
                print_success("Force pushed with lease successfully!")
                if push_res.strip():
                    console.print(f"[dim]{push_res}[/dim]")
                return True
            except Exception as e:
                show_error_panel(f"Force push failed: {e}", "Resolution Error")
                return False
        else:
            print_warning("Force push cancelled.")
            return False

    elif cmd_type == "set_upstream":
        try:
            with spinner(f"Setting upstream and pushing to {remote}/{curr_branch}..."):
                push_res = git_ops.push(remote=remote, branch=curr_branch, set_upstream=True)
            print_success("Set upstream and pushed successfully!")
            if push_res.strip():
                console.print(f"[dim]{push_res}[/dim]")
            return True
        except Exception as e:
            show_error_panel(f"Push with set-upstream failed: {e}", "Resolution Error")
            return False

    elif cmd_type == "help_auth":
        auth_guide = (
            "Authentication Troubleshooting Guide:\n"
            "1. SSH Key setup: Run 'ssh -T git@github.com' to verify key access.\n"
            "2. HTTPS Token: Run 'git config --global credential.helper manager' to update saved passwords/tokens.\n"
            "3. Remote URL: Verify remote URL with 'git remote -v'."
        )
        console.print(Panel(auth_guide, title="[bold cyan]Authentication Help[/bold cyan]", border_style="#00D5FF"))
        return False

    return False
