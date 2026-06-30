# Styling theme definitions for Rich terminal output

from rich.theme import Theme

# Premium Neon-Sunset dark-mode palette
THEME_STYLES = {
    # Status levels
    "info":        "bold #00D5FF",        # Vibrant cyan
    "warning":     "bold #FFD600",        # Neon amber
    "error":       "bold #FF1744",        # Electric red
    "success":     "bold #00E676",        # Spring green
    "muted":       "#666666",             # Dim grey for secondary text

    # Brand / AI identity
    "ai":          "bold #FF6D00",        # Safety-orange — Ace signature colour
    "accent":      "bold #B388FF",        # Soft violet accent
    "highlight":   "bold #B388FF",        # Alias for highlight

    # Git diff colours
    "git.add":     "#00E676",
    "git.delete":  "#FF1744",
    "git.modify":  "#FFD600",

    # Structural
    "command":     "bold #FFFFFF on #1A237E",  # Deep navy background for commands
    "path":        "underline #00D5FF",
    "label":       "bold #9E9E9E",             # Neutral label text
    "panel.border": "#FF6D00",
}

def get_rich_theme() -> Theme:
    """Get the Rich theme object containing all styling rules."""
    return Theme(THEME_STYLES)
