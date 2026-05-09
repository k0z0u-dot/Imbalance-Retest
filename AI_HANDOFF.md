# AI Handoff

Last updated: 2026-05-09

## Latest Update

Purpose of this pass:

- Document the current ChatGPT-Codex semi-automated development loop.
- Add `docs/AGENT_WORKFLOW.md` describing roles, the Issue-to-Codex-to-push-to-review loop,
  Codex preflight/completion checklists, ChatGPT review checks, known GitHub tool
  limitations, and safety rules linking to `AGENT_POLICY.md`.
- Update `README.md` with a short workflow-doc link.
- Keep this as documentation only. No research logic, output schema, CI,
  automation, EA logic, live trading, order execution, position sizing,
  broker/exchange integration, portfolio logic, or risk-management behavior was
  changed.

Changed files:

- `docs/AGENT_WORKFLOW.md`
- `README.md`
- `AI_HANDOFF.md`

Implementation summary:

- Added `docs/AGENT_WORKFLOW.md`.
- Documented roles:
  - ChatGPT
  - Codex
  - GitHub
  - GitHub Actions
- Documented the standard loop:
  - Issue definition
  - Codex implementation
  - required local checks
  - `AI_HANDOFF.md` update
  - commit/push to `main`
  - ChatGPT review
- Added Codex preflight checklist.
- Added Codex completion checklist.
- Added ChatGPT review checklist.
- Documented known GitHub tool limitations:
  - Issue creation generally works.
  - Repository, file, and commit reads work.
  - Issue comments are unreliable.
  - Issue close or update actions may be intermittent.
  - If close/comment fails, completion is tracked by latest commit SHA plus
    `AI_HANDOFF.md`.
- Added safety rules and linked to `AGENT_POLICY.md`.
- README now links to `docs/AGENT_WORKFLOW.md` from the Agent Policy section.

Commands run:

- `git status --short`
  - Initial result: no output; worktree was clean.
- `Get-Content -Raw AGENT_POLICY.md`
  - Reviewed repository policy before editing.
- `Get-Content -Raw AI_HANDOFF.md`
  - Reviewed previous handoff state.
- `Get-Content -Raw README.md`
  - Reviewed existing README sections.
- `Get-ChildItem docs -File | Select-Object Name,Length`
  - Confirmed existing docs before adding `AGENT_WORKFLOW.md`.
- `python -m scripts.check_handoff`
  - Result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - First run result: timed out after 304 seconds.
- `Get-Process python -ErrorAction SilentlyContinue`
  - Result after timeout: no Python process output; no leftover pytest process.
- `git status --short`
  - Confirmed only `README.md` and `docs/AGENT_WORKFLOW.md` were changed before
    updating this handoff file.
- `python -m pytest`
  - Re-run with longer timeout: `48 passed in 367.10s (0:06:07)`.
- `python -m scripts.check_handoff`
  - Result after updating `AI_HANDOFF.md`: quick tests passed, handoff check
    PASS.
- `python -m pytest`
  - Result after updating `AI_HANDOFF.md`: `48 passed in 431.90s (0:07:11)`.

Test results:

```text
python -m scripts.check_handoff
36 passed, 12 deselected in 13.01s
handoff check: PASS

python -m pytest
timed out after 304 seconds

python -m pytest
48 passed in 367.10s (0:06:07)

python -m scripts.check_handoff
36 passed, 12 deselected in 59.33s
handoff check: PASS

python -m pytest
48 passed in 431.90s (0:07:11)
```

Current error / concern:

- Full pytest passed but took much longer than recent runs. The first run hit a
  304-second timeout; subsequent runs passed in about 6-7 minutes.
- This pass intentionally does not add tests because the requested change is
  documentation-only and existing checks passed.
- No CI, automation, research logic, schema, or trading behavior was changed.

Decisions made:

- Kept README update minimal.
- Put detailed workflow content in `docs/AGENT_WORKFLOW.md`, not README.
- Used ASCII `ChatGPT-Codex` / `Issue-to-Codex-to-push-to-review` wording in
  docs to keep file encoding simple.
- Did not add GitHub automation or Codex auto-start behavior.

What I want ChatGPT to do next:

1. Review whether `docs/AGENT_WORKFLOW.md` accurately reflects the intended
   handoff and review process.
2. Decide whether a future issue should add lightweight tests for workflow docs.
3. If full pytest remains slow, decide whether to split slower integration
   checks further.

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
- Agent workflow documentation: `docs/AGENT_WORKFLOW.md`.

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
- `docs/AGENT_WORKFLOW.md`: ChatGPT-Codex development loop
- `README.md`: quick start and common CLI examples
- `data/ofi_synthetic.csv`: sample synthetic CSV
