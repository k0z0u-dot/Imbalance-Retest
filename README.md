# Imbalance-Retest Zone

Research tooling for detecting **OFI Memory Zones** from order-flow imbalance and
checking whether later retests react more often than ordinary price areas.

This is not an EA or live trading strategy. The first goal is observational:
measure whether zones created by abnormal taker flow imbalance show stronger
retest behavior.

## Quick Start

```bash
python -m scripts.run_ofi_zone_study \
  --input data/sample.csv \
  --output output/ofi_zone_study \
  --timestamp-col timestamp \
  --price-col close
```

The command writes OFI features, generated zone events, active zones, retests,
baseline comparison, summary CSVs, `metrics_summary.json`, and `config.json` to
the output directory.

## Synthetic Sample

```bash
python -m scripts.generate_ofi_synthetic_data \
  --output data/ofi_synthetic.csv

python -m scripts.run_ofi_zone_study \
  --input data/ofi_synthetic.csv \
  --output output/ofi_synthetic_study
```

Larger sanity dataset for quality-gate/report wiring:

```bash
python -m scripts.generate_ofi_synthetic_data \
  --output data/ofi_synthetic_large.csv \
  --cycles 20 \
  --seed 42

python -m scripts.run_ofi_zone_study \
  --input data/ofi_synthetic_large.csv \
  --output output/ofi_synthetic_large_study
```

## Parameter Sweep

```bash
python -m scripts.run_ofi_zone_sweep \
  --input data/ofi_synthetic.csv \
  --output output/ofi_sweep \
  --grid-json configs/ofi_sweep_grid.json
```

## Input Inspection (Real CSV Pre-check)

Before running a real-data OFI study, inspect input readiness first:

```bash
python -m scripts.inspect_ofi_input \
  --input data/real_asset.csv \
  --output output/input_inspection
```

If your CSV uses canonical flow column names (for example `taker_buy_volume` / `taker_sell_volume`), inspection auto-detects them even without `--taker-buy-col` / `--taker-sell-col`.

This writes `input_diagnostics.json` and `input_diagnostics.md` with timestamp quality, flow-source detection, detected column mapping, coverage/null rates, warnings, and a readiness verdict (`READY`, `USABLE_WITH_WARNINGS`, `NOT_READY`).

Run inspect → study → report safely in one command for real-data smoke:

```bash
python -m scripts.run_ofi_real_data_smoke \
  --input data/real/BTC_1m.csv \
  --output-root output/real_smoke/BTC_1m \
  --config-json configs/ofi_loose.json
```

If readiness is `NOT_READY`, the runner stops before study/report and writes `smoke_summary.json` / `smoke_summary.md`.

## v0.3 Validation

Use config JSON to enable multiple baseline trials and OOS checks:

```json
{
  "baseline_random_trials": 50,
  "split_mode": "train_test",
  "train_ratio": 0.7
}
```

```bash
python -m scripts.run_ofi_zone_study \
  --input data/sample.csv \
  --output output/ofi_v03_validation \
  --config-json configs/ofi_v03_config.json
```

v0.3 adds `baseline_trials.csv`, expanded `baseline_summary.csv`,
`data_diagnostics.json`, and optional train/test or walk-forward outputs.

## v0.4 Experiment Report

Summarize one study output directory:

```bash
python -m scripts.summarize_ofi_experiment \
  --input output/ofi_train_test \
  --output output/ofi_train_test_report
```

Summarize a sweep output directory:

```bash
python -m scripts.summarize_ofi_experiment \
  --input output/ofi_sweep \
  --output output/ofi_sweep_report \
  --sweep
```

The report command writes `experiment_report.md` and
`experiment_report.json`. Sweep mode also writes
`sweep_robustness_summary.csv` and `sweep_robustness_report.md`.

## Experiment Batch

Run several reproducible study configs against one input CSV:

```bash
python -m scripts.run_ofi_experiment_batch \
  --input data/ofi_synthetic_large.csv \
  --output-root output/ofi_batch \
  --config configs/ofi_loose.json \
  --config configs/ofi_default_validation.json \
  --config configs/ofi_strict.json
```

The batch runner writes per-config `study/` and `report/` directories plus
`batch_summary.csv` and `batch_summary.json`. See
[docs/OFI_EXPERIMENT_PROTOCOL.md](docs/OFI_EXPERIMENT_PROTOCOL.md) for the
recommended validation order.

## CI

GitHub Actions runs separate jobs for the handoff check, full pytest suite, and a small batch
runner smoke test on pushes to `main` and pull requests. The full pytest job prints
`--durations=20` output so slow tests are easy to review in CI logs.

## Agent Policy

For Codex, ChatGPT, and future review agents, read
[AGENT_POLICY.md](AGENT_POLICY.md) before making repository changes.
The semi-automated ChatGPT-Codex loop is documented in
[docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md).

## Tests

Run the full test suite:

```bash
python -m pytest
```

For a quicker handoff check that skips full study/sweep/report integration
pipelines:

```bash
python -m pytest -m "not integration"
```

The same handoff sanity check is available as a small script that also verifies
the required handoff files exist:

```bash
python -m scripts.check_handoff
```

See [docs/OFI_MEMORY_ZONE.md](docs/OFI_MEMORY_ZONE.md) for the full hypothesis,
input requirements, leakage controls, baseline comparison, sweep runner, output
schema, and known limitations.
