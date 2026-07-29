"""Update checker utility for Ace CLI."""

import json
import os
import time
import urllib.request
from pathlib import Path
from ace import __version__ as CURRENT_VERSION

CACHE_FILE = Path.home() / ".ace" / "version_cache.json"
CHECK_INTERVAL_SECONDS = 86400  # Check PyPI once per 24 hours


def check_for_updates() -> None:
    """
    Check PyPI for newer version of ace-git-copilot.
    Display a non-intrusive notification if a newer version exists.
    """
    # Skip during CI runs
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        return

    latest_version = None
    now = time.time()

    # Read cache
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            last_check = data.get("last_check", 0)
            cached_latest = data.get("latest_version")
            if now - last_check < CHECK_INTERVAL_SECONDS and cached_latest:
                latest_version = cached_latest
        except Exception:
            pass

    # Fetch from PyPI if cache expired or missing
    if not latest_version:
        try:
            url = "https://pypi.org/pypi/ace-git-copilot/json"
            req = urllib.request.Request(url, headers={"User-Agent": "ace-cli"})
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                pypi_data = json.loads(resp.read().decode("utf-8"))
                latest_version = pypi_data.get("info", {}).get("version")

            # Write cache
            if latest_version:
                CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(
                    json.dumps({"last_check": now, "latest_version": latest_version}),
                    encoding="utf-8",
                )
        except Exception:
            return

    if not latest_version:
        return

    def parse_ver(v_str: str):
        try:
            return tuple(int(x) for x in v_str.split("."))
        except Exception:
            return (0, 0, 0)

    if parse_ver(latest_version) > parse_ver(CURRENT_VERSION):
        try:
            from ace.ui.display import console

            console.print(
                f"[dim yellow]💡 A new version of Ace is available: [bold]v{CURRENT_VERSION}[/bold] → [bold #00E676]v{latest_version}[/bold #00E676]. "
                f"Run [bold cyan]pip install --upgrade ace-git-copilot[/bold cyan] to update.[/dim yellow]\n"
            )
        except Exception:
            pass
