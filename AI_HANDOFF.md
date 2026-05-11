# AI Handoff

Last updated: 2026-05-11

## Latest Update

Purpose of this pass:

- Improve CLI UX by auto-detecting canonical OFI flow columns when explicit CLI mappings are not provided.
- Preserve OFI feature semantics, zone/retest logic, baselines, quality gate, and output schemas.

Changed files:

- `src/ofi_memory_zones/column_detection.py`
- `src/ofi_memory_zones/input_inspection.py`
- `tests/test_column_detection.py`
- `tests/test_input_inspection.py`
- `AI_HANDOFF.md`

Implementation summary:

- Added canonical flow column detection utility (`infer_column_mapping_from_columns`) with priority-safe candidate lists for taker buy/sell, buy/sell proxy, side/size, and signed volume.
- Explicit mappings continue to take precedence; auto-detection only fills `None` fields.
- Integrated auto-detection into `inspect_input_csv()` so `scripts.inspect_ofi_input` can detect standard flow columns without extra CLI flags.
- Added diagnostics output field `detected_column_mapping` for transparency of inferred mappings.
- Added tests for detection behavior and explicit-over-auto precedence, and updated CLI inspection test to run without explicit flow flags.

Commands run:

- `python -m scripts.check_handoff`
- `python -m pytest`

Known unresolved points:

- None in this scope.

Codex Cloud UI PR workflow:

- This change set is prepared for Codex Cloud UI PR creation/update workflow.
- No manual `git push` was performed from shell.



## Latest Update

Purpose of this pass:

- Add a pre-study input CSV inspection CLI so real BTC/ETH/SOL-like datasets can be diagnosed before OFI zone study execution.
- Preserve existing OFI feature construction, zone/retest semantics, baselines, reporting, and existing output schemas.

Changed files:

- `src/ofi_memory_zones/input_inspection.py`
- `scripts/inspect_ofi_input.py`
- `tests/test_input_inspection.py`
- `README.md`
- `docs/OFI_EXPERIMENT_PROTOCOL.md`
- `docs/OFI_MEMORY_ZONE.md`
- `AI_HANDOFF.md`

Implementation summary:

- Added `inspect_input_csv()` diagnostics with rows/columns, timestamp quality, duplicate detection, inferred bar interval, duration, OHLC availability, flow source detection priority, proxy flags, coverage/null rates, zero-flow rate, warnings, and readiness verdict (`READY`/`USABLE_WITH_WARNINGS`/`NOT_READY`).
- Added flow source priority aligned with existing study behavior:
  1) taker_buy+taker_sell
  2) buy_volume+sell_volume proxy
  3) side+size proxy
  4) signed_volume proxy
  5) none (NOT_READY)
- Added `write_input_diagnostics_reports()` to output `input_diagnostics.json` and `input_diagnostics.md` with recommended next command.
- Added `python -m scripts.inspect_ofi_input` CLI with explicit column-mapping flags.
- Added tests for readiness/proxy/not-ready behavior, timestamp/high-low warnings, and CLI artifact creation.
- Updated README and protocol docs to run inspection before real-data OFI study.

Commands run:

- `pytest -q`
- `python -m pytest -m "not integration"`
- `python -m scripts.check_handoff`
- `python -m pytest --durations=20`

Test results:

- See command output in this handoff update.

Known unresolved points:

- None in this scope.

Codex Cloud UI PR workflow:

- This change set is prepared for Codex Cloud UI PR creation/update workflow.
- No manual `git push` was performed from shell.


## Latest Update

Purpose of this pass:

- Improve CI/test observability for review in GitHub Actions, Codex Cloud, and local runs.
- Keep OFI feature construction, zone generation, retest logic, baselines, reporting semantics, quality-gate interpretation, and output schemas unchanged.

Changed files:

- `.github/workflows/ci.yml`
- `README.md`
- `AI_HANDOFF.md`

Implementation summary:

- Split GitHub Actions checks into three explicit jobs so logs are easier to review by purpose:
  - quick handoff check
  - full pytest
  - batch runner smoke
- Updated CI full pytest command to `python -m pytest --durations=20` to expose slow-test timing summary directly in Actions logs.
- Left `pyproject.toml` pytest addopts unchanged (`-q`) to avoid changing local default behavior unexpectedly.
- Added a short README CI note that full pytest includes `--durations=20` in CI.

Commands run:

- `pytest -q`
- `python -m pytest -m "not integration"`
- `python -m scripts.check_handoff`
- `python -m pytest --durations=20`

Test results:

```text
pytest -q
................................................                         [100%]
48 passed in 70.38s (0:01:10)

python -m pytest -m "not integration"
....................................                                     [100%]
36 passed, 12 deselected in 52.13s

python -m scripts.check_handoff
handoff check: required files OK (AI_HANDOFF.md, README.md, pyproject.toml)
handoff check: running quick tests
command: /usr/local/bin/python -m pytest -m not integration
....................................                                     [100%]
36 passed, 12 deselected in 55.17s
handoff check: PASS

python -m pytest --durations=20
................................................                         [100%]
============================= slowest 20 durations ==============================
8.53s call     tests/test_reports.py::test_experiment_report_passes_quality_gate_on_large_synthetic
8.17s call     tests/test_ofi_zone_study.py::test_cli_runs_with_taker_buy_sell_and_writes_outputs
7.90s call     tests/test_ofi_zone_study.py::test_cli_runs_with_side_size_columns
7.65s call     tests/test_ofi_zone_sweep.py::test_sweep_runs_and_writes_summary
7.34s call     tests/test_reports.py::test_experiment_report_marks_fail_when_gate_not_met
7.31s call     tests/test_reports.py::test_sweep_report_outputs_files
7.22s call     tests/test_batch.py::test_batch_runs_configs_and_writes_summary
0.05s call     tests/test_utils.py::test_floor_to_tick_handles_basic_values
0.05s setup    tests/test_batch.py::test_discover_config_paths_explicit_and_sorted_dir
0.05s call     tests/test_quality_gate.py::test_quality_gate_fails_when_no_confirmed_retests
(remaining durations omitted)
48 passed in 74.61s (0:01:14)
```

CI/runtime concerns:

- Full-suite runtime variance remains expected across environments; `--durations=20` now makes the slowest test contributors explicit in CI logs for easier comparison.

Known unresolved points:

- No functional blockers in this scope.
- Runtime variance itself is not eliminated, only made more observable.

Codex Cloud UI PR workflow:

- Prepared this change set for Codex Cloud UI PR creation/update workflow.
- No manual `git push` was performed from the shell.

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
