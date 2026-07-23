import os
import sys
import io

# Enforce UTF-8 output on Windows to avoid cp1252 encoding crashes
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Ensure ace is in import path
sys.path.insert(0, os.path.abspath("."))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.terminal_theme import MONOKAI
from ace.ui.themes import get_rich_theme

def make_dashboard():
    console = Console(record=True, width=95, theme=get_rich_theme(), color_system="truecolor")
    
    # 1. Title/Banner
    from ace.ui.banner import get_fire_banner_static
    console.print(get_fire_banner_static())
    console.print(
        Text.assemble(
            ("  Ace", "bold #FF6D00"),
            ("  AI Git Copilot", "bold white"),
            ("  ·  Interactive Dashboard", "dim #9E9E9E"),
        )
    )
    console.print()

    # 2. Status panels (simulated repo)
    st = Table.grid(padding=(0, 2))
    st.add_column(style="label", justify="right", min_width=12)
    st.add_column()
    st.add_row("Branch", Text("  master", style="bold #00E676"))
    st.add_row("Remote", Text("origin/master", style="#9E9E9E"))
    st.add_row("Sync", Text("Up to date", style="#00E676"))
    status_panel = Panel(
        st,
        title="[bold white]Repository[/bold white]",
        border_style="#00D5FF",
        box=box.ROUNDED,
        expand=False,
        padding=(0, 1),
    )

    ct = Table.grid(padding=(0, 2))
    ct.add_column(style="label", justify="right", min_width=12)
    ct.add_column()
    ct.add_row("Staged", Text("2", style="bold #00E676"))
    ct.add_row("Unstaged", Text("1", style="bold #FFD600"))
    ct.add_row("Untracked", Text("none", style="dim #666666"))
    changes_panel = Panel(
        ct,
        title="[bold white]Workspace[/bold white]",
        border_style="#FFD600",
        box=box.ROUNDED,
        expand=False,
        padding=(0, 1),
    )

    rt = Table.grid(padding=(0, 2))
    rt.add_column(style="bold #B388FF", min_width=14)
    rt.add_column(style="dim #9E9E9E")
    rt.add_row("portfolio", "master")
    rt.add_row("blog-engine", "main")
    rt.add_row("docs-site", "develop")
    sibling_panel = Panel(
        rt,
        title="[bold white]Workspace Repos[/bold white]",
        border_style="#B388FF",
        box=box.ROUNDED,
        expand=False,
        padding=(0, 1),
    )

    console.print(Columns([status_panel, changes_panel, sibling_panel]))
    console.print()

    # 3. Workspace file status list
    staged_t = Table(show_header=False, box=None, padding=(0, 2))
    staged_t.add_row(Text.assemble(("+ ", "bold #00E676"), ("src/app/not-found.tsx", "#BDBDBD")))
    staged_t.add_row(Text.assemble(("+ ", "bold #00E676"), ("src/components/fuzzy-text.tsx", "#BDBDBD")))
    console.print(Panel(staged_t, title="[bold #00E676]Staged[/bold #00E676]",
                        border_style="#00E676", box=box.SIMPLE, expand=False))
    console.print()

    # 4. Recent commits table
    commit_table = Table(
        show_header=True,
        header_style="bold #9E9E9E",
        box=box.SIMPLE_HEAD,
        show_edge=False,
        padding=(0, 2),
    )
    commit_table.add_column("Hash", style="#666666", width=8, no_wrap=True)
    commit_table.add_column("Message", style="white", ratio=4)
    commit_table.add_column("Author", style="#B388FF", ratio=2)
    commit_table.add_row("bb56b4e", "docs: swap pip and pipx installation options in README", "Jachin Samuel")
    commit_table.add_row("8353372", "docs: swap Ollama and NVIDIA NIM options in README setup", "Jachin Samuel")
    commit_table.add_row("9a2c06f", "fix(cli): raise typer.Exit after executing NL plan", "Jachin Samuel")
    console.print(
        Panel(commit_table, title="[bold white]Recent Commits[/bold white]",
              border_style="#444444", box=box.ROUNDED, expand=False)
    )
    console.print()

    # 5. Interactive Dashboard Menu
    menu_table = Table.grid(padding=(0, 2))
    menu_table.add_column(style="bold #00D5FF", justify="right", min_width=5)
    menu_table.add_column(style="white")
    menu_table.add_row("[c]", "Run AI Smart Commit")
    menu_table.add_row("[r]", "Run AI Code Review")
    menu_table.add_row("[u]", "Run Smart Undo last action")
    menu_table.add_row("[q]", "Quit dashboard")
    console.print(Panel(menu_table, title="[bold white]Interactive Controls[/bold white]",
                        border_style="#FF6D00", box=box.ROUNDED, expand=False))

    console.save_svg("media/dashboard.svg", title="Ace TUI Dashboard", theme=MONOKAI)

