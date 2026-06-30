import click
import typer
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box
from ace.ui.display import console, spinner, show_warning_panel, print_success, print_warning
from ace.core.git_ops import GitOps


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _branch_label(branch: str) -> Text:
    """Render the current branch name with a small indicator."""
    return Text.assemble(("  ", ""), (branch, "bold #00E676"))


def _sync_label(ahead: int, behind: int) -> Text:
    if not ahead and not behind:
        return Text("Up to date", style="#00E676")
    parts: list = []
    if ahead:
        parts.append((f"+{ahead} ahead", "bold #00E676"))
    if ahead and behind:
        parts.append(("  /  ", "dim #555555"))
    if behind:
        parts.append((f"-{behind} behind", "bold #FF1744"))
    return Text.assemble(*parts)


def _file_count_label(n: int, colour: str) -> Text:
    if n == 0:
        return Text("none", style="dim #666666")
    return Text(str(n), style=f"bold {colour}")


# ─── Dashboard entry point ───────────────────────────────────────────────────

def show_dashboard(git_ops: GitOps, offline: bool = False):
    """
    Renders an interactive terminal dashboard displaying repository state,
    workspace changes, and a menu to quickly run Ace operations.
    """
    from ace.ui.banner import animate_fire_banner, get_fire_banner_static

    click.clear()
    try:
        animate_fire_banner(duration_seconds=1.2)
    except Exception:
        pass

    while True:
        click.clear()

        # ── Header ──────────────────────────────────────────────────────────
        console.print(get_fire_banner_static())
        console.print(
            Text.assemble(
                ("  Ace", "bold #FF6D00"),
                ("  AI Git Copilot", "bold white"),
                ("  ·  Interactive Dashboard", "dim #9E9E9E"),
            )
        )
        console.print()

        # ── Fetch repo state ────────────────────────────────────────────────
        try:
            current_branch = git_ops.get_current_branch() or "Detached HEAD"
            tracking       = git_ops.get_upstream_tracking() or "No remote tracking"
            ab             = git_ops.get_ahead_behind()
            status         = git_ops.get_status()
            commits        = git_ops.get_log(n=5)
        except Exception as e:
            console.print(f"[error]Failed to read repository: {e}[/error]")
            break

        # ── Status panel ────────────────────────────────────────────────────
        st = Table.grid(padding=(0, 2))
        st.add_column(style="label",  justify="right", min_width=12)
        st.add_column()
        st.add_row("Branch",   _branch_label(current_branch))
        st.add_row("Remote",   Text(tracking,  style="#9E9E9E"))
        st.add_row("Sync",     _sync_label(ab["ahead"], ab["behind"]))
        status_panel = Panel(
            st,
            title="[bold white]Repository[/bold white]",
            border_style="#00D5FF",
            box=box.ROUNDED,
            expand=False,
            padding=(0, 1),
        )

        # ── Changes panel ───────────────────────────────────────────────────
        ct = Table.grid(padding=(0, 2))
        ct.add_column(style="label", justify="right", min_width=12)
        ct.add_column()
        ct.add_row("Staged",    _file_count_label(len(status["staged"]),    "#00E676"))
        ct.add_row("Unstaged",  _file_count_label(len(status["unstaged"]),  "#FFD600"))
        ct.add_row("Untracked", _file_count_label(len(status["untracked"]), "#9E9E9E"))
        changes_panel = Panel(
            ct,
            title="[bold white]Workspace[/bold white]",
            border_style="#FFD600",
            box=box.ROUNDED,
            expand=False,
            padding=(0, 1),
        )

        # ── Sibling repos panel ─────────────────────────────────────────────
        parent_dir    = Path(git_ops.working_dir).parent
        sibling_repos: list[str] = []
        try:
            for p in parent_dir.iterdir():
                if p.is_dir() and p != Path(git_ops.working_dir) and (p / ".git").exists():
                    sibling_repos.append(p.name)
        except Exception:
            pass

        sibling_panel = None
        if sibling_repos:
            rt = Table.grid(padding=(0, 2))
            rt.add_column(style="bold #B388FF", min_width=14)
            rt.add_column(style="dim #9E9E9E")
            for r_name in sibling_repos[:5]:
                sib_branch = "?"
                try:
                    import git as _git
                    sib_branch = _git.Repo(parent_dir / r_name).active_branch.name
                except Exception:
                    pass
                rt.add_row(r_name, sib_branch)
            if len(sibling_repos) > 5:
                rt.add_row(f"  +{len(sibling_repos) - 5} more", "")
            sibling_panel = Panel(
                rt,
                title="[bold white]Workspace Repos[/bold white]",
                border_style="#B388FF",
                box=box.ROUNDED,
                expand=False,
                padding=(0, 1),
            )

        panels = [status_panel, changes_panel]
        if sibling_panel:
            panels.append(sibling_panel)
        console.print(Columns(panels))
        console.print()

        # ── Staged / Unstaged file lists ────────────────────────────────────
        if status["staged"]:
            t = Table(show_header=False, box=None, padding=(0, 2))
            t.add_column()
            for f in status["staged"]:
                t.add_row(Text.assemble(("+ ", "bold #00E676"), (f, "#BDBDBD")))
            console.print(Panel(t, title="[bold #00E676]Staged[/bold #00E676]",
                                border_style="#00E676", box=box.SIMPLE, expand=False))
            console.print()

        if status["unstaged"]:
            t = Table(show_header=False, box=None, padding=(0, 2))
            t.add_column()
            for f in status["unstaged"]:
                t.add_row(Text.assemble(("~ ", "bold #FFD600"), (f, "#BDBDBD")))
            console.print(Panel(t, title="[bold #FFD600]Unstaged[/bold #FFD600]",
                                border_style="#FFD600", box=box.SIMPLE, expand=False))
            console.print()

        if status["untracked"]:
            t = Table(show_header=False, box=None, padding=(0, 2))
            t.add_column()
            for f in status["untracked"]:
                t.add_row(Text.assemble(("? ", "dim #9E9E9E"), (f, "dim #9E9E9E")))
            console.print(Panel(t, title="[dim]Untracked[/dim]",
                                border_style="#555555", box=box.SIMPLE, expand=False))
            console.print()

        # ── Recent commits ──────────────────────────────────────────────────
        if commits:
            commit_table = Table(
                show_header=True,
                header_style="bold #9E9E9E",
                box=box.SIMPLE_HEAD,
                show_edge=False,
                padding=(0, 2),
            )
            commit_table.add_column("Hash",    style="#666666",   width=8,  no_wrap=True)
            commit_table.add_column("Message", style="white",     ratio=4)
            commit_table.add_column("Author",  style="#B388FF",   ratio=2)
            for c in commits:
                commit_table.add_row(c["hexsha"][:7], c["summary"], c["author"])
            console.print(
                Panel(commit_table, title="[bold white]Recent Commits[/bold white]",
                      border_style="#444444", box=box.ROUNDED, expand=False)
            )
        else:
            console.print("[dim]  No commit history yet.[/dim]")
        console.print()

        # ── Action menu ─────────────────────────────────────────────────────
        menu = Table(show_header=False, box=None, padding=(0, 4), expand=False)
        menu.add_column(min_width=22)
        menu.add_column(min_width=22)


        def _row(key: str, label: str) -> Text:
            return Text.assemble((f"[{key}]", "bold #00D5FF"), (f"  {label}", "#BDBDBD"))

        menu.add_row(_row("c", "AI Commit"),    _row("r", "AI Code Review"))
        menu.add_row(_row("u", "Smart Undo"),   _row("p", "Plan Command (AI)"))
        menu.add_row(_row("s", "Repo Stats"),   _row("w", "Switch Repo"))
        menu.add_row(_row("q", "Quit"),         Text(""))

        console.print(
            Panel(menu, title="[bold white]Actions[/bold white]",
                  border_style="#FF6D00", box=box.ROUNDED, expand=False)
        )
        console.print()
        console.print("[bold #FF6D00]  Press a key ...[/bold #FF6D00]  ", end="")

        # ── Key input ───────────────────────────────────────────────────────
        while True:
            choice = click.getchar().lower().strip()
            if choice in ("\r", "\n", ""):
                choice = "q"
                break
            if choice in ("c", "r", "u", "p", "s", "w", "q"):
                break

        console.print(f"[dim]{choice}[/dim]")
        console.print()

        # ── Handle choice ───────────────────────────────────────────────────
        if choice == "q":
            console.print("[dim]  Exiting dashboard.[/dim]")
            break

        elif choice == "c":
            from ace.cli import commit_cmd
            try:
                commit_cmd(offline=offline)
            except Exception as e:
                console.print(f"[error]  Error: {e}[/error]")

        elif choice == "r":
            from ace.cli import review_cmd
            try:
                review_cmd(all_changes=True, offline=offline)
            except Exception as e:
                console.print(f"[error]  Error: {e}[/error]")

        elif choice == "u":
            from ace.cli import undo_cmd
            try:
                undo_cmd(offline=offline)
            except Exception as e:
                console.print(f"[error]  Error: {e}[/error]")

        elif choice == "s":
            from ace.cli import stats_cmd
            try:
                stats_cmd()
            except Exception as e:
                console.print(f"[error]  Error: {e}[/error]")

        elif choice == "w":
            _handle_switch_repo(git_ops, parent_dir)

        elif choice == "p":
            _handle_plan_command(git_ops, offline)

        console.print()
        console.print("[dim]  Press any key to return ...[/dim]  ", end="")
        click.getchar()


