# Styling theme definitions for Rich terminal output

from rich.theme import Theme

# Premium dark-mode color palette (Neon-Sunset style)
THEME_STYLES = {
    "info": "bold #00D5FF",          # Vibrant cyan
    "warning": "bold #FFD600",       # Neon yellow
    "error": "bold #FF1744",         # Electric red
    "success": "bold #00E676",       # Spring green
    "ai": "bold #FF6D00",            # Safety orange / Ace signature highlight
    "git.add": "#00E676",
    "git.delete": "#FF1744",
    "git.modify": "#FFD600",
    "command": "bold #FFFFFF on #1A237E", # Deep blue background for git commands
    "path": "underline #00D5FF",
    "panel.border": "#FF6D00",
    "highlight": "bold #B388FF",      # Light violet highlight
}

def get_rich_theme() -> Theme:
    """Get the Rich theme object containing all styling rules."""
    return Theme(THEME_STYLES)

