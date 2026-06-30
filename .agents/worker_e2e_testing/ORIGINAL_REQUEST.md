## 2026-06-30T15:28:03Z
You are a worker agent.
Your working directory is d:\Projects\Ace\.agents\worker_e2e_testing.
Your task is to implement a comprehensive, opaque-box, requirement-driven E2E test suite under tests/e2e/.

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT
> hardcode test results, create dummy/facade implementations, or
> circumvent the intended task. A Forensic Auditor will independently
> verify your work. Integrity violations WILL be detected and your
> work WILL be rejected.

### Instructions:
1. Create `tests/e2e/` folder.
2. In `tests/e2e/conftest.py`, implement:
   - A background thread mock LLM HTTP server listening on a dynamic port that handles POST to `/v1/chat/completions` (OpenAI format). It should inspect request content to decide which pre-defined JSON response to return.
   - A `git_workspace` pytest fixture that initializes a fresh Git repository in a temporary directory, configures git name and email, and returns a helper to invoke the `ace` CLI command.
   - The CLI runner must invoke `python -m ace.cli` or `python -m ace` as a subprocess, injecting environment variables:
     - `ACE_PROVIDER=custom`
     - `CUSTOM_API_BASE=http://localhost:<mock_port>/v1`
     - `CUSTOM_API_KEY=mock-key`
     - `CUSTOM_MODEL=mock-model`
     - `HOME=<temp_home_path>` (ensure a clean home directory isolated from the user's host config)
3. Implement 6 features to test:
   - Feature 1: NL Planner (Natural Language mode)
   - Feature 2: Commit Generator (`ace commit`)
   - Feature 3: Config Wizard / Display (`ace config` / `ace setup`)
   - Feature 4: Changelog Generator (`ace changelog`)
   - Feature 5: PR Drafter (`ace pr`)
   - Feature 6: Diagnostics & Recovery (`ace doctor` & `ace undo`)
4. Implement the following test files under `tests/e2e/`:
   - `test_tier1_features.py`: Happy path tests for all 6 features (5 tests per feature = 30 tests).
   - `test_tier2_boundaries.py`: Boundary and edge cases for all 6 features (5 tests per feature = 30 tests).
   - `test_tier3_combinations.py`: Pairwise combination tests between features (6 tests).
   - `test_tier4_workloads.py`: Complex real-world workload scenarios (5 tests).
   Ensure all tests use assertions on exit codes, stdout/stderr strings, and post-execution git repository state, communicating only through the CLI subprocess interface and Git.
5. Create `d:\Projects\Ace\TEST_INFRA.md` at the project root using the project template for E2E Test Infra.
6. Create `d:\Projects\Ace\TEST_READY.md` at the project root using the project template for E2E Test Suite Ready.
7. Run the newly created test suite via `.venv\Scripts\pytest -v tests/e2e/` and confirm that all 71 tests compile and pass successfully.

Write a detailed handoff report in handoff.md in your working directory summarizing:
- Files created
- Total test cases implemented per tier
- Command used to run tests and verification results (include pytest output)
- File paths of TEST_INFRA.md and TEST_READY.md.
Notify the parent orchestrator when complete.
