import click
from typing import Dict, Tuple
from rich.text import Text
from ace.ui.display import console

def confirm(question: str, default: bool = True) -> bool:
    """
    Prompt the user for a yes/no confirmation.
    
    Returns True if confirmed, False otherwise.
    """
    suffix = " [Y/n]" if default else " [y/N]"
    prompt = f"[bold white]{question}[/bold white]{suffix}"
    
    # Render with rich, but prompt using click
    console.print(prompt, end="")
    val = click.getchar()
    console.print()  # Add newline after char entry
    
    val = val.lower().strip()
    if val in ("y", "yes"):
        return True
    if val in ("n", "no"):
        return False
    if val == "\r" or val == "\n" or not val:
        return default
    return default

def prompt_action(options: Dict[str, Tuple[str, str]], default_key: str = "\r") -> str:
    """
    Prompt the user to select from a set of actions using single-key inputs.
    
    options: dict mapping key character to a tuple (label, description)
             e.g., {"\r": ("Accept", "Accept the suggestion"), "e": ("Edit", "Edit the content")}
    default_key: key returned if user presses Enter
    
    Returns the selected key character.
    """
    text = Text()
    for key, (label, _) in options.items():
        if text.cell_len > 0:
            text.append("  ")
        
        display_key = "Enter" if key == "\r" else key
        text.append(f"[{display_key}]", style="bold cyan")
        text.append(f" {label}", style="white")
        
    console.print(text)
    
    while True:
        char = click.getchar()
        # Handle Windows carriage return
        if char == "\r" or char == "\n":
            char = "\r"
            
        char_lower = char.lower()
        
        # Check direct match or lowercase match
        if char in options:
            return char
        if char_lower in options:
            return char_lower
            
        # If enter pressed and default exists
        if char == "\r" and default_key in options:
            return default_key
            
        # Invalid option, try again silently or with a brief indicator
        pass
