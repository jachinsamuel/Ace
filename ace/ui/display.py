import sys
from contextlib import contextmanager
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich import box
from ace.ui.themes import get_rich_theme

# Initialize global Rich console with the application theme
console = Console(theme=get_rich_theme())

def print_info(message: str) -> None:
    """Print an informational message."""
    console.print(f" [info]⚡ {message}[/info]")

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f" [success]✔ {message}[/success]")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f" [warning]⚠️  {message}[/warning]")

def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f" [error]✖ {message}[/error]", file=sys.stderr)

def show_warning_panel(message: str, title: str = "WARNING") -> None:
    """Show a yellow warning panel with a title."""
    panel = Panel(
        Text.from_markup(message),
        title=f"⚠️  {title}",
        border_style="warning",
        expand=False
    )
    console.print(panel)

def show_error_panel(message: str, title: str = "ERROR") -> None:
    """Show a red error panel with a title."""
    panel = Panel(
        Text.from_markup(message),
        title=f"❌ {title}",
        border_style="error",
        expand=False
    )
    console.print(panel)

@contextmanager
def spinner(message: str = "Thinking..."):
    """Context manager to display a terminal loading spinner with a message."""
    with console.status(f"[ai]{message}[/ai]", spinner="dots") as status:
        yield status

def show_plan(commands: List[str], explanations: List[str]) -> None:
    """Display the execution plan table with commands and descriptions."""
    table = Table(
        show_header=True,
        header_style="bold #FF6D00",
        box=box.ROUNDED,
        border_style="#FF6D00",
        title="[bold white]🧠 Proposed Execution Plan[/bold white]",
        title_justify="left",
        expand=False,
        padding=(0, 2)
    )
    table.add_column("Step", justify="center", style="bold #00D5FF", width=6)
    table.add_column("Command", style="bold white", width=30)
    table.add_column("Explanation", style="#E0E0E0")

    for i, (cmd, exp) in enumerate(zip(commands, explanations), 1):
        cmd_styled = Text(cmd, style="bold white")
        if cmd.startswith("git "):
            cmd_styled = Text("git ", style="bold #Highlight") + Text(cmd[4:], style="bold white")
        elif cmd.startswith("ace "):
            cmd_styled = Text("ace ", style="bold #ai") + Text(cmd[4:], style="bold white")
            
        table.add_row(f"{i:02d}", cmd_styled, exp)
        
    console.print()
    console.print(table)
    console.print()

def show_commit_message(message: str) -> None:
    """Display a suggested commit message in a clear panel with length warning indicators."""
    lines = message.splitlines()
    subject = lines[0] if lines else ""
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    text = Text()
    # Style conventional commit components if present
    import re
    conv_match = re.match(r"^(\w+)(?:\(([^)]+)\))?(!?):(.*)$", subject)
    if conv_match:
        c_type, c_scope, c_breaking, c_desc = conv_match.groups()
        text.append(c_type, style="bold #00D5FF")
        if c_scope:
            text.append(f"({c_scope})", style="bold #Highlight")
        if c_breaking:
            text.append("!", style="bold #error")
        text.append(f":{c_desc}", style="bold #success")
    else:
        text.append(subject, style="bold #success")
        
    if body:
        text.append("\n" + body, style="#E0E0E0")

    # Character count styling for the subtitle
    sub_len = len(subject)
    if sub_len <= 50:
        sub_color = "#00E676"  # optimal
    elif sub_len <= 72:
        sub_color = "#FFD600"  # acceptable warning
    else:
        sub_color = "#FF1744"  # too long
        
    subtitle = f"[dim]Length:[/dim] [bold {sub_color}]{sub_len}[/bold {sub_color}][dim]/72 chars[/dim]"

    panel = Panel(
        text,
        title="[bold white]📝 Suggested Commit Message[/bold white]",
        subtitle=subtitle,
        subtitle_align="right",
        border_style="#FF6D00",
        box=box.ROUNDED,
        expand=False,
        padding=(1, 2)
    )
    console.print()
    console.print(panel)
    console.print()

def show_diff(diff_text: str) -> None:
    """Render a syntax-highlighted git diff."""
    if not diff_text.strip():
        console.print("[dim]No changes to display.[/dim]")
        return
        
    syntax = Syntax(diff_text, "diff", theme="ansi_dark", word_wrap=True)
    console.print(syntax)

def show_review(findings: List[Dict[str, Any]], score: float) -> None:
    """Display aggregated AI code review findings."""
    console.print(f"\n[bold]🔍 AI Code Review Score: [ai]{score}/10[/ai][/bold]\n")
    
    if not findings:
        console.print("[success]✅ No issues found! Excellent work.[/success]")
        return

    # Severity mapping
    sev_emoji = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "💡"
    }
    sev_style = {
        "critical": "bold red",
        "warning": "yellow",
        "info": "cyan"
    }

    for item in findings:
        sev = item.get("severity", "info").lower()
        emoji = sev_emoji.get(sev, "💡")
        style = sev_style.get(sev, "white")
        
        console.print(f" {emoji} [bold {style}]{item.get('category', 'ISSUE').upper()}[/bold {style}] in [path]{item.get('file')}:{item.get('line', '?')}[/path]")
        console.print(f"    {item.get('description')}")
        if item.get("fix"):
            console.print("    [dim]Suggested fix:[/dim]")
            syntax = Syntax(item.get("fix"), "python", theme="ansi_dark", indent_guides=False, word_wrap=True)
            console.print(Panel(syntax, border_style="dim", expand=False))
        console.print()