# ─── Action handlers ──────────────────────────────────────────────────────────

def _handle_switch_repo(git_ops: GitOps, parent_dir: Path) -> None:
    """Interactive repository switcher."""
    from ace.ui.prompts import prompt_select

    all_repos: list[str] = []
    try:
        all_repos = sorted(
            p.name for p in parent_dir.iterdir()
            if p.is_dir() and (p / ".git").exists()
        )
    except Exception:
        pass

    if not all_repos:
        print_warning("No other repositories found in the parent directory.")
        return

    current_name = Path(git_ops.working_dir).name
    display_options = [
        f"{name}  [bold #00E676](current)[/bold #00E676]" if name == current_name else name
        for name in all_repos
    ]

    console.print("[bold white]  Repositories in workspace:[/bold white]")
    sel_idx = prompt_select(display_options, prompt_text="  Repository number", default="s")
    if sel_idx < 0:
        console.print("[dim]  Switch cancelled.[/dim]")
        return

    selected = all_repos[sel_idx]
    new_path  = parent_dir / selected
    try:
        from ace.core.git_ops import GitOps as _GitOps
        git_ops.__dict__.update(_GitOps(str(new_path)).__dict__)
        print_success(f"Switched to  {selected}")
    except Exception as e:
        console.print(f"[error]  Failed to switch: {e}[/error]")


