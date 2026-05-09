# AI Handoff

Last updated: 2026-05-09

## Latest Update

Purpose of this pass:

- Implement GitHub Issue #1:
  [Codex Task: Add a lightweight handoff check command](https://github.com/k0z0u-dot/Imbalance-Retest/issues/1).
- Add a small command that verifies required handoff files exist and runs the
  quick non-integration pytest command.
- Keep the change outside research logic, OFI feature construction, zone
  generation, retest logic, baseline logic, report outputs, and existing CLI
  contracts.

Changed files:

- `scripts/check_handoff.py`
- `tests/test_check_handoff.py`
- `README.md`
- `docs/OFI_MEMORY_ZONE.md`
- `AI_HANDOFF.md`

Implementation summary:

- Added `python -m scripts.check_handoff`.
- The command checks that these files exist:
  - `AI_HANDOFF.md`
  - `README.md`
  - `pyproject.toml`
- It runs:

```bash
python -m pytest -m "not integration"
```

- It prints a concise pass/fail summary.
- It returns non-zero when required files are missing or pytest fails.
- Added optional full mode:

```bash
python -m scripts.check_handoff --full
```

- Added unit tests for command construction, missing-file failure, successful
  quick execution, and pytest failure propagation.
- README and docs now mention the handoff check command.

Commands run:

- `git status --short`
  - Initial result: no output; worktree was clean.
- `git remote -v`
  - Confirmed origin is `https://github.com/k0z0u-dot/Imbalance-Retest.git`.
- `Get-Content -Raw AI_HANDOFF.md`
  - Reviewed current handoff state.
- `Get-ChildItem -Force | Select-Object Name,Mode,Length`
  - Confirmed repository root layout.
- `gh issue view 1 --repo k0z0u-dot/Imbalance-Retest --json number,title,body,labels,state,url`
  - Failed because `gh` is not installed.
- Opened Issue #1 through GitHub web page.
  - Confirmed scope, constraints, required commands, documentation, and done
    criteria.
- `Get-Content -Raw README.md`
  - Reviewed existing test documentation.
- `Get-Content -Raw docs\OFI_MEMORY_ZONE.md`
  - Reviewed existing test documentation.
- `Get-ChildItem src\ofi_memory_zones -File | Select-Object Name,Length`
  - Confirmed core package files; no research logic changes were needed.
- `Get-ChildItem scripts -File | Select-Object Name,Length`
  - Reviewed existing script layout.
- `Get-Content -Raw scripts\run_ofi_zone_study.py`
  - Checked existing script style.
- `Get-Content -Raw scripts\run_ofi_zone_sweep.py`
  - Checked existing script style.
- `Get-Content -Raw pyproject.toml`
  - Confirmed pytest configuration and integration marker.
- `python -m pytest tests\test_check_handoff.py`
  - Result: `5 passed in 0.66s`.
- `python -m pytest -m "not integration"`
  - First result after initial implementation: `29 passed, 12 deselected in 16.75s`.
- `python -m pytest`
  - First result after initial implementation: `41 passed in 113.73s (0:01:53)`.
- `python -m scripts.check_handoff`
  - First result: passed, but pytest output appeared before summary lines due
    stdout buffering.
- Updated `scripts/check_handoff.py` to flush summary lines before invoking
  pytest.
- `python -m pytest -m "not integration"`
  - Final result: `29 passed, 12 deselected in 12.26s`.
- `python -m pytest`
  - Final result: `41 passed in 118.27s (0:01:58)`.
- `python -m scripts.check_handoff`
  - Final result: required files OK, quick tests passed, handoff check PASS.
- `git diff --check`
  - Result: passed; only line-ending warnings were printed.
- `git status --short`
  - Final result:

```text
 M AI_HANDOFF.md
 M README.md
 M docs/OFI_MEMORY_ZONE.md
?? scripts/check_handoff.py
?? tests/test_check_handoff.py
```

- `python -m scripts.check_handoff`
  - Final result after updating `AI_HANDOFF.md`: required files OK, quick tests
    passed, handoff check PASS.
- `git diff --stat`
  - Confirmed small docs changes; untracked new files are not included in plain
    `git diff --stat`.
- `git diff -- scripts\check_handoff.py tests\test_check_handoff.py README.md docs\OFI_MEMORY_ZONE.md`
  - Confirmed docs additions. New untracked files are present separately.
- `git status --short`
  - Before this handoff update:

```text
 M README.md
 M docs/OFI_MEMORY_ZONE.md
?? scripts/check_handoff.py
?? tests/test_check_handoff.py
```

Test results:

```text
python -m pytest tests\test_check_handoff.py
5 passed in 0.66s

python -m pytest -m "not integration"
29 passed, 12 deselected in 12.26s

python -m pytest
41 passed in 118.27s (0:01:58)

python -m scripts.check_handoff
handoff check: required files OK (AI_HANDOFF.md, README.md, pyproject.toml)
handoff check: running quick tests
command: C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe -m pytest -m not integration
29 passed, 12 deselected in 10.29s
handoff check: PASS

python -m scripts.check_handoff
handoff check: required files OK (AI_HANDOFF.md, README.md, pyproject.toml)
handoff check: running quick tests
command: C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe -m pytest -m not integration
29 passed, 12 deselected in 11.55s
handoff check: PASS
```

Current error / concern:

- `gh` is not installed, so GitHub Issue #1 was read through the web page.
- `rg.exe` previously returned `Access is denied` in this environment; use
  PowerShell `Select-String` if that persists.
- Full pytest remains around 2 minutes on this machine.
- The handoff check intentionally runs the quick non-integration suite, not the
  full suite.
- The command string printed by `scripts.check_handoff` uses the active Python
  interpreter path, so it may differ by machine.
- No research logic was modified in this pass.

Decisions made:

- Implemented `scripts/check_handoff.py` as a standard-library-only script.
- Used `sys.executable -m pytest` to ensure the check runs with the same Python
  interpreter used to invoke the script.
- Kept the script independent of `src/ofi_memory_zones` to avoid coupling a
  repository health check to research code imports.
- Added `--full` because Issue #1 explicitly allowed it and the implementation
  stayed small.
- Added tests that monkeypatch `subprocess.run` so the script behavior is
  covered without nesting pytest inside pytest.

What I want ChatGPT to do next:

1. Review whether `scripts.check_handoff --full` should be documented or left
   as a discoverable `--help` option.
2. Consider whether CI should run both:
   - `python -m scripts.check_handoff`
   - `python -m pytest`
3. Decide whether to close Issue #1 after this change is committed.

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

Key entry points:

- `python -m scripts.run_ofi_zone_study`
- `python -m scripts.run_ofi_zone_sweep`
- `python -m scripts.generate_ofi_synthetic_data`
- `python -m scripts.summarize_ofi_experiment`
- `python -m scripts.check_handoff`

Repository layout:

- `src/ofi_memory_zones/`: core package
- `scripts/`: CLI entry points and handoff check script
- `tests/`: pytest coverage
- `docs/OFI_MEMORY_ZONE.md`: detailed design and usage documentation
- `README.md`: quick start and common CLI examples
- `configs/ofi_synthetic_sanity.json`: synthetic sanity config
- `data/ofi_synthetic.csv`: sample synthetic CSV
