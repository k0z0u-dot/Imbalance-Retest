# AI Handoff

Last updated: 2026-05-09

## Latest Update

Purpose of this pass:

- Implement GitHub Issue #2:
  [Codex Task: Add reproducible OFI experiment protocol and batch runner](https://github.com/k0z0u-dot/Imbalance-Retest/issues/2).
- Add a small reproducible experiment orchestration layer for running multiple
  OFI study configs against one input CSV.
- Add starter configs and a practical protocol document for synthetic and
  real-data validation.
- Keep this pass outside EA/trading logic. No execution, order placement,
  position sizing, or risk-management code was added.
- Do not change OFI feature construction, zone generation, retest semantics,
  target/stop first-touch behavior, baseline definitions, or existing study
  output schemas.

Changed files:

- `src/ofi_memory_zones/batch.py`
- `scripts/run_ofi_experiment_batch.py`
- `tests/test_experiment_batch.py`
- `configs/ofi_loose.json`
- `configs/ofi_default_validation.json`
- `configs/ofi_strict.json`
- `configs/ofi_train_test_default.json`
- `configs/ofi_walk_forward_default.json`
- `configs/ofi_sweep_small.json`
- `docs/OFI_EXPERIMENT_PROTOCOL.md`
- `README.md`
- `docs/OFI_MEMORY_ZONE.md`
- `AI_HANDOFF.md`

Implementation summary:

- Added batch runner CLI:

```bash
python -m scripts.run_ofi_experiment_batch \
  --input data/ofi_synthetic_large.csv \
  --output-root output/ofi_batch \
  --config configs/ofi_loose.json \
  --config configs/ofi_default_validation.json \
  --config configs/ofi_strict.json
```

- Batch runner behavior:
  - creates `<output-root>/<config_name>/study/`
  - creates `<output-root>/<config_name>/report/`
  - runs `run_ofi_zone_study`
  - runs `summarize_ofi_experiment`
  - writes `batch_summary.csv`
  - writes `batch_summary.json`
  - records failed configs as `status = failed`
  - continues after failures unless `--fail-fast` is passed
- Added config discovery:

```bash
python -m scripts.run_ofi_experiment_batch \
  --input data/sample.csv \
  --output-root output/ofi_batch \
  --config-dir configs \
  --pattern "ofi_*.json"
```

- Directory discovery skips sweep-grid JSON files such as
  `ofi_sweep_small.json`; explicitly passing a sweep grid via `--config` still
  records a failed config because it is not a study config.
- Added starter configs:
  - loose smoke validation
  - default real-data validation
  - strict validation
  - train/test validation
  - walk-forward validation
  - small sweep grid
- Added `docs/OFI_EXPERIMENT_PROTOCOL.md` with run order:
  1. synthetic sanity check
  2. single-asset smoke test
  3. baseline comparison
  4. train/test validation
  5. walk-forward validation
  6. small sweep robustness check
  7. batch runner usage
  8. inspection order
  9. common failure cases
  10. criteria for further work
- README now documents the batch runner briefly.
- `docs/OFI_MEMORY_ZONE.md` links to the protocol doc without duplicating it.

Commands run:

- `git status --short`
  - Initial result: no output; worktree was clean.
- `Get-ChildItem configs -File | Select-Object Name,Length`
  - Confirmed only `ofi_synthetic_sanity.json` existed before this pass.
- `Get-ChildItem tests -File | Select-Object Name,Length`
  - Reviewed test layout.
- `Get-Content -Raw AI_HANDOFF.md`
  - Reviewed previous handoff state.
- `Get-Content -Raw README.md`
  - Reviewed existing user-facing command docs.
- `Get-Content -Raw src\ofi_memory_zones\study.py`
  - Reviewed `run_ofi_zone_study` and `load_config_json`.
- `Get-Content -Raw src\ofi_memory_zones\reporting.py`
  - Reviewed `summarize_ofi_experiment`.
- `Get-Content -Raw src\ofi_memory_zones\sweep.py`
  - Reviewed sweep config format.
- `Get-Content -Raw src\ofi_memory_zones\config.py`
  - Reviewed allowed config keys.
- `Get-Content -Raw scripts\summarize_ofi_experiment.py`
  - Reviewed script style.
- `Get-Content -Raw src\ofi_memory_zones\schema.py`
  - Reviewed `ColumnMapping`.
- `Get-Content -Raw scripts\generate_ofi_synthetic_data.py`
  - Reviewed synthetic CLI.
- `Get-Content -Raw scripts\check_handoff.py`
  - Reviewed handoff command.
- `Get-Content -Raw configs\ofi_synthetic_sanity.json`
  - Existing config was inspected and not overwritten.
- `Get-Content -Raw tests\test_experiment_report.py`
  - Reviewed existing integration test style.
- `Select-String -Path src\ofi_memory_zones\*.py -Pattern 'delta_avg_return|baseline_comparison|delta_return|ofi_avg_return' -Context 1,3`
  - Checked baseline delta conventions.
- `Get-Content -Raw src\ofi_memory_zones\metrics.py`
  - Reviewed metrics summary shape.
- `Get-Content -Raw src\ofi_memory_zones\baselines.py`
  - Reviewed baseline summary fields.
- `Get-Content -Raw src\ofi_memory_zones\evaluation.py`
  - Reviewed quality gate baseline interpretation.
- `python -m pytest tests\test_experiment_batch.py`
  - First result: `5 passed in 11.37s`.
- `python -m scripts.generate_ofi_synthetic_data --output output/ofi_issue2_synthetic.csv --cycles 2 --seed 42`
  - Result: wrote 1120 synthetic rows.
- `python -m scripts.run_ofi_experiment_batch --input output/ofi_issue2_synthetic.csv --output-root output/ofi_issue2_batch --config configs/ofi_loose.json --config configs/ofi_strict.json`
  - Result: timed out after 244 seconds. `ofi_loose` had completed; `ofi_strict`
    was still running. The orphan Python process was stopped.
- `python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ofi_issue2_batch_min --config configs/ofi_loose.json`
  - Result: 1 succeeded, 0 failed.
- `python -m pytest -m "not integration"`
  - Intermediate result: `34 passed, 12 deselected in 10.88s`.
- `python -m scripts.check_handoff`
  - Intermediate result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - Intermediate result: `46 passed in 121.32s (0:02:01)`.
- `python -m pytest tests\test_experiment_batch.py`
  - Final result after config-dir sweep-grid filtering: `5 passed in 11.06s`.
- `python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ofi_issue2_batch_final --config configs/ofi_loose.json`
  - Final result: 1 succeeded, 0 failed.
- `python -m pytest -m "not integration"`
  - Final result: `34 passed, 12 deselected in 11.20s`.
- `python -m scripts.check_handoff`
  - Final result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - Final result: `46 passed in 108.20s (0:01:48)`.
- `Get-Content output\ofi_issue2_batch_final\batch_summary.csv`
  - Confirmed `batch_summary.csv` columns and one successful `ofi_loose` row.
- `Get-Process python -ErrorAction SilentlyContinue`
  - Final result: no Python process output; no leftover runner process.
- `python -m scripts.check_handoff`
  - Final result after updating `AI_HANDOFF.md`: quick tests passed, handoff
    check PASS.
- GitHub Issue #2 was reopened in the browser on 2026-05-09 before commit/push.
  - Confirmed the requested scope remained protocol/config/batch orchestration,
    documentation, tests, handoff update, and main push.
- `git status --short`
  - Push-prep result: Issue #2 files were modified/untracked on `main`.
- `git branch --show-current`
  - Result: `main`.
- `git log --oneline -5`
  - Latest commit before this pass: `f3a6b35 Add lightweight handoff check command`.
- `python -m pytest -m "not integration"`
  - Push-prep result: `34 passed, 12 deselected in 11.68s`.
- `python -m scripts.check_handoff`
  - Push-prep result: quick tests passed, handoff check PASS.
- `python -m pytest`
  - Push-prep result: `46 passed in 106.94s (0:01:46)`.
- `python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ofi_issue2_batch_pushcheck --config configs/ofi_loose.json`
  - Push-prep result: 1 succeeded, 0 failed.
- `git diff --check`
  - Push-prep result: passed; only line-ending warnings were printed.
- `Get-Process python -ErrorAction SilentlyContinue`
  - Push-prep result: no Python process output after the batch run completed.

Test results:

```text
python -m pytest tests\test_experiment_batch.py
5 passed in 11.06s

python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ofi_issue2_batch_final --config configs/ofi_loose.json
Batch result: 1 succeeded, 0 failed

python -m pytest -m "not integration"
34 passed, 12 deselected in 11.20s

python -m scripts.check_handoff
34 passed, 12 deselected in 11.80s
handoff check: PASS

python -m scripts.check_handoff
34 passed, 12 deselected in 11.39s
handoff check: PASS

python -m pytest
46 passed in 108.20s (0:01:48)

python -m pytest -m "not integration"
34 passed, 12 deselected in 11.68s

python -m scripts.check_handoff
34 passed, 12 deselected in 11.09s
handoff check: PASS

python -m pytest
46 passed in 106.94s (0:01:46)

python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/ofi_issue2_batch_pushcheck --config configs/ofi_loose.json
Batch result: 1 succeeded, 0 failed
```

Current error / concern:

- The two-config synthetic batch command using `ofi_loose` and `ofi_strict`
  timed out at 244 seconds because the strict config with many baseline trials
  is too heavy for a minimal command. The final verification uses one loose
  config and completes successfully.
- `ofi_loose` on the small tracked synthetic sample produced a report verdict
  of `FAIL` because average return after cost was negative and retest count was
  low. This is an expected quality-gate result, not a batch runner failure.
- Full pytest remains around 2 minutes.
- Config files are starting points for reproducible validation, not optimized
  parameter sets.
- `configs/ofi_sweep_small.json` is a sweep grid, not a study config. Batch
  directory discovery skips it; explicitly passing it to `--config` will record
  a failed config row.
- No EA/trading logic was added.

Decisions made:

- Added a dedicated `src/ofi_memory_zones/batch.py` orchestration module instead
  of embedding all logic in the script.
- Used existing internal functions directly:
  - `run_ofi_zone_study`
  - `summarize_ofi_experiment`
  - `load_config_json`
- Used CSV/JSON output for batch summary without introducing new dependencies.
- Kept failure handling local to each config and added `--fail-fast` for stricter
  runs.
- Computed batch baseline delta columns as `OFI average return - baseline
  average return`, so positive values mean OFI outperformed that baseline.
- Added lightweight unit tests with monkeypatching rather than adding another
  slow full-pipeline test.

What I want ChatGPT to do next:

1. Review whether the default real-data config values are sensible starting
   points for the intended market/timeframe.
2. Decide whether `ofi_sweep_small.json` should be renamed to make it clearer
   that it is for `run_ofi_zone_sweep`, not the batch runner.
3. Consider adding CI commands:
   - `python -m pytest -m "not integration"`
   - `python -m scripts.check_handoff`
   - optionally `python -m pytest` on slower runs.
4. Review the pushed Issue #2 commit on GitHub and decide whether to close the
   issue.

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

Key entry points:

- `python -m scripts.run_ofi_zone_study`
- `python -m scripts.run_ofi_zone_sweep`
- `python -m scripts.generate_ofi_synthetic_data`
- `python -m scripts.summarize_ofi_experiment`
- `python -m scripts.check_handoff`
- `python -m scripts.run_ofi_experiment_batch`

Repository layout:

- `src/ofi_memory_zones/`: core package
- `scripts/`: CLI entry points and handoff/batch scripts
- `tests/`: pytest coverage
- `configs/`: reusable study configs and sweep grid
- `docs/OFI_MEMORY_ZONE.md`: detailed design and usage documentation
- `docs/OFI_EXPERIMENT_PROTOCOL.md`: repeatable validation protocol
- `README.md`: quick start and common CLI examples
- `data/ofi_synthetic.csv`: sample synthetic CSV
