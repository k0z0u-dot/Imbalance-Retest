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

See [docs/OFI_MEMORY_ZONE.md](docs/OFI_MEMORY_ZONE.md) for the full hypothesis,
input requirements, leakage controls, baseline comparison, sweep runner, output
schema, and known limitations.
