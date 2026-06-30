# Handoff Report: Ace Codebase & Test Exploration

## 1. Observation

### CLI Features and Subcommands
The CLI entry point is defined in `pyproject.toml` (lines 29-30) and `ace/cli.py` (lines 64-70):
```toml
[project.scripts]
ace = "ace.cli:app"
```
```python
app = typer.Typer(
    name="ace",
    help="Ace — AI-Powered Git Copilot. Talk to Git in plain English.",
    no_args_is_help=False,
    cls=NaturalLanguageGroup,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
```

The CLI implements the following subcommands in `ace/cli.py`:
* **Natural Language Mode**: Invoked when no subcommands are matched. It parses the intent via LLM (`IntentParser`), generates Git commands, assesses safety via `SafetyChecker.analyze_command`, and executes them. It is supported by the `NaturalLanguageGroup` (lines 37-60) and `main` callback (lines 80-235).
* **`commit`** (line 236): Generates a commit message using `CommitGenerator` based on staged changes and commits them. Supports `--offline`, `--format` / `-f`, and `--prepare`. Offers post-commit remote push and setting upstream.
* **`setup`** (line 414): Interactive step-by-step configuration wizard.
* **`config`** (line 519): Displays active configuration sections (`AI`, `Commit`, `Review`, `Safety`) and their settings in a Rich table.
* **`review`** (line 558): Performs AI-powered code reviews. Supports `file` argument, `--all` / `-a`, `--branch` / `-b`, `--offline`, and `--strict`.
* **`resolve`** (line 642): AI-assisted interactive merge conflict resolution.
* **`changelog`** (line 746): Compiles a Markdown changelog. Supports `--from`, `--to`, `--output` / `-o`, and `--offline`.
* **`stats`** (line 789): Aggregates and visualizes contributor commits, additions/deletions, extension distribution, and activity timelines.
* **`doctor`** (line 893): Repository diagnostics and AI-assisted recovery recommendation.
* **`explain`** (line 1004): Explains Git concepts or commands.
* **`undo`** (line 1037): Reverts the last action using reflog analysis and safety checks.
* **`dash`** (line 1161): Launches the interactive terminal dashboard (TUI).
* **`pr`** (line 1174): Drafts pull request descriptions. Supports `--base` / `-b`, `--output` / `-o`, and `--offline`.
* **`search`** (line 1238): Semantic commit search with checkout options.
* **`ignore`** (line 1327): Generates `.gitignore` rules.
* **`add` / `stage`** (line 1444, line 1465): Stages changes in the index.
* **`squash`** (line 1471): Evaluates commits and performs AI-guided history cleanup/rebases.
* **`hook`** (line 1577): Installs/uninstalls `pre-commit` and `prepare-commit-msg` hooks.

