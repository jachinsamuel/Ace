# Scope: E2E Testing Track

## Architecture
- The E2E tests must be opaque-box, meaning they execute the `ace` command as a subprocess (via `python -m ace` or the `ace` CLI command) and do not import or monkey-patch the application code.
- A local mock LLM server will run inside a pytest fixture or background thread during test execution. It will intercept `/v1/chat/completions` API calls and serve predefined JSON responses matching the test's prompt context.
- Env vars are injected: `ACE_PROVIDER=custom`, `CUSTOM_API_BASE=http://localhost:<port>/v1`, `CUSTOM_API_KEY=mock-key`, `CUSTOM_MODEL=mock-model`, and `HOME` points to a temporary folder to keep the developer's home directory pristine.
- All test runs create a temporary Git workspace, initialize a fresh Git repository, stage files, or set commits, run the CLI, and assert output, exit codes, and post-execution git repository state.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Test Infra & Mock Server | Implement base test runner, mock HTTP server fixture, and CLI subprocess wrapper. | None | IN_PROGRESS |
| 2 | Tier 1 - Feature Coverage | Happy path tests for 6 core features: NL planning, Commit, Config, Changelog, Doctor/Undo, PR. (30 tests) | 1 | PLANNED |
| 3 | Tier 2 - Boundary & Edge | Boundary value and error condition testing for the 6 core features. (30 tests) | 2 | PLANNED |
| 4 | Tier 3 - Cross-Feature | Pairwise combinations of key features (e.g. Config + NL, NL + Commit, Commit + Changelog, etc.). (6 tests) | 3 | PLANNED |
| 5 | Tier 4 - Workload Scenarios | Complex, multi-step real-world user scenarios (e.g. init repo -> stage -> commit -> changelog -> doctor). (5 tests) | 4 | PLANNED |
| 6 | Verification & Publication | Run E2E test suite, compile results, verify zero lint errors, write TEST_INFRA.md and publish TEST_READY.md. | 5 | PLANNED |

## Interface Contracts
- Subprocess invocation interface: `run_ace(args: List[str], stdin: Optional[bytes] = None, env: Optional[Dict[str, str]] = None) -> CompletedProcess`
- Mock LLM server: HTTP POST requests on `/v1/chat/completions` must receive JSON responses modeled after OpenAI API.
