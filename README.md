# Ace — AI-Powered Git Copilot

```text
 █████╗   ██████╗ ███████╗
██╔══██╗ ██╔════╝ ██╔════╝
███████║ ██║      █████╗  
██╔══██║ ██║      ██╔══╝  
██║  ██║ ╚██████╗ ███████╗
╚═╝  ╚═╝  ╚═════╝ ╚══════╝
```

[![PyPI Version](https://img.shields.io/pypi/v/ace-git-copilot.svg)](https://pypi.org/project/ace-git-copilot/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/ace-git-copilot.svg)](https://pypi.org/project/ace-git-copilot/)
[![Python Version](https://img.shields.io/pypi/pyversions/ace-git-copilot.svg)](https://pypi.org/project/ace-git-copilot/)
[![License: MIT](https://img.shields.io/github/license/jachinsamuel/Ace.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/jachinsamuel/Ace.svg)](https://github.com/jachinsamuel/Ace/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jachinsamuel/Ace.svg)](https://github.com/jachinsamuel/Ace/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/jachinsamuel/Ace.svg)](https://github.com/jachinsamuel/Ace/issues)

Ace is an intelligent command-line tool that brings AI assistance directly to your Git workflow. Talk to Git in plain English — Ace translates your intents into Git commands, explains what it is doing, and runs them safely. It also features a fully interactive terminal user interface (TUI) dashboard to help manage your repositories with ease.

---

## Features

*   **Natural Language Git Commands**: Translate commands like "undo my last commit but keep changes" or "create a branch login-page" into clean, standard Git actions.
*   **AI-Powered Commits**: Analyzes staged diffs and generates Conventional Commit messages automatically.
*   **Automated Code Review**: Rates code quality and points out bugs, security flaws, or styling issues inside staged or unstaged diffs.
*   **Merge Conflict Resolution**: Interactively walks you through conflict blocks and suggests correct merges.
*   **Rich Repo Stats and Changelogs**: Instantly computes repository statistics (commits, additions, deletions, file counts) and generates markdown release notes since the last tag.
*   **Semantic Commit Search**: Search commits by natural language queries (e.g. "fixed the authorization bug") instead of matching literal strings.
*   **Interactive TUI Dashboard**: Run `ace dash` to launch a terminal interface showing current status, branch info, commit charts, and interactive menus.
*   **Safety Features**: Classifies actions into safe, moderate, or destructive levels, and requests confirmation before running destructive operations.

---

## Installation

For Python command-line applications like Ace, it is highly recommended to install using **pipx**. pipx automatically installs the application in an isolated environment and manages your system PATH so the executable works globally without conflict.

### Option A: Install via pipx (Recommended)
1. Install pipx and configure your system PATH (only needs to be done once):
   ```bash
   pip install pipx
   pipx ensurepath
   ```
   *(Note: If `pipx ensurepath` modified your path, close your current terminal window and open a new one to apply).*

2. Install Ace:
   ```bash
   pipx install ace-git-copilot
   ```

3. Run it directly:
   ```bash
   ace dash
   ```

### Option B: Install via standard pip (Alternative)
You can also install Ace globally using standard pip:
```bash
pip install ace-git-copilot
```
*Note: If you run into a `command not found` error, you can bypass your system PATH and run the tool directly through Python module execution:*
```bash
python -m ace dash
```

---

## Configuration and Setup

Run the built-in configuration wizard to select your AI model provider:
```bash
ace setup
```
Ace saves your configuration file to `~/.ace/config.toml`. It supports the following AI model providers:

### 1. NVIDIA NIM API (Cloud)
Uses cloud-hosted high-performance models.
* You will need an NVIDIA developer API key. Get one for free at [NVIDIA build](https://build.nvidia.com/).
* Default model: `meta/llama-3.3-70b-instruct`

### 2. Ollama (Local Models)
For a 100% private, offline, and free experience.
* Ensure [Ollama](https://ollama.com/) is installed and running on your system.
* Default model: `qwen2.5-coder:7b`
* If the selected model is not downloaded yet, Ace will automatically pull it for you during setup.

### 3. OpenAI
Uses OpenAI GPT models.
* You will need an OpenAI API key.
* Default model: `gpt-4o-mini`

### 4. Anthropic
Uses Anthropic Claude models.
* You will need an Anthropic API key.
* Default model: `claude-3-5-sonnet-latest`

### 5. Custom OpenAI-Compatible
Allows using any custom endpoint that supports the OpenAI API schema (e.g. Groq, OpenRouter, Together AI).
* You will need the provider's API key and custom API base URL (e.g. `https://api.groq.com/openai/v1`).
* Default model: `custom-model`

---

## Usage

### Natural Language Mode
Run natural language requests directly in quotes:
```bash
ace "stage everything and commit with a message about authentication"
ace "undo my last commit but keep the files"
ace "switch to a new branch called design-updates"
```

### Command-Line Toolchain
Ace has dedicated subcommands for specific tasks. Here is the complete command list:

| Command | Shorthand | Description |
|:---|:---|:---|
| `ace setup` | — | Launch the initial setup wizard to configure AI models. |
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
| `ace dash` | — | Launch the interactive repository management console (TUI). |
| `ace config` | — | Print out active configuration settings. |
| `ace help` | — | Show user guide and help information on how to use Ace. |

---

## Interactive Terminal Dashboard (TUI)

Launch the repository dashboard by running:
```bash
ace dash
```

The dashboard features:
*   A start-up logo.
*   Active branch info, tracking status, and repository charts.
*   Interactive shortcuts for one-key commits, reviews, undos, and configuration management.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
