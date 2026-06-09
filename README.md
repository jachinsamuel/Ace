# ♠️ Ace — AI-Powered Git Copilot

[![PyPI Version](https://img.shields.io/pypi/v/ace-git-copilot?color=blue)](https://pypi.org/project/ace-git-copilot/)
[![Python Version](https://img.shields.io/pypi/pyversions/ace-git-copilot)](https://pypi.org/project/ace-git-copilot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Ace** is an intelligent command-line tool that brings AI assistance directly to your Git workflow. Talk to Git in plain English — Ace translates your intents into Git commands, explains what it is doing, and runs them safely. It also features a fully interactive terminal user interface (TUI) dashboard to help manage your repositories with ease.

---

## ✨ Features

*   **🧠 Natural Language Git Commands**: Translate commands like `"undo my last commit but keep changes"` or `"create a branch login-page"` into clean, standard Git actions.
*   **📝 AI-Powered Commits**: Analyzes staged diffs and generates Conventional Commit messages automatically.
*   **🔍 Automated Code Review**: Rates code quality and points out bugs, security flaws, or styling issues inside staged or unstaged diffs.
*   **⚔️ Merge Conflict Resolution**: Interactively walks you through conflict blocks and suggests correct merges.
*   **📊 Rich Repo Stats & Changelogs**: Instantly computes repository statistics (commits, additions, deletions, file counts) and generates markdown release notes since the last tag.
*   **🔎 Semantic Commit Search**: Search commits by natural language queries (e.g. `"fixed the authorization bug"`) instead of matching literal strings.
*   **🔥 Interactive TUI Dashboard**: Run `ace dash` to launch a beautiful terminal interface showing current status, branch info, commit charts, and interactive menus.
*   **🛡️ Safety First**: Classifies actions into safe, moderate, or destructive levels, and requests confirmation before running destructive operations.

---

## 🚀 Installation

Install the package directly from PyPI:
```bash
pip install ace-git-copilot
```

*Note: Make sure your Python scripts path (e.g., `AppData\Roaming\Python\Python3xx\Scripts` on Windows) is added to your environment `PATH` variable.*

To update to the latest version:
```bash
pip install --upgrade ace-git-copilot
```

---

## ⚙️ Configuration & Setup

Run the built-in configuration wizard to select your AI model provider:
```bash
ace setup
```
Ace saves your configuration file to `~/.ace/config.toml`. It supports:
1.  **NVIDIA NIM Cloud API** (high-speed, high-accuracy models) using your NVIDIA developer API key.
2.  **Local Ollama Models** (100% offline, free private local models like `qwen2.5-coder`, `llama3.1`, or `mistral`). If the requested model isn't downloaded, Ace will automatically pull it for you.

---

## 🛠️ Usage

### 💬 Natural Language Mode
Run natural language requests directly in quotes:
```bash
ace "stage everything and commit with a message about authentication"
ace "undo my last commit but keep the files"
ace "switch to a new branch called design-updates"
```

### 📋 Command-Line Toolchain
Ace has dedicated subcommands for specific tasks:

| Command | Shorthand | Description |
|:---|:---|:---|
| `ace stage [files]` | `ace add` | Stage specific files or all untracked changes. |
| `ace commit` | — | Generate Conventional Commit messages from diffs and commit. |
| `ace review` | — | Run code review on staged, unstaged, or branch changes. |
| `ace resolve` | — | Step-by-step interactive merge conflict resolver. |
| `ace explain <query>`| — | Explain complex Git commands or repository errors. |
| `ace stats` | — | Rich visualization of repo statistics, extension breakdowns, and history. |
| `ace changelog` | — | Compile release changelogs since the last tag. |
| `ace pr` | — | Draft a Markdown pull request title and description. |
| `ace search <query>` | — | Semantically search commit history using natural language. |
| `ace ignore <rule>` | — | Generate and append standard templates to `.gitignore`. |
| `ace undo` | — | Safely revert the last action after checking repository status. |
| `ace dash` | — | Launch the interactive repository management console. |
| `ace config` | — | Print out active configuration settings. |

---

## 🎨 Interactive Terminal Dashboard (TUI)

Launch the repository dashboard by running:
```bash
ace dash
```

The dashboard features:
*   A vibrant start-up logo.
*   Active branch info, tracking status, and repository charts.
*   Interactive shortcuts for one-key commits, reviews, undos, and configuration management.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
