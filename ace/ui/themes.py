# Styling theme definitions for Rich terminal output

from rich.theme import Theme

# Styles used across the app
THEME_STYLES = {
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "green",
    "ai": "bold orange3",
    "git.add": "green",
    "git.delete": "red",
    "git.modify": "yellow",
    "command": "bold white on blue",
    "path": "underline cyan",
    "panel.border": "orange3",
}

def get_rich_theme() -> Theme:
    """Get the Rich theme object containing all styling rules."""
    return Theme(THEME_STYLES)
