# Ace AI Git Copilot E2E Test Infrastructure

This document describes the End-to-End (E2E) testing infrastructure implemented for Ace.

## Architecture & Design

The E2E test suite operates entirely in an **opaque-box** manner:
- The tests interact with the system solely through the Command Line Interface (CLI) subprocess and the file system (Git repository state).
- No application modules or internal logic are directly imported or monkey-patched during test execution.
- System configurations and database states are isolated on a per-test basis.

### 1. Mock LLM HTTP Server
A lightweight, OpenAI-compatible mock LLM server is run in a background thread during test execution:
- It listens on a dynamic local port (`http://127.0.0.1:<port>`).
- It intercepts POST requests to `/v1/chat/completions`.
- By parsing the payload's system prompts and user messages, it matches queries and context to predefined, schema-compliant JSON responses for all core features (NL Planning, Commits, PR Drafting, Diagnostics, Changelogs, Undo).

### 2. Isolated Workspace Fixture (`git_workspace`)
To guarantee that the host machine's configuration and git repositories remain pristine, the `git_workspace` fixture:
- Allocates a fresh temporary directory for each test run.
- Initializes a new Git repository within that directory and configures dummy user details (`user.name`, `user.email`).
- Overrides the `HOME` and `USERPROFILE` environment variables to point to a temporary path, redirecting all configuration reads and writes (e.g. `~/.ace/config.toml`) to the test sandbox.
- Sets `GIT_CEILING_DIRECTORIES` to prevent git operations from traversing upward and affecting parent projects.

### 3. Non-Blocking Subprocess Terminal Prompts
Standard terminal prompts that wait for keypresses (such as Click's `getchar`) bypass typical piped stdin buffers on Windows by querying console hardware directly (`msvcrt.getch()`). To make the CLI testable and non-blocking in subprocesses:
- The test runner invokes python with a wrapper script:
  `python -c "import sys, click; click.getchar = lambda: sys.stdin.read(1); from ace.cli import app; app()"`
- This monkeypatches `click.getchar` inside the subprocess context to read from `sys.stdin` rather than the console keyboard buffer, allowing reliable test execution using piped input streams (e.g. sending `\n` to accept plans or `s\n` to skip actions).

## Test Suite Tiers

- **Tier 1 (Happy Paths)**: 30 test cases covering the standard successful paths of all 6 core features.
- **Tier 2 (Boundaries & Edge Cases)**: 30 test cases testing error boundaries, invalid parameters, missing credentials, empty diffs, and detached HEAD states.
- **Tier 3 (Pairwise Combinations)**: 6 test cases verifying integrated flows between two different features (e.g., config setup affecting commit format, commits populating changelogs, doctor detecting changes resolved by undo).
- **Tier 4 (Real-World Workloads)**: 5 complex multi-step workload scenarios simulating daily user activities (e.g. feature branch lifecycles, hotfix operations, rebase conflict recoveries, and release doc compilations).
