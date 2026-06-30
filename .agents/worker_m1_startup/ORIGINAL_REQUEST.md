## 2026-06-30T10:05:17Z

You are a worker subagent with ID worker_m1_startup.
Your working directory is `d:\Projects\Ace\.agents\worker_m1_startup\`.
Your mission is to implement Milestone 1: Startup Optimization for Ace Git Copilot.

Read the initial analysis report at `d:\Projects\Ace\.agents\implementation_track\explorer_initial_report.md` for background.

Your specific tasks:
1. Optimize startup latency. In `ace/cli.py`, move heavy imports (such as `GitOps`, `get_llm`, `CommitGenerator`, `IntentParser`, `SafetyChecker`, and any heavy UI prompt modules) from the top-level to local function/method level inside CLI commands.
2. Verify that running `ace --help` or `python -m ace --help` works correctly and does not eagerly import heavy packages.
3. Profile the import time or run times of `ace --help` to ensure it executes in <250ms.
4. Run `ruff check ace` and ensure 0 warnings/errors.
5. Run `pytest` to make sure unit tests still pass.
6. Write a detailed completion handoff to `d:\Projects\Ace\.agents\worker_m1_startup\handoff.md`.

MANDATORY INTEGRITY WARNING — include this verbatim in the Worker's dispatch prompt:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
