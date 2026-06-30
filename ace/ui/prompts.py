import click
from typing import Dict, Tuple
from rich.text import Text
from ace.ui.display import console


def confirm(question: str, default: bool = True) -> bool:
    """
    Prompt the user for a yes/no confirmation with a styled inline prompt.

    Returns True if confirmed, False otherwise.
    """
    hint = "[Y/n]" if default else "[y/N]"
    console.print(
        Text.assemble(
            ("  › ", "bold #00D5FF"),
            (question + "  ", "bold white"),
            (hint, "bold #666666"),
            ("  ", ""),
        ),
        end="",
    )
    val = click.getchar()
    console.print()  # newline after keypress

    val = val.lower().strip()
    if val in ("y", "yes"):
        return True
    if val in ("n", "no"):
        return False
    if val in ("\r", "\n", ""):
        return default
    return default


def prompt_action(options: Dict[str, Tuple[str, str]], default_key: str = "\r") -> str:
    """
    Display a one-key action menu and return the pressed key.

    options: dict mapping key character → (label, description)
             e.g., {"\r": ("Accept", "accept the suggestion"), "e": ("Edit", "edit inline")}
    """
    parts: list = [("  ", "")]
    for idx, (key, (label, _)) in enumerate(options.items()):
        if idx > 0:
            parts.append(("  ·  ", "dim #555555"))
        display_key = "Enter" if key == "\r" else key.upper()
        parts.append((f"[{display_key}]", "bold #00D5FF"))
        parts.append((f" {label}", "#BDBDBD"))

    console.print(Text.assemble(*parts))

    while True:
        char = click.getchar()
        # Normalise Windows CRLF
        if char in ("\r", "\n"):
            char = "\r"
        char_lower = char.lower()

        if char in options:
            return char
        if char_lower in options:
            return char_lower
        if char == "\r" and default_key in options:
            return default_key


def prompt_select(options: list, prompt_text: str = "Choose option", default: str = "s") -> int:
    """
    Prompt the user to select from a numbered list.

    Returns the zero-based index of the selected item, or -1 to skip.
    """
    console.print()
    for idx, opt in enumerate(options, 1):
        console.print(
            Text.assemble(
                (f"  [{idx}]", "bold #00D5FF"),
                ("  ", ""),
                (opt, "white"),
            )
        )
    console.print()

    while True:
        choice = click.prompt(prompt_text, default=default)
        choice_clean = choice.strip().lower()
        if choice_clean in ("s", "skip", "q", "quit", "exit"):
            return -1
        try:
            val = int(choice_clean)
            if 1 <= val <= len(options):
                return val - 1
        except ValueError:
            pass
        console.print(
            Text.assemble(
                ("  ✕ ", "bold #FF1744"),
                ("Invalid choice — enter a number or ", "#BDBDBD"),
                ("s", "bold #00D5FF"),
                (" to skip.", "#BDBDBD"),
            )
        )