### Installation and Invocation
* Installed as a global CLI executable `ace` mapping to `ace.cli:app` (via `pyproject.toml`).
* Can be run directly via module invocation: `python -m ace` (via `ace/__main__.py`).
* Configured using `~/.ace/config.toml` via `get_config()` and `save_config()` in `ace/core/config.py`.
* Environment variable overrides are supported in `ace/core/config.py` (lines 101-153):
  * `ACE_PROVIDER` overrides active AI provider.
  * API keys and endpoints: `NVIDIA_API_KEY`, `NVIDIA_MODEL`, `OLLAMA_MODEL`, `OLLAMA_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `CUSTOM_API_KEY`, `CUSTOM_API_BASE`, `CUSTOM_MODEL`.

### Unit/Integration Test Structure
* Located in `tests/`.
* Run via standard `pytest` commands. Execution command used: `.venv\Scripts\pytest -v`.
* All 52 tests passed:
  ```text
  ============================= 52 passed in 55.98s =============================
  ```
* Structurally, the tests use:
  * `conftest.py`: Creates a temporary Git repository using `gitpython` and configures a mock user:
    ```python
    @pytest.fixture
    def temp_git_repo():
        # ...
        repo = git.Repo.init(repo_path)
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Test User")
            cw.set_value("user", "email", "test@example.com")
        yield repo_path, repo
    ```
  * Unit/Integration level mocking: Python's `unittest.mock.patch` is used to mock the `get_llm` factory or direct `GitOps` class calls (e.g., `tests/test_code_reviewer.py`, `tests/test_undo.py`).
  * No end-to-end (E2E) testing module is currently implemented to verify CLI subprocess execution and exit code assertions without internal monkey-patching.

---

## 2. Logic Chain
1. *Observation 1*: The application parses CLI options using `typer`/`click` and reads config values using `get_config()`, which has built-in environment variable overrides for API keys, providers, and URLs.
2. *Observation 2*: The application uses LangChain model classes fetched via `get_llm()`. If `custom` provider is selected, it uses `langchain_openai.ChatOpenAI` initialized with `openai_api_base=config.ai.custom_api_base` and `openai_api_key=config.ai.custom_api_key`.
3. *Observation 3*: Existing tests mock `get_llm` at the Python class/module level (e.g. `test_code_reviewer.py:49` with `patch("ace.ai.code_reviewer.get_llm", return_value=mock_llm)`). This prevents them from qualifying as opaque-box E2E tests, because they rely on internal structure modification.
4. *Conclusion*: By combining Observation 1 and 2, we can configure a running `ace` CLI process to redirect its AI HTTP requests to a local mock server using environment variable overrides. This facilitates completely opaque-box E2E tests without source code patching.

---

## 3. Caveats
* Interactive prompts (such as TUI `ace dash` and interactive loops in `ace commit` / `ace resolve`) require robust `stdin` piping to send virtual keypresses. Terminal mouse events and complex visual rendering (from `rich` and `click.getchar`) were not fully explored under different terminal emulations but will require standard POSIX/Windows subprocess pipes.
* Local test execution was done on Windows using `.venv\Scripts\pytest -v`. The paths are Windows-based, but `pyproject.toml` asserts OS independence.

---

## 4. Conclusion
We have verified that Ace implements a rich suite of AI-powered Git helpers. The application is run via standard CLI scripts or `python -m ace` and retrieves configuration from `~/.ace/config.toml` (with environment variables taking precedence). Existing tests successfully cover unit logic, mock-heavy class integrations, and gitoperations, but lack E2E coverage.

### Recommended Opaque-Box E2E Testing Strategy
We recommend adding an E2E test module (`tests/e2e/`) that implements the following strategy:
1. **Isolated Workspace**: Initialize a fresh Git repository for each test inside a temporary directory.
2. **Local Mock LLM Server**: Spin up a simple HTTP server (using `http.server.HTTPServer` or `FastAPI` inside a pytest fixture) listening on a local port. The mock server will listen for requests to `/v1/chat/completions` (OpenAI format) and return pre-defined mock JSON responses based on the received prompts (e.g. returning simulated command plans for intent parsing or conventional commits for staged changes).
3. **Subprocess Invocation**: Run the CLI using python's `subprocess.Popen` or `subprocess.run`:
   * Execute: `python -m ace.cli <command> <options>` or `python -m ace <command>`.
   * Inject Environment Variables:
     * `ACE_PROVIDER=custom`
     * `CUSTOM_API_BASE=http://localhost:<mock_port>/v1`
     * `CUSTOM_API_KEY=mock-key`
     * `CUSTOM_MODEL=mock-model`
     * `HOME=<temporary_home_dir>` (to avoid writing or reading the developer's real `~/.ace/config.toml`).
4. **Behavior Verification**:
   * **Exit Codes**: Assert `result.returncode == 0` (or the expected error code).
   * **Stdout/Stderr**: Search for specific UI strings (e.g. "🧠 Understanding request", "Plan executed successfully!").
   * **Git State**: Query the local Git repository status or log after execution using `gitpython` or shell commands to confirm that files were staged, commits created, or branches created as intended.
   * **Interactive Prompts**: Write inputs to `stdin` (e.g., `b"\n"` to accept options or `b"y\n"` to confirm plans).

---

## 5. Verification Method
1. To run all unit and integration tests, run from the root:
   ```powershell
   .venv\Scripts\pytest -v
   ```
2. Verify that configuration environment variables are correctly loaded by running:
   ```powershell
   $env:ACE_PROVIDER="custom"
   $env:CUSTOM_API_BASE="http://localhost:12345/v1"
   python -m ace config
   ```
   Inspect the active configuration output table to verify "AI - Provider" is "custom" and "AI - Custom API Base URL" is "http://localhost:12345/v1".
