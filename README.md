# Ace — AI-Powered Git Copilot

> Ace is an intelligent terminal tool that understands what you want to do with Git and does it for you. Talk to Git in plain English — Ace figures out the right git commands, explains what it's doing, and executes safely.

---

## 🚀 Installation

Install in editable mode globally/user-wide:
```bash
python -m pip install --user -e D:\Ace
```

*Note: Make sure your Python scripts path (e.g., `AppData\Roaming\Python\Python3xx\Scripts`) is added to your Windows PATH environment variable.*

---

## ⚙️ Configuration

Configure your AI provider (NVIDIA NIM or local Ollama) by running:
```bash
ace setup
```
This will save your preferences to `~/.ace/config.toml`.

---

## 🛠️ Usage & Commands

### 🧠 Natural Language Input
Run anything you want to do directly:
```bash
ace "stage all changes"
ace "undo my last commit but keep changes"
ace "create feature branch named login"
```

### 📋 Command Reference

| Command | Shorthand | Description |
|---------|-----------|-------------|
| `ace add <files>` | `ace stage` | Stage files (`git add`) for commit. |
| `ace commit` | — | Generate a smart Conventional Commit message and commit. |
| `ace review` | — | AI code review of staged/unstaged changes. |
| `ace resolve` | — | AI-assisted interactive merge conflict resolution. |
| `ace changelog` | — | Generate markdown release notes since the last tag. |
| `ace stats` | — | Enhanced visual repo overview, extension counts, and lines altered. |
| `ace explain <cmd>` | — | Explain Git commands or concepts in plain English. |
| `ace undo` | — | Context-aware smart undo (analyzes Git state to safely revert last action). |
| `ace pr` | — | Generate a markdown Pull Request description comparing branches. |
| `ace search <query>` | — | Semantic search across repository commits. |
| `ace ignore <query>` | — | Generate and append rules to `.gitignore`. |
| `ace dash` | — | Launch the interactive terminal dashboard TUI. |
| `ace config` | — | View the active configuration settings. |

---

## 📁 Codebase Directory & File Functions

Here is the list of files in the project and what each one does:

### 📍 Core CLI & Setup
* **`pyproject.toml`**: Configures the project, entry points (`ace = ace.cli:app`), dependencies (`typer`, `rich`, `gitpython`, `langchain`), and build systems.
* **`ace/cli.py`**: The entrypoint of the Typer application. Defines all CLI commands, parses command line flags, and routes calls.

### ⚙️ Core Modules (`ace/core/`)
* **`ace/core/config.py`**: Manages reading, writing, and parsing the user's TOML settings file (`config.toml`).
* **`ace/core/git_ops.py`**: Wraps the GitPython library to perform programmatic Git commands (e.g. status, diff, log, commit, push).
* **`ace/core/safety.py`**: Classifies Git commands into safety levels (Safe, Moderate, Destructive) and guards against destructive operations.
* **`ace/core/context.py`**: Collects repository-wide details (branch, diffs, untracked files) to provide context for AI requests.

### 🧠 AI Engine (`ace/ai/`)
* **`ace/ai/llm_factory.py`**: Instantiates ChatNVIDIA (cloud) or ChatOllama (local) depending on configuration settings.
* **`ace/ai/intent_parser.py`**: Translates the user's natural language input into Git commands.
* **`ace/ai/commit_generator.py`**: Analyzes staged diffs and generates Conventional Commit messages.
* **`ace/ai/code_reviewer.py`**: Analyzes unstaged or staged diffs to locate bugs, style flaws, security issues, and rate code.
* **`ace/ai/conflict_resolver.py`**: Parses file-level merge conflicts and suggests correct merges.
* **`ace/ai/changelog_generator.py`**: Collates commit messages and formats release logs.
* **`ace/ai/history_analyzer.py`**: Runs semantic searches across log files and computes repository overview metrics.
* **`ace/ai/pr_drafter.py`**: Drafts Pull Request titles and bodies comparing branch changes.
* **`ace/ai/gitignore_generator.py`**: Generates `.gitignore` syntax templates.
* **`ace/ai/prompts/`**: Houses all prompt templates for the LLMs (intent, commit, review, conflict, explain, undo, pr, search, ignore).

### 🎨 User Interface (`ace/ui/`)
* **`ace/ui/display.py`**: Directs Rich panel printouts, warning/error panels, and load spinners.
* **`ace/ui/themes.py`**: Houses colors, styling, and markdown rules.
* **`ace/ui/prompts.py`**: Handles keyboard selection options (e.g., commit/review prompts).
* **`ace/ui/dashboard.py`**: Implements the interactive terminal dashboard (TUI) showing branch states and command routing menus.

### 🔧 Utilities (`ace/utils/`)
* **`ace/utils/json_utils.py`**: Extracts and parses clean JSON structures from Markdown code blocks.
* **`ace/utils/diff_parser.py`**: Splits unified diff files into per-file chunks.
* **`ace/utils/conflict_parser.py`**: Parses git conflict blocks inside file lines.
