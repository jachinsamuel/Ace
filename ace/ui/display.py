import sys
from contextlib import contextmanager
from typing import List, Dict, Any
from rich.console import Console
from rich.text import Text
from ace.ui.themes import get_rich_theme

# Initialize global Rich console (force_terminal ensures colour/Unicode on Windows)
console     = Console(theme=get_rich_theme(), force_terminal=True)
err_console = Console(theme=get_rich_theme(), force_terminal=True, stderr=True)

# Status symbols — safe subset that renders in all modern Windows terminals
_SYM_INFO    = ">>"   # informational
_SYM_SUCCESS = "**"   # success
_SYM_WARNING = "!!"   # warning
_SYM_ERROR   = "EE"   # error


# ─── Inline status printers ──────────────────────────────────────────────────

def print_info(message: str) -> None:
    """Print an informational message."""
    console.print(f" [info]{_SYM_INFO}[/info]  {message}")

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f" [success]{_SYM_SUCCESS}[/success]  {message}")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f" [warning]{_SYM_WARNING}[/warning]  [warning]{message}[/warning]")

def print_error(message: str) -> None:
    """Print an error message."""
    err_console.print(f" [error]{_SYM_ERROR}[/error]  [error]{message}[/error]")


# ─── Panels ──────────────────────────────────────────────────────────────────

def show_warning_panel(message: str, title: str = "Warning") -> None:
    """Show a styled amber warning panel."""
    from rich.panel import Panel
    from rich import box
    panel = Panel(
        Text.from_markup(message),
        title=f"[bold #FFD600] ! {title}[/bold #FFD600]",
        border_style="#FFD600",
        box=box.ROUNDED,
        expand=False,
        padding=(0, 2),
    )
    console.print()
    console.print(panel)
    console.print()

def show_error_panel(message: str, title: str = "Error") -> None:
    """Show a styled red error panel."""
    from rich.panel import Panel
    from rich import box
    panel = Panel(
        Text.from_markup(message),
        title=f"[bold #FF1744] {_SYM_ERROR} {title}[/bold #FF1744]",
        border_style="#FF1744",
        box=box.ROUNDED,
        expand=False,
        padding=(0, 2),
    )
    console.print()
    console.print(panel)
    console.print()


# ─── Spinner ─────────────────────────────────────────────────────────────────

@contextmanager
def spinner(message: str = "Thinking..."):
    """Context manager to display a loading spinner."""
    with console.status(f"[ai]{message}[/ai]", spinner="dots") as status:
        yield status


# ─── Execution plan ──────────────────────────────────────────────────────────

def show_plan(commands: List[str], explanations: List[str]) -> None:
    """Display the AI execution plan as a clean numbered table."""
    from rich.table import Table
    from rich import box

    table = Table(
        show_header=True,
        header_style="bold #9E9E9E",
        box=box.SIMPLE_HEAD,
        border_style="#FF6D00",
        title="[bold white]Proposed Execution Plan[/bold white]",
        title_justify="left",
        expand=False,
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("#",   justify="right",  style="bold #666666", width=4)
    table.add_column("Command",               style="bold white",   width=32)
    table.add_column("What it does",          style="#BDBDBD")

    for i, (cmd, exp) in enumerate(zip(commands, explanations), 1):
        # Colour-highlight the "git" or "ace" prefix
        if cmd.startswith("git "):
            cmd_text = Text("git ", style="bold #00D5FF") + Text(cmd[4:], style="bold white")
        elif cmd.startswith("ace "):
            cmd_text = Text("ace ", style="bold #FF6D00") + Text(cmd[4:], style="bold white")
        else:
            cmd_text = Text(cmd, style="bold white")

        table.add_row(str(i), cmd_text, exp)

    console.print()
    console.print(table)
    console.print()


# ─── Commit message ──────────────────────────────────────────────────────────

def show_commit_message(message: str) -> None:
    """Display a suggested commit message in a styled panel."""
    import re
    from rich.panel import Panel
    from rich import box

    lines   = message.splitlines()
    subject = lines[0] if lines else ""
    body    = "\n".join(lines[1:]) if len(lines) > 1 else ""

    text = Text()
    conv_match = re.match(r"^(\w+)(?:\(([^)]+)\))?(!?):(.*)$", subject)
    if conv_match:
        c_type, c_scope, c_breaking, c_desc = conv_match.groups()
        text.append(c_type,         style="bold #00D5FF")
        if c_scope:
            text.append(f"({c_scope})",  style="bold #B388FF")
        if c_breaking:
            text.append("!",            style="bold #FF1744")
        text.append(f":{c_desc}",   style="bold #00E676")
    else:
        text.append(subject, style="bold #00E676")

    if body:
        text.append("\n" + body, style="#BDBDBD")

    # Character-count indicator in subtitle
    sub_len = len(subject)
    if sub_len <= 50:
        count_color = "#00E676"
    elif sub_len <= 72:
        count_color = "#FFD600"
    else:
        count_color = "#FF1744"

    subtitle = (
        f"[#666666]chars:[/#666666] "
        f"[bold {count_color}]{sub_len}[/bold {count_color}]"
        f"[#666666]/72[/#666666]"
    )

    panel = Panel(
        text,
        title="[bold white]Suggested Commit[/bold white]",
        subtitle=subtitle,
        subtitle_align="right",
        border_style="#FF6D00",
        box=box.ROUNDED,
        expand=False,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


# ─── Diff renderer ───────────────────────────────────────────────────────────

def show_diff(diff_text: str) -> None:
    """Render a syntax-highlighted git diff."""
    from rich.syntax import Syntax
    if not diff_text.strip():
        console.print("[muted]  No changes to display.[/muted]")
        return
    syntax = Syntax(diff_text, "diff", theme="ansi_dark", word_wrap=True)
    console.print(syntax)


# ─── Code review results ─────────────────────────────────────────────────────

def show_review(findings: List[Dict[str, Any]], score: float) -> None:
    """Display aggregated AI code review findings."""
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich import box

    # Score badge
    if score >= 8:
        score_style = "bold #00E676"
    elif score >= 5:
        score_style = "bold #FFD600"
    else:
        score_style = "bold #FF1744"

    console.print()
    console.print(
        Text.assemble(
            ("  AI Code Review  ", "bold white on #1A237E"),
            ("  Score: ", "bold #9E9E9E"),
            (f"{score}/10", score_style),
        )
    )
    console.print()

    if not findings:
        print_success("No issues found — clean code!")
        return

    sev_sym = {
        "critical": ("EE", "bold #FF1744"),
        "warning":  ("!!", "bold #FFD600"),
        "info":     (">>", "bold #00D5FF"),
    }

    for item in findings:
        sev   = item.get("severity", "info").lower()
        sym, sym_style = sev_sym.get(sev, (">>", "bold #00D5FF"))

        loc  = f"{item.get('file', '?')}:{item.get('line', '?')}"
        cat  = item.get("category", "issue").upper()
        desc = item.get("description", "")
        fix  = item.get("fix", "")

        # Header row
        console.print(
            Text.assemble(
                (f" {sym} ", sym_style),
                (f"{cat}  ", "bold white"),
                (loc, "underline #00D5FF"),
            )
        )
        console.print(f"   [#BDBDBD]{desc}[/#BDBDBD]")

        if fix:
            console.print("   [#666666]Suggested fix:[/#666666]")
            syntax = Syntax(
                fix, "python",
                theme="ansi_dark",
                indent_guides=False,
                word_wrap=True,
            )
            console.print(
                Panel(syntax, border_style="#444444", box=box.SIMPLE, expand=False, padding=(0, 1))
            )
        console.print()
