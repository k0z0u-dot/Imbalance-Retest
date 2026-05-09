# AI Handoff

Last updated: 2026-05-09

## Latest Update

Purpose of this pass:

- Self-review the current repository state for the integration marker addition
  and quick handoff test command.
- Confirm that no research logic, CLI contract, output schema, or test
  expectations were unintentionally changed.
- Update this handoff file with the review result, commands, tests, and
  remaining concerns.

Self-review result:

- No code or documentation fix was required.
- `git diff` was empty at the start of this review, so there was no uncommitted
  implementation diff to amend.
- Current files were inspected directly:
  - `pyproject.toml` defines the `integration` marker correctly.
  - `README.md` and `docs/OFI_MEMORY_ZONE.md` document the quick command
    `python -m pytest -m "not integration"` consistently.
  - Tests marked with `pytest.mark.integration` are full-pipeline or
    integration-oriented tests: study, sweep, report, diagnostics, matched
    baseline, OOS split, synthetic smoke, or synthetic cycles.
  - Unit-level tests for features, zone generation, retests, swing baseline,
    quality evaluation, and zone strength remain unmarked.

Changed files in this pass:

- `AI_HANDOFF.md`

No source code, test logic, README content, docs content, CLI behavior, output
schema, or research logic was changed.

Commands run in this pass:

- `git diff --stat`
  - Result: no output.
- `git diff -- pyproject.toml README.md docs\OFI_MEMORY_ZONE.md`
  - Result: no output.
- `git diff -- tests`
  - Result: no output.
- `git diff -- AI_HANDOFF.md`
  - Result: no output before this handoff rewrite.
- `git status --short`
  - Result before this handoff rewrite: no output.
- `Get-Content -Raw pyproject.toml`
  - Confirmed pytest marker definition.
- `Select-String -Path tests\*.py -Pattern 'pytestmark|pytest.mark.integration|integration' -Context 1,2`
  - Confirmed integration marker placement.
- `Select-String -Path README.md,docs\OFI_MEMORY_ZONE.md -Pattern 'pytest|integration|not integration' -Context 1,2`
  - Confirmed documented test commands.
- `rg ...`
  - Failed with `Access is denied`; replaced with PowerShell
    `Select-String` checks.
- `Select-String -Path tests\*.py -Pattern 'pytestmark|def test_|run_study|run_sweep|summarize|generate_synthetic|generate_ofi|tmp_path|to_csv|baseline|walk_forward'`
  - Confirmed marker placement against integration-oriented test bodies.
- `Select-String -Path README.md,docs\OFI_MEMORY_ZONE.md,pyproject.toml -Pattern 'integration|not integration|pytest'`
  - Confirmed documentation and config consistency.
- `Get-Content -Raw tests\test_ofi_study.py`
  - Reviewed study output integration test.
- `Get-Content -Raw tests\test_ofi_sweep.py`
  - Reviewed sweep integration test.
- `python -m pytest -m "not integration"`
  - Result: `24 passed, 12 deselected in 11.67s`.
- `python -m pytest`
  - Result: `36 passed in 98.06s (0:01:38)`.
- `Get-Content -Raw AI_HANDOFF.md`
  - Found stale/mojibake update text and replaced it with this readable record.
- `git status --short`
  - Result after this handoff rewrite: ` M AI_HANDOFF.md`.

Test result:

```text
python -m pytest -m "not integration"
24 passed, 12 deselected in 11.67s

python -m pytest
36 passed in 98.06s (0:01:38)
```

Current error / concern:

- The only current working-tree change from this pass should be
  `AI_HANDOFF.md`.
- `rg` is not usable in this shell because `rg.exe` returns `Access is denied`.
  Use PowerShell `Select-String` if this persists.
- Full pytest still takes about 1.5 minutes on this machine; the quick
  non-integration command is suitable for handoff checks.
- The `integration` marker is intentionally broad. If the test suite grows,
  consider adding narrower markers such as `sweep`, `report`, or `slow`.
- The project version in `pyproject.toml` is still `0.1.0` despite iterative
  v0.2-v0.4 style research additions.

Decisions made:

- Treat the existing marker split as safe and consistent.
- Do not modify research logic, tests, CLI behavior, outputs, README, or docs.
- Rewrite only `AI_HANDOFF.md` because the previous top update contained
  unreadable mojibake and the user requested a fresh self-review record.

What I want ChatGPT to do next:

1. Decide whether the `AI_HANDOFF.md` rewrite should be committed together with
   the existing marker/docs work or as a separate handoff-only commit.
2. If test runtime grows, consider splitting `integration` into more specific
   markers.
3. Consider whether `pyproject.toml` version metadata should reflect the
   current research module maturity.

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

Key entry points:

- `python -m scripts.run_ofi_zone_study`
- `python -m scripts.run_ofi_zone_sweep`
- `python -m scripts.generate_ofi_synthetic_data`
- `python -m scripts.summarize_ofi_experiment`

Repository layout:

- `src/ofi_memory_zones/`: core package
- `scripts/`: CLI entry points
- `tests/`: pytest coverage
- `docs/OFI_MEMORY_ZONE.md`: detailed design and usage documentation
- `README.md`: quick start and common CLI examples
- `configs/ofi_synthetic_sanity.json`: synthetic sanity config
- `data/ofi_synthetic.csv`: sample synthetic CSV
