import sys
from contextlib import contextmanager
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from ace.ui.themes import get_rich_theme

# Initialize global Rich console with the application theme
console = Console(theme=get_rich_theme())

def print_info(message: str) -> None:
    """Print an informational message."""
    console.print(f"[info]ℹ {message}[/info]")

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]✅ {message}[/success]")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]⚠️  {message}[/warning]")

def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]❌ {message}[/error]", file=sys.stderr)

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
    """Display the execution plan panel with commands and their description."""
    content = Text()
    content.append("Proposed Plan:\n", style="bold white")
    
    for i, (cmd, exp) in enumerate(zip(commands, explanations), 1):
        content.append(f"\n {i}. ", style="bold purple")
        content.append(f"{cmd}\n", style="bold white")
        content.append(f"    ↳ {exp}\n", style="dim italic")

    panel = Panel(
        content,
        title="🧠 Ace AI Git Plan",
        border_style="panel.border",
        expand=False
    )
    console.print(panel)

def show_commit_message(message: str) -> None:
    """Display a suggested commit message in a clear panel."""
    # Split into subject and body
    lines = message.splitlines()
    subject = lines[0] if lines else ""
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    text = Text()
    text.append(subject, style="bold green")
    if body:
        text.append("\n" + body, style="white")

    panel = Panel(
        text,
        title="📝 Suggested Commit Message",
        border_style="panel.border",
        expand=False
    )
    console.print(panel)

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
