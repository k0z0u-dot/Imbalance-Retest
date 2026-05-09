# AI Handoff

Last updated: 2026-05-09

## Latest Update

Purpose of this pass:

- Implement GitHub Issue #3:
  [Codex Task: Add CI workflow for handoff and tests](https://github.com/k0z0u-dot/Imbalance-Retest/issues/3).
- Add a GitHub Actions CI workflow that runs the repository handoff check and
  the full pytest suite on pushes to `main` and pull requests.
- Include the optional batch runner smoke step because the local command is
  deterministic and completed successfully.
- Keep this pass focused on CI and minimal docs. No OFI research logic,
  config-tuning behavior, output schemas, EA logic, order execution, position
  sizing, or risk-management code was changed.

Changed files:

- `.github/workflows/ci.yml`
- `tests/test_ci_workflow.py`
- `README.md`
- `AI_HANDOFF.md`

Implementation summary:

- Added `.github/workflows/ci.yml`.
- CI trigger:
  - push to `main`
  - pull request
- CI environment:
  - `ubuntu-latest`
  - Python `3.11`
  - installs `numpy`, `pandas`, and `pytest`
- CI steps:

```bash
python -m scripts.check_handoff
python -m pytest
python -m scripts.run_ofi_experiment_batch \
  --input data/ofi_synthetic.csv \
  --output-root output/ci_ofi_batch \
  --config configs/ofi_loose.json
```

- Added `tests/test_ci_workflow.py` to assert that the workflow includes:
  - push to `main`
  - pull requests
  - Python 3.11
  - handoff check
  - full pytest
  - batch runner smoke command
- README now briefly mentions CI.

Commands run:

- Opened GitHub Issue #3 in the browser and confirmed scope, constraints, local
  commands, and done criteria.
- `git status --short`
  - Initial result: no output; worktree was clean.
- `Get-Content -Raw AI_HANDOFF.md`
  - Reviewed previous handoff state.
- `Get-Content -Raw README.md`
  - Reviewed existing command docs.
- `Get-Content -Raw pyproject.toml`
  - Confirmed dependencies and pytest marker config.
- `Get-ChildItem -Recurse .github -ErrorAction SilentlyContinue | Select-Object FullName,Length`
  - Confirmed `.github/` did not previously contain a workflow.
- `python -m pytest tests\test_ci_workflow.py`
  - Result: `1 passed in 0.30s`.
- `python -m pytest -m "not integration"`
  - Result: `35 passed, 12 deselected in 12.64s`.
- `python -m scripts.check_handoff`
  - Result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - Result: `47 passed in 103.49s (0:01:43)`.
- `python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ci_ofi_batch_local --config configs/ofi_loose.json`
  - Result: 1 succeeded, 0 failed.
- `python -m scripts.check_handoff`
  - Result after updating `AI_HANDOFF.md`: quick tests passed, handoff check
    PASS.
- Post-push verification requested by the user:
  - `.github/workflows/ci.yml` exists.
  - CI triggers are `push` to `main` and `pull_request`.
  - CI uses Python `3.11`.
  - CI runs `python -m scripts.check_handoff`.
  - CI runs `python -m pytest`.
  - README and AI handoff are updated.
  - Latest commit only touched CI/docs/test workflow files; no research logic,
    output schema, EA, or trading logic was touched.
- `python -m pytest -m "not integration"`
  - Post-push verification result: `35 passed, 12 deselected in 13.25s`.
- `python -m scripts.check_handoff`
  - Post-push verification result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - Post-push verification result: `47 passed in 115.47s (0:01:55)`.

Test results:

```text
python -m pytest tests\test_ci_workflow.py
1 passed in 0.30s

python -m pytest -m "not integration"
35 passed, 12 deselected in 12.64s

python -m scripts.check_handoff
35 passed, 12 deselected in 13.34s
handoff check: PASS

python -m pytest
47 passed in 103.49s (0:01:43)

python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ci_ofi_batch_local --config configs/ofi_loose.json
Batch result: 1 succeeded, 0 failed

python -m scripts.check_handoff
35 passed, 12 deselected in 14.26s
handoff check: PASS

python -m pytest -m "not integration"
35 passed, 12 deselected in 13.25s

python -m scripts.check_handoff
35 passed, 12 deselected in 10.98s
handoff check: PASS

python -m pytest
47 passed in 115.47s (0:01:55)
```

Current error / concern:

- The CI workflow intentionally duplicates quick pytest work because
  `scripts.check_handoff` runs `python -m pytest -m "not integration"` and the
  workflow also runs full pytest. This matches Issue #3 and keeps the handoff
  contract explicit.
- CI runtime will include the full pytest suite plus a deterministic batch smoke
  run. Local runtime was roughly:
  - quick handoff: about 20 seconds including startup
  - full pytest: about 1 minute 43 seconds
  - batch smoke: about 53 seconds
- No caching was added. The workflow stays simple and avoids CI-specific
  behavior that could hide dependency issues.
- No research or trading logic was changed.

Decisions made:

- Used one CI job with separate steps instead of multiple jobs to keep setup
  simple and avoid repeated dependency installs.
- Used common GitHub actions only:
  - `actions/checkout@v4`
  - `actions/setup-python@v5`
- Installed runtime/dev dependencies directly with pip:
  - `numpy>=1.24`
  - `pandas>=2.0`
  - `pytest>=8.0`
- Included the optional batch smoke step because it is deterministic and passed
  locally.

What I want ChatGPT to do next:

1. After this is pushed, check the GitHub Actions run for commit status.
2. If CI runtime becomes too slow, decide whether to remove the optional batch
   smoke step or move it to a separate workflow/job.
3. Consider whether a future issue should add a small `requirements-dev.txt` or
   make the project installable with `pip install -e ".[dev]"`.

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

Key entry points:

- `python -m scripts.run_ofi_zone_study`
- `python -m scripts.run_ofi_zone_sweep`
- `python -m scripts.generate_ofi_synthetic_data`
- `python -m scripts.summarize_ofi_experiment`
- `python -m scripts.check_handoff`
- `python -m scripts.run_ofi_experiment_batch`

Repository layout:

- `.github/workflows/ci.yml`: GitHub Actions CI
- `src/ofi_memory_zones/`: core package
- `scripts/`: CLI entry points and handoff/batch scripts
- `tests/`: pytest coverage
- `configs/`: reusable study configs and sweep grid
- `docs/OFI_MEMORY_ZONE.md`: detailed design and usage documentation
- `docs/OFI_EXPERIMENT_PROTOCOL.md`: repeatable validation protocol
- `README.md`: quick start and common CLI examples
- `data/ofi_synthetic.csv`: sample synthetic CSV
