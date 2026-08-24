#!/usr/bin/env bash
# ==============================================================================
# Ace — One-Line Installer for Linux and macOS
# Repo: https://github.com/jachinsamuel/Ace
# ==============================================================================

set -e

BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

echo -e "${CYAN}${BOLD}"
echo "   ___        "
echo "  / _ | ______ "
echo " / __ |/ __/ -_)"
echo "/_/ |_|\__/\__/ "
echo "AI-Powered Git Copilot Installer"
echo -e "${RESET}"

# 1. Check for Python 3.11+
check_python() {
    for cmd in python3 python py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
            if [ -n "$version" ]; then
                major=$(echo "$version" | cut -d. -f1)
                minor=$(echo "$version" | cut -d. -f2)
                if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
                    echo "$cmd"
                    return 0
                fi
            fi
        fi
    done
    return 1
}

PYTHON_CMD=$(check_python || true)

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Python 3.11 or newer is required to install Ace.${RESET}"
    echo "Please install Python 3.11+ from https://www.python.org or via your system package manager."
    exit 1
fi

echo -e "${GREEN}✔${RESET} Found compatible Python: ${BOLD}$($PYTHON_CMD --version)${RESET}"

# 2. Try uv or pipx if available, otherwise install into isolated ~/.local/share/ace
INSTALL_DIR="$HOME/.local/share/ace"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

if command -v uv >/dev/null 2>&1; then
    echo -e "${CYAN}→ Installing via uv tool...${RESET}"
    uv tool install ace-git-copilot --force
elif command -v pipx >/dev/null 2>&1; then
    echo -e "${CYAN}→ Installing via pipx...${RESET}"
    pipx install ace-git-copilot --force
else
    echo -e "${CYAN}→ Creating isolated environment in ${INSTALL_DIR}...${RESET}"
    mkdir -p "$INSTALL_DIR"
    "$PYTHON_CMD" -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade ace-git-copilot
    
    # Symlink to ~/.local/bin/ace
    ln -sf "$INSTALL_DIR/venv/bin/ace" "$BIN_DIR/ace"
fi

# 3. Check PATH
PATH_FOUND=false
case ":$PATH:" in
    *":$BIN_DIR:"*) PATH_FOUND=true ;;
    *":$HOME/.local/bin:"*) PATH_FOUND=true ;;
esac

echo ""
echo -e "${GREEN}${BOLD}✔ Ace Git Copilot installed successfully!${RESET}"
echo ""

if [ "$PATH_FOUND" = false ]; then
    echo -e "${YELLOW}Notice: $BIN_DIR is not in your current PATH.${RESET}"
    echo "To run 'ace' directly, add the following line to your ~/.bashrc or ~/.zshrc:"
    echo -e "  ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
    echo ""
    echo "Then reload your shell: ${BOLD}source ~/.bashrc${RESET} (or source ~/.zshrc)"
    echo ""
fi

echo -e "Get started by running:"
echo -e "  ${CYAN}${BOLD}ace setup${RESET}   → Configure your preferred AI model"
echo -e "  ${CYAN}${BOLD}ace dash${RESET}    → Open the interactive Git cockpit"
echo ""