def make_commit_svg():
    console = Console(record=True, width=95, theme=get_rich_theme(), color_system="truecolor")
    
    console.print(Text("🧠 Understanding request: \"add everything and commit\"...", style="italic #00D5FF"))
    console.print()

    # Planned execution plan
    plan_table = Table(
        show_header=True,
        header_style="bold #FF6D00",
        box=box.ROUNDED,
        border_style="#555555",
        padding=(0, 2),
    )
    plan_table.add_column("#", width=3, justify="right")
    plan_table.add_column("Command", style="bold cyan")
    plan_table.add_column("What it does", style="white")
    plan_table.add_row("1", "git add .", "Stages all changes, including 'src/app/not-found.tsx' and 'src/components/fuzzy-text.tsx'")
    plan_table.add_row("2", "ace commit", "Analyzes the changes and opens the interactive Conventional Commit wizard.")
    console.print(Panel(plan_table, title="[bold green]Proposed Execution Plan[/bold green]", border_style="#00E676", expand=False))
    console.print()

    # Prompt
    console.print(Text("  › Do you want to execute this plan?  [Y/n]", style="bold #00D5FF"))
    console.print(Text(" ›  Executing: git add .", style="dim #BDBDBD"))
    console.print(Text(" ›  Executing: ace commit", style="dim #BDBDBD"))
    console.print()

    # Commit proposal
    commit_body = (
        "feat(components): add fuzzy-text component and not-found page\n\n"
        "Added a new FuzzyText component that provides a fuzzy text effect, and a new NotFound page\n"
        "that utilizes this component. The FuzzyText component allows for customization of font size,\n"
        "weight, family, color, and more, and also supports hover and click effects. The NotFound\n"
        "page uses this component to display a 404 message with a fuzzy text effect."
    )
    console.print(Panel(
        Text(commit_body, style="white"),
        title="[bold green]Suggested Commit[/bold green]",
        border_style="#00E676",
        box=box.ROUNDED,
        padding=(1, 2),
        expand=False,
    ))
    console.print()

    # Helper menu
    console.print(Text("  [Enter] Accept & Commit  ·  [E] Edit  ·  [R] Regenerate  ·  [C] Switch format  ·  [S] Skip", style="bold #FF6D00"))
    console.print(Text(" ✔  Committed changes successfully!", style="bold #00E676"))
    console.print(Text(" ✔  Plan executed successfully!", style="bold #00E676"))

    console.save_svg("media/cli_in_action.svg", title="Ace Commit Flow", theme=MONOKAI)

def make_stats_svg():
    console = Console(record=True, width=95, theme=get_rich_theme(), color_system="truecolor")
    
    # Side-by-side tables
    info_table = Table(show_header=False, box=box.ROUNDED, border_style="#00D5FF", padding=(0, 2))
    info_table.add_row(Text("Total Commits: 48", style="bold white"))
    info_table.add_row(Text("Active Branches: 1", style="bold white"))
    
    changes_table = Table(show_header=False, box=box.ROUNDED, border_style="#FFD600", padding=(0, 2))
    changes_table.add_row(Text("Staged: 0 files", style="dim"))
    changes_table.add_row(Text("Unstaged: 0 files", style="dim"))
    changes_table.add_row(Text("Untracked: 0 files", style="dim"))
    
    console.print(Columns([
        Panel(info_table, title="[bold white]Repository Info[/bold white]", border_style="#00D5FF", box=box.ROUNDED),
        Panel(changes_table, title="[bold white]Workspace Changes[/bold white]", border_style="#FFD600", box=box.ROUNDED)
    ]))
    console.print()

    # Contributors Table
    cont_table = Table(title="[bold white]Top Contributors[/bold white]", box=box.ROUNDED, border_style="#B388FF", padding=(0, 2))
    cont_table.add_column("Author", style="bold white")
    cont_table.add_column("Commits", style="bold white")
    cont_table.add_column("Lines Added/Deleted", style="bold white")
    cont_table.add_column("Activity Bar", style="bold #B388FF")
    cont_table.add_row("jachinsamuel", "48 (100.0%)", "+11899/-988", "████████████████████")
    console.print(cont_table)
    console.print()

    # Language distribution
    lang_table = Table(title="[bold white]File Extension Distribution[/bold white]", box=box.ROUNDED, border_style="#FFD600", padding=(0, 2))
    lang_table.add_column("Extension", style="bold white")
    lang_table.add_column("Files Count", style="bold white")
    lang_table.add_column("Percentage Bar", style="bold #FFD600")
    lang_table.add_row(".py", "87", "█████████████░░░░░░░")
    lang_table.add_row(".md", "38", "█████░░░░░░░░░░░░░░░")
    lang_table.add_row(".json", "8", "█░░░░░░░░░░░░░░░░░░░")
    console.print(lang_table)
    console.print()

    console.save_svg("media/stats.svg", title="Ace Repository Stats", theme=MONOKAI)

if __name__ == "__main__":
    os.makedirs("media", exist_ok=True)
    make_dashboard()
    make_commit_svg()
    make_stats_svg()
    print("SVGs generated successfully!")
