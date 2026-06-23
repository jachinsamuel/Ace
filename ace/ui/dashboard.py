import click
import typer
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from ace.ui.display import console, spinner, show_warning_panel
from ace.core.git_ops import GitOps

def show_dashboard(git_ops: GitOps, offline: bool = False):
    """
    Renders an interactive terminal dashboard displaying repository state,
    workspace changes, and a menu to quickly run Ace operations.
    """
    from ace.ui.banner import animate_fire_banner, get_fire_banner_static
    
    # Play fire animation once on initial startup
    click.clear()
    try:
        animate_fire_banner(duration_seconds=1.2)
    except Exception:
        pass  # Fallback if animation fails
        
    while True:
        click.clear()
        
        # 1. Header
        console.print(get_fire_banner_static())
        console.print("[bold orange3]🚀 Ace AI Git Copilot Interactive Dashboard[/bold orange3]\n")

        
        # 2. Retrieve Status
        try:
            current_branch = git_ops.get_current_branch() or "Detached HEAD"
            tracking = git_ops.get_upstream_tracking() or "No remote tracking branch"
            ab = git_ops.get_ahead_behind()
            status = git_ops.get_status()
            
            # Get last 3 commits
            commits = git_ops.get_log(n=3)
        except Exception as e:
            console.print(f"[red]Error retrieving repository status: {e}[/red]")
            break
            
        # 3. Status Grid / Panel
        status_table = Table.grid(padding=1)
        status_table.add_column(style="bold cyan", justify="right")
        status_table.add_column()
        
        status_table.add_row("Branch:", current_branch)
        status_table.add_row("Tracking:", tracking)
        if ab["ahead"] or ab["behind"]:
            status_table.add_row("Sync Status:", f"[green]Ahead {ab['ahead']}[/green] / [red]Behind {ab['behind']}[/red] commits")
        else:
            status_table.add_row("Sync Status:", "Up to date with remote")
            
        status_panel = Panel(status_table, title="[bold]Repository Status[/bold]", border_style="blue", expand=False)
        
        # Changes Panel
        changes_table = Table.grid(padding=1)
        changes_table.add_column(style="bold yellow", justify="right")
        changes_table.add_column()
        
        changes_table.add_row("Staged:", f"{len(status['staged'])} files")
        changes_table.add_row("Unstaged:", f"{len(status['unstaged'])} files")
        changes_table.add_row("Untracked:", f"{len(status['untracked'])} files")
        
        changes_panel = Panel(changes_table, title="[bold]Workspace Changes[/bold]", border_style="yellow", expand=False)
        
        # Workspace sibling repositories detection
        parent_dir = Path(git_ops.working_dir).parent
        sibling_repos = []
        try:
            for p in parent_dir.iterdir():
                if p.is_dir() and p != Path(git_ops.working_dir):
                    if (p / ".git").exists():
                        sibling_repos.append(p.name)
        except Exception:
            pass

        sibling_panel = None
        if sibling_repos:
            sibling_table = Table.grid(padding=1)
            sibling_table.add_column(style="bold #B388FF")
            sibling_table.add_column(style="white")
            
            for idx, r_name in enumerate(sibling_repos[:4], 1):
                sib_branch = "unknown"
                try:
                    import git
                    s_repo = git.Repo(parent_dir / r_name)
                    sib_branch = s_repo.active_branch.name
                except Exception:
                    pass
                sibling_table.add_row(f"  📂 {r_name} ", f" ({sib_branch})")
                
            if len(sibling_repos) > 4:
                sibling_table.add_row("  ... ", f" ({len(sibling_repos) - 4} more)")
                
            sibling_panel = Panel(sibling_table, title="[bold]Workspace Repos[/bold]", border_style="#B388FF", expand=False)

        panels = [status_panel, changes_panel]
        if sibling_panel:
            panels.append(sibling_panel)
            
        console.print(Columns(panels))
        
        # 4. Detailed changes (if any)
        if status["staged"]:
            t = Table(title="Staged Files (to be committed)", show_header=False, box=None)
            for f in status["staged"]:
                t.add_row(f"[green]  staged: {f}[/green]")
            console.print(t)
            
        if status["unstaged"]:
            t = Table(title="Unstaged Changes", show_header=False, box=None)
            for f in status["unstaged"]:
                t.add_row(f"[red]  modified: {f}[/red]")
            console.print(t)
            
        if status["untracked"]:
            t = Table(title="Untracked Files", show_header=False, box=None)
            for f in status["untracked"]:
                t.add_row(f"[dim]  untracked: {f}[/dim]")
            console.print(t)
            
        # 5. Recent Commits Panel
        if commits:
            commit_table = Table(show_header=True, header_style="bold green", box=None)
            commit_table.add_column("Hash", style="dim", width=8)
            commit_table.add_column("Message")
            commit_table.add_column("Author", style="cyan")
            for c in commits:
                commit_table.add_row(c["hexsha"][:7], c["summary"], c["author"])
            console.print(Panel(commit_table, title="[bold]Recent Commits[/bold]", border_style="dim"))
        else:
            console.print("[dim]No commit history yet.[/dim]")
            
        menu_table = Table(show_header=False, box=None, padding=(0, 2))
        menu_table.add_column(style="bold cyan", justify="right")
        menu_table.add_column(style="white")
        menu_table.add_column(style="bold cyan", justify="right")
        menu_table.add_column(style="white")
        
        menu_table.add_row("\[c]", "AI Commit", "\[r]", "AI Code Review")
        menu_table.add_row("\[u]", "AI Smart Undo", "\[p]", "Plan Git Command (AI)")
        menu_table.add_row("\[s]", "Repo Stats", "\[w]", "Switch Repo")
        menu_table.add_row("\[q]", "Quit Dashboard", "", "")
        
        console.print(Panel(menu_table, title="[bold white]Available Actions[/bold white]", border_style="orange3", expand=False))
        console.print()
        
        # Get user input using instant single keypress
        console.print("[bold orange3]Press a key to select action...[/bold orange3] ", end="")
        while True:
            choice = click.getchar().lower().strip()
            if choice == "\r" or choice == "\n" or not choice:
                choice = "q"
                break
            if choice in ("c", "r", "u", "p", "s", "w", "q"):
                break
        console.print(choice)
        console.print()
        
        if choice == "q":
            console.print("[yellow]Exiting dashboard.[/yellow]")
            break
        elif choice == "c":
            # Run commit command from cli
            from ace.cli import commit_cmd
            try:
                commit_cmd(offline=offline)
            except Exception as e:
                console.print(f"[red]Error running commit: {e}[/red]")
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            click.getchar()
        elif choice == "r":
            # Run review command from cli
            from ace.cli import review_cmd
            try:
                review_cmd(all_changes=True, offline=offline)
            except Exception as e:
                console.print(f"[red]Error running code review: {e}[/red]")
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            click.getchar()
        elif choice == "u":
            # Run undo command from cli
            from ace.cli import undo_cmd
            try:
                undo_cmd(offline=offline)
            except Exception as e:
                console.print(f"[red]Error running undo: {e}[/red]")
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            click.getchar()
        elif choice == "s":
            # Run stats command from cli
            from ace.cli import stats_cmd
            try:
                stats_cmd()
            except Exception as e:
                console.print(f"[red]Error running stats: {e}[/red]")
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            click.getchar()
        elif choice == "w":
            # Switch repository
            from ace.ui.prompts import prompt_select
            sibling_repos_all = []
            try:
                for p in parent_dir.iterdir():
                    if p.is_dir() and (p / ".git").exists():
                        sibling_repos_all.append(p.name)
            except Exception:
                pass
            sibling_repos_all.sort()
            
            if not sibling_repos_all:
                console.print("[yellow]No other repositories found in the parent directory.[/yellow]")
            else:
                console.print("[bold]Available repositories in workspace:[/bold]")
                current_name = Path(git_ops.working_dir).name
                display_options = []
                for name in sibling_repos_all:
                    if name == current_name:
                        display_options.append(f"{name} [bold green](current)[/bold green]")
                    else:
                        display_options.append(name)
                
                sel_idx = prompt_select(display_options, prompt_text="Enter repository number to switch to", default="s")
                if sel_idx >= 0:
                    selected_repo_name = sibling_repos_all[sel_idx]
                    new_path = parent_dir / selected_repo_name
                    try:
                        from ace.core.git_ops import GitOps as NewGitOps
                        git_ops = NewGitOps(str(new_path))
                        console.print(f"[green]Switched workspace to repository: [bold]{selected_repo_name}[/bold][/green]")
                    except Exception as e:
                        console.print(f"[red]Failed to switch repository: {e}[/red]")
                else:
                    console.print("[yellow]Switch cancelled.[/yellow]")
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            click.getchar()
        elif choice == "p":
            query = typer.prompt("What do you want to do with Git? (e.g. 'undo my last commit')")
            if query.strip():
                from ace.ai.intent_parser import IntentParser
                from ace.core.safety import SafetyChecker
                from ace.ui.display import show_plan
                from ace.ui.prompts import confirm as ui_confirm
                
                console.print(f"🧠 Understanding request: [italic]\"{query}\"[/italic]...")
                parser = IntentParser(git_ops)
                try:
                    with spinner("Planning Git commands..."):
                        parsed = parser.parse_intent(query, offline=offline)
                    commands = parsed.get("commands", [])
                    explanation = parsed.get("explanation", "")
                    
                    if not commands:
                        console.print(f"[yellow]No commands planned. Explanation:[/yellow] {explanation}")
                    else:
                        show_plan(commands, [explanation] + [""] * (len(commands) - 1))
                        
                        # Safety checks
                        highest_risk = "safe"
                        risk_details = []
                        for cmd in commands:
                            r_level, r_desc, _ = SafetyChecker.analyze_command(cmd)
                            if r_level == "destructive":
                                highest_risk = "destructive"
                                risk_details.append(f"Command: {cmd}\nRisk: {r_desc}")
                            elif r_level == "moderate" and highest_risk != "destructive":
                                highest_risk = "moderate"
                                
                        execute_plan = True
                        if highest_risk == "destructive":
                            show_warning_panel("\n\n".join(risk_details), "⚠️ DESTRUCTIVE OPERATION DETECTED")
                            execute_plan = ui_confirm("Are you sure you want to execute these destructive commands?", default=False)
                        elif highest_risk == "moderate":
                            execute_plan = ui_confirm("Do you want to execute this plan?", default=True)
                            
                        if execute_plan:
                            for cmd in commands:
                                console.print(f"Executing: [bold]{cmd}[/bold]")
                                git_args = cmd[4:] if cmd.startswith("git ") else cmd
                                res = git_ops.execute(git_args)
                                if res.strip():
                                    console.print(res)
                            console.print("[green]Plan executed successfully![/green]")
                        else:
                            console.print("[yellow]Plan aborted.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error planning commands: {e}[/red]")
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            click.getchar()
