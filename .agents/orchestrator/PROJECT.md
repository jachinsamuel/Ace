# Project: Ace Git Copilot Optimization

## Architecture
Ace is an AI-powered Git Copilot CLI application using Typer, Click, and Rich for the user interface, GitPython for Git operations, and LangChain for LLM API integration.
- **Entry point**: `ace.cli` (specifically `ace.cli:app`).
- **CLI Framework**: Typer/Click command groups and subcommands.
- **AI Modules**: `ace.ai.*` handles LLM interactions, prompts, factory logic, and generators (commit message, PR draft, changelog, reviews, semantic search, etc.).
- **Core logic**: `ace.core.*` handles Git interface operations, configuration management, diagnostics, and safety analyzer.
- **UI & Display**: `ace.ui.*` houses Rich-based UI styling, dashboards, banners, prompts, and themes.

## Code Layout
- `ace/cli.py` - Main Typer application and subcommand definitions.
- `ace/core/` - Core utility libraries: configuration (`config.py`), Git integration (`git_ops.py`), safety policies (`safety.py`).
- `ace/ai/` - LLM interaction logic: factory (`llm_factory.py`), parser (`intent_parser.py`), review (`code_reviewer.py`), commits (`commit_generator.py`).
- `ace/ui/` - Layout and user input elements: themes, static/dynamic banners, prompts, dashboard.
- `tests/` - Unit and integration tests mapping to respective modules.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | E2E Testing Track | Define feature requirements and implement the Category-Partition, BVA, Pairwise E2E test suite. Output: `TEST_READY.md`. | None | IN_PROGRESS (Conv ID: 75bd9c52-a2f3-416f-a979-0d0aaca1aa4f) |
| M2 | Startup & Import Optimization | Refactor `ace/cli.py` and other modules to lazy-load heavy imports (`langchain`, `llm_factory`, `commit_generator`, `intent_parser`, etc.). Ensure `ace --help` executes in <250ms. | M1 | IN_PROGRESS (Conv ID: ec67676c-109f-462d-a601-8f8b26d70488) |
| M3 | Codebase Cleanliness & Emoji Removal | Refactor codebase to remove unused/redundant modules and helpers. Audit and remove cringy/verbose emojis from UI prompts, logs, and banners, replacing them with professional typography. | M1 | IN_PROGRESS (Conv ID: ec67676c-109f-462d-a601-8f8b26d70488) |
| M4 | Test Suite Optimization | Profile, optimize fixtures and mocks in `tests/` to run all 52 tests in <15s without flakiness. | M1, M2 | IN_PROGRESS (Conv ID: ec67676c-109f-462d-a601-8f8b26d70488) |
| M5 | Final Verification & Hardening | Run dual-track E2E checks, pass 100% test suite, and run Phase 2 (Adversarial Coverage Hardening). | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### `ace.cli` ↔ `ace.ai.llm_factory`
- `get_llm(offline_override: bool = False) -> BaseChatModel`: Lazy loaded to prevent eager import of LangChain.

### `ace.cli` ↔ `ace.ai.intent_parser`
- `IntentParser(git_ops: GitOps)`: Parses natural language intent to Git command plans. Eager imports of langchain deferred to method execution.

### `ace.cli` ↔ `ace.ai.commit_generator`
- `CommitGenerator(git_ops: GitOps)`: Generates smart commit messages. Deferred eager imports of langchain.
