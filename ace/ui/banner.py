import random
import time
from rich.live import Live
from rich.text import Text
from ace.ui.display import console

BANNER_LINES = [
    " █████╗   ██████╗ ███████╗",
    "██╔══██╗ ██╔════╝ ██╔════╝",
    "███████║ ██║      █████╗  ",
    "██╔══██║ ██║      ██╔══╝  ",
    "██║  ██║ ╚██████╗ ███████╗",
    "╚═╝  ╚═╝  ╚═════╝ ╚══════╝"
]

def get_fire_frame(frame: int) -> Text:
    """Generates a single frame of the flickering fire ASCII banner."""
    text = Text()
    for row_idx, line in enumerate(BANNER_LINES):
        for col_idx, char in enumerate(line):
            if char == " ":
                text.append(" ")
            else:
                # Determine color palette based on row temperature (top is hotter, bottom is cooler)
                if row_idx == 0:
                    sub_colors = ["orange1", "gold1", "yellow", "bright_white"]
                elif row_idx in (1, 2):
                    sub_colors = ["dark_orange", "orange3", "orange1", "gold1", "yellow"]
                elif row_idx in (3, 4):
                    sub_colors = ["red", "orange_red1", "dark_orange", "orange3"]
                else:
                    sub_colors = ["red", "orange_red1", "dark_orange"]
                
                # Dynamic flicker effect using frame number, column position, and random fluctuations
                sub_idx = (frame + col_idx + random.randint(0, 2)) % len(sub_colors)
                color = sub_colors[sub_idx]
                text.append(char, style=f"bold {color}")
        text.append("\n")
    return text

def get_fire_banner_static() -> Text:
    """Returns a static fire gradient ASCII art banner."""
    text = Text()
    row_colors = [
        "yellow",       # Row 0
        "gold1",        # Row 1
        "orange1",      # Row 2
        "orange3",      # Row 3
        "orange_red1",  # Row 4
        "red"           # Row 5
    ]
    for line, color in zip(BANNER_LINES, row_colors):
        text.append(line + "\n", style=f"bold {color}")
    return text

def animate_fire_banner(duration_seconds: float = 1.2):
    """Plays a flickering fire banner animation using Rich's Live render tool."""
    start_time = time.time()
    frame = 0
    with Live(get_fire_frame(frame), console=console, refresh_per_second=12, auto_refresh=False) as live:
        while time.time() - start_time < duration_seconds:
            time.sleep(0.08)
            frame += 1
            live.update(get_fire_frame(frame), refresh=True)