def _handle_plan_command(git_ops: GitOps, offline: bool) -> None:
    """AI natural-language command planner."""
    from ace.ai.intent_parser import IntentParser
    from ace.core.safety import SafetyChecker
    from ace.ui.display import show_plan
    from ace.ui.prompts import confirm as ui_confirm

    query = typer.prompt("  What do you want to do with Git?")
    if not query.strip():
        return

    parser = IntentParser(git_ops)
    try:
        with spinner("Planning commands..."):
            parsed = parser.parse_intent(query, offline=offline)

        commands    = parsed.get("commands", [])
        explanation = parsed.get("explanation", "")

        if not commands:
            console.print(f"[dim]  No commands planned.[/dim]  {explanation}")
            return

        show_plan(commands, [explanation] + [""] * (len(commands) - 1))

        # Safety classification
        highest_risk  = "safe"
        risk_details: list[str] = []
        for cmd in commands:
            r_level, r_desc, _ = SafetyChecker.analyze_command(cmd)
            if r_level == "destructive":
                highest_risk = "destructive"
                risk_details.append(f"[bold]{cmd}[/bold]\n{r_desc}")
            elif r_level == "moderate" and highest_risk != "destructive":
                highest_risk = "moderate"

        execute = True
        if highest_risk == "destructive":
            show_warning_panel("\n\n".join(risk_details), "Destructive Operation Detected")
            execute = ui_confirm("Execute these destructive commands?", default=False)
        elif highest_risk == "moderate":
            execute = ui_confirm("Execute this plan?", default=True)

        if execute:
            for cmd in commands:
                console.print(
                    Text.assemble(
                        ("  › ", "bold #00D5FF"),
                        ("Running  ", "#9E9E9E"),
                        (cmd, "bold white"),
                    )
                )
                git_args = cmd[4:] if cmd.startswith("git ") else cmd
                result   = git_ops.execute(git_args)
                if result.strip():
                    console.print(f"[dim]{result}[/dim]")
            print_success("Plan executed successfully.")
        else:
            console.print("[dim]  Plan aborted.[/dim]")

    except Exception as e:
        console.print(f"[error]  Error: {e}[/error]")
