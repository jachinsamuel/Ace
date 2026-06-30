# Project: Ace Git Copilot Optimization

## Architecture
- **CLI layer**: `ace/cli.py` and `ace/__main__.py` (built with Typer).
- **AI/LLM layer**: `ace/ai/llm_factory.py` (LangChain wrappers) and individual generators under `ace/ai/`.
- **Git Operations**: `ace/core/git_ops.py` (GitPython wrappers).
- **UI/UX layer**: `ace/ui/` (animations, prompts, themes, dashboards).
- **Tests**: `tests/` directory containing unit tests.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Startup Optimization | Lazy-loading heavy imports (LangChain, LLM factory, generators) to ensure `ace --help` executes in <250ms. | None | IN_PROGRESS (worker: f78e94da) |
| 2 | Codebase Refactoring & UI/UX Styling | Eliminate unused modules/imports, clean up cringy/verbose emojis, replace with professional typography, disable blocking animation. | M1 | PLANNED |
| 3 | Test Suite Speed & Reliability | Profile tests, configure pytest options, mock heavy modules globally, resolve Ollama health check blocking to run tests in <15s. | M1 | PLANNED |
| 4 | E2E and Adversarial Hardening | Phase 1: Pass 100% of E2E tests (Tiers 1-4). Phase 2: Adversarial Coverage Hardening (Tier 5). | M1, M2, M3 | PLANNED |

## Interface Contracts
- **CLI Commands**: Subcommand signatures in `ace/cli.py` must remain backwards-compatible.
- **Factory Functions**: `ace.ai.llm_factory.get_llm` and other core factory interfaces must not change signatures, only internal execution paths.
- **GitOps Interface**: `ace.core.git_ops.GitOps` and its error handling.
