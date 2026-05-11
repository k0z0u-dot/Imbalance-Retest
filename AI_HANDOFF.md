# AI Handoff

Last updated: 2026-05-11

## Latest Update

Purpose of this pass:

- Fix pytest import stability so `scripts` can be imported from repo root in Codex Cloud, GitHub Actions, and local runs.
- Keep all research logic, OFI calculations, zone generation, retest evaluation, baselines, report outputs, and CI intent unchanged.

Changed files:

- `pyproject.toml`
- `AI_HANDOFF.md`

Implementation summary:

- Confirmed `[tool.pytest.ini_options]` existed in `pyproject.toml`.
- Changed pytest `pythonpath` from `["src"]` to `["src", "."]` so tests can import the repo-root `scripts` package reliably.
- No changes were made to research/business logic modules, outputs, or workflow semantics.

Commands run:

- `pytest -q`
- `python -m pytest -m "not integration"`
- `python -m scripts.check_handoff`
- `python -m pytest`

Test results:

```text
pytest -q
................................................                         [100%]

python -m pytest -m "not integration"
36 passed, 12 deselected in 56.59s

python -m scripts.check_handoff
36 passed, 12 deselected in 56.29s
handoff check: PASS

python -m pytest
48 passed in 73.86s (0:01:13)
```

Known unresolved points:

- None identified for this scoped fix.
- Full test runtime variability may still occur by environment, but all required commands passed in this run.

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

## Codex Cloud UI PR smoke test

- Selected environment name: `Imbalance-Retest`
- Attached repository: `k0z0u-dot/Imbalance-Retest`
- Whether origin is visible: `No` (no entries from `git remote -v`)
- Commands run:
  - `pwd`
  - `git status --short --branch`
  - `git remote -v`
  - `git log --oneline -5`
  - `pytest -q`
- Check result:
  - Environment and repository context confirmed.
  - Git checks completed.
  - `pytest -q` failed during test collection with `ModuleNotFoundError: No module named 'scripts'` in `tests/test_check_handoff.py`.
