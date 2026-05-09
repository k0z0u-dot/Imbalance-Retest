# AI Handoff

Last updated: 2026-05-09

## Latest Update

Purpose of this pass:

- Implement GitHub Issue #5:
  [Codex Task: Add agent policy for safe semi-automated development loop](https://github.com/k0z0u-dot/Imbalance-Retest/issues/5).
- Add `AGENT_POLICY.md` so ChatGPT, Codex, and future review/automation agents
  share the same repository constraints and workflow.
- Keep this as a policy/documentation pass. No research logic, output schema,
  CI automation, Codex auto-triggering, EA logic, live trading, order execution,
  position sizing, broker/exchange integration, portfolio logic, or risk
  management was changed.

Changed files:

- `AGENT_POLICY.md`
- `tests/test_agent_policy.py`
- `README.md`
- `AI_HANDOFF.md`

Implementation summary:

- Added root-level `AGENT_POLICY.md`.
- Policy sections:
  - Repository Purpose
  - Hard Constraints
  - Required Workflow For Codex Tasks
  - Required Checks
  - Review Criteria
  - Failure Handling
- The policy states that the repository is an observational OFI Memory Zone /
  Imbalance-Retest research toolkit and explicitly not an EA, live trading bot,
  execution system, position sizing system, or broker/exchange integration
  project.
- The policy requires future agents to avoid changing these unless a GitHub
  Issue explicitly asks for it:
  - OFI feature construction semantics
  - zone generation semantics
  - retest classification semantics
  - target/stop first-touch outcome logic
  - baseline definitions
  - output schemas
  - quality-gate interpretation
- Added a small test to verify `AGENT_POLICY.md` exists and contains the
  required sections/constraints.
- README now briefly points agents to `AGENT_POLICY.md`.

Commands run:

- Opened GitHub Issue #5 in the browser and confirmed scope, constraints,
  required sections, tests, and done criteria.
- `git status --short`
  - Initial result: no output; worktree was clean.
- `git branch --show-current`
  - Result: `main`.
- `Get-Content -Raw AI_HANDOFF.md`
  - Reviewed previous handoff state.
- `Get-Content -Raw README.md`
  - Reviewed existing docs structure.
- `Get-ChildItem tests -File | Select-Object Name,Length`
  - Reviewed test layout before adding the policy test.
- `python -m pytest tests\test_agent_policy.py`
  - First result: failed because one asserted phrase crossed a line break in
    `AGENT_POLICY.md`.
- Updated `AGENT_POLICY.md` to keep the repository-purpose phrase contiguous.
- `python -m pytest tests\test_agent_policy.py`
  - Result: `1 passed in 0.28s`.
- `python -m scripts.check_handoff`
  - Result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - Result: `48 passed in 118.26s (0:01:58)`.
- `python -m scripts.check_handoff`
  - Result after updating `AI_HANDOFF.md`: quick tests passed, handoff check
    PASS.
- `python -m pytest`
  - Result after updating `AI_HANDOFF.md`: `48 passed in 107.70s (0:01:47)`.
- `git diff --check`
  - Result: passed; only line-ending warnings were printed.
- `git status --short`
  - Pre-commit result:

```text
 M AI_HANDOFF.md
 M README.md
?? AGENT_POLICY.md
?? tests/test_agent_policy.py
```

Test results:

```text
python -m pytest tests\test_agent_policy.py
1 passed in 0.28s

python -m scripts.check_handoff
36 passed, 12 deselected in 17.31s
handoff check: PASS

python -m pytest
48 passed in 118.26s (0:01:58)

python -m scripts.check_handoff
36 passed, 12 deselected in 11.41s
handoff check: PASS

python -m pytest
48 passed in 107.70s (0:01:47)
```

Current error / concern:

- The first policy test run failed due to a line-break-sensitive phrase check.
  The policy document was adjusted without changing scope or meaning, and the
  test then passed.
- Full pytest remains around 2 minutes locally.
- This pass intentionally does not add automation that triggers Codex or edits
  code automatically.
- No CI workflow changes were made.
- No research/trading logic was changed.

Decisions made:

- Added a policy-file existence/content test because Issue #5 allowed a small
  policy test if useful.
- Kept README update to one short section.
- Did not modify `scripts.check_handoff`, CI, research modules, output schemas,
  or config defaults.

What I want ChatGPT to do next:

1. Review whether `AGENT_POLICY.md` is strict enough for future review agents.
2. Decide whether future issues should require agents to quote or summarize the
   policy before implementation.
3. After push, confirm GitHub shows the latest commit and decide whether to
   close Issue #5.

## Current Goal

This repository is an observational research toolkit for OFI Memory Zone /
Imbalance-Retest Zone studies. Its purpose is to detect price zones derived from
order-flow imbalance, evaluate retest behavior, compare OFI zones against
baselines, and generate experiment-level reports.

This is not an EA, execution bot, order-entry system, or position-management
system.

## Current State

Implemented major features:

- OFI feature construction from taker buy/sell volume, buy/sell proxy,
  side+size raw trades, or signed_volume proxy.
- Explicit error behavior when no usable flow source exists.
- Rolling imbalance z-score, robust imbalance z-score, volume z-score, and ATR.
- Four OFI zone types:
  - `initiative_support`
  - `absorption_support`
  - `initiative_resistance`
  - `absorption_resistance`
- Leakage control via `available_from` after `reaction_horizon_bars`.
- Retest detection, confirmation classification, first-touch target/stop
  outcome evaluation, MFE/MAE, and after-cost return.
- Zone strength and beta posterior success estimates.
- Baseline comparisons:
  - `random_zone`
  - `time_matched_random_zone`
  - `price_near_random_zone`
  - `swing_sr_zone`
  - `volume_profile_zone`
- Multiple random baseline trials with `baseline_trials.csv` and
  `baseline_summary.csv`.
- Train/test and walk-forward validation outputs.
- Data diagnostics output.
- Experiment report generation and quality gate verdicts.
- Sweep runner and sweep robustness report.
- Synthetic data generator, including multi-cycle synthetic datasets for
  quality-gate sanity checks.
- Pytest `integration` marker for slower full-pipeline tests.
- Handoff sanity command: `python -m scripts.check_handoff`.
- Experiment batch runner: `python -m scripts.run_ofi_experiment_batch`.
- Reusable protocol configs and `docs/OFI_EXPERIMENT_PROTOCOL.md`.
- GitHub Actions CI workflow for handoff, full tests, and batch smoke.
- Agent development policy: `AGENT_POLICY.md`.

Key entry points:

- `python -m scripts.run_ofi_zone_study`
- `python -m scripts.run_ofi_zone_sweep`
- `python -m scripts.generate_ofi_synthetic_data`
- `python -m scripts.summarize_ofi_experiment`
- `python -m scripts.check_handoff`
- `python -m scripts.run_ofi_experiment_batch`

Repository layout:

- `AGENT_POLICY.md`: repository rules for ChatGPT/Codex/review agents
- `.github/workflows/ci.yml`: GitHub Actions CI
- `src/ofi_memory_zones/`: core package
- `scripts/`: CLI entry points and handoff/batch scripts
- `tests/`: pytest coverage
- `configs/`: reusable study configs and sweep grid
- `docs/OFI_MEMORY_ZONE.md`: detailed design and usage documentation
- `docs/OFI_EXPERIMENT_PROTOCOL.md`: repeatable validation protocol
- `README.md`: quick start and common CLI examples
- `data/ofi_synthetic.csv`: sample synthetic CSV
