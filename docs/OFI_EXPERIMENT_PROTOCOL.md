# OFI Experiment Protocol

This protocol makes OFI Memory Zone validation repeatable across synthetic
sanity checks and first-pass real-data studies. It is still research tooling,
not an EA, signal engine, execution system, or position-management layer.

## 1. Synthetic Sanity Check

Use synthetic data to verify wiring, file outputs, reports, and quality-gate
behavior. Synthetic results are not market evidence.

```bash
python -m scripts.generate_ofi_synthetic_data \
  --output data/ofi_synthetic_large.csv \
  --cycles 20 \
  --seed 42

python -m scripts.run_ofi_zone_study \
  --input data/ofi_synthetic_large.csv \
  --output output/protocol_synthetic/study \
  --config-json configs/ofi_synthetic_sanity.json

python -m scripts.summarize_ofi_experiment \
  --input output/protocol_synthetic/study \
  --output output/protocol_synthetic/report
```

Inspect `experiment_report.md`, `data_diagnostics.json`, and
`baseline_summary.csv`. A synthetic `FAIL` can be acceptable if it reflects a
sample-size or gate condition rather than a crash.

## 2. Real-Data Input Inspection (Run First)

Before any real-data study run, inspect CSV readiness:

```bash
python -m scripts.inspect_ofi_input \
  --input data/real_asset.csv \
  --output output/real_input_inspection
```

If your CSV has canonical flow names (such as `taker_buy_volume` / `taker_sell_volume`), they are auto-detected without explicit flow flags.

Read `input_diagnostics.md` first. If verdict is `NOT_READY`, fix required columns/quality issues before `run_ofi_zone_study`.

## 2. Single-Asset Smoke Test

Run a loose config on one real-data CSV to confirm the schema, flow source, and
basic sample size.

```bash
python -m scripts.run_ofi_zone_study \
  --input data/real_asset.csv \
  --output output/real_smoke_loose/study \
  --config-json configs/ofi_loose.json

python -m scripts.summarize_ofi_experiment \
  --input output/real_smoke_loose/study \
  --output output/real_smoke_loose/report
```

Check `data_diagnostics.json` first. Flow proxy usage, missing high/low data,
or very low retest counts should be treated as data-quality blockers before any
performance interpretation.


## 2.5 Real-Data Smoke Runner (Inspection + Study + Report)

After reviewing `input_diagnostics.md`, you can run a guarded smoke pipeline:

```bash
python -m scripts.run_ofi_real_data_smoke \
  --input data/real/BTC_1m.csv \
  --output-root output/real_smoke/BTC_1m \
  --config-json configs/ofi_loose.json
```

Behavior:

- Runs `inspect_ofi_input` equivalent first and stores outputs under `input_inspection/`.
- If `readiness_verdict == NOT_READY`, it stops before study/report and writes only `smoke_summary.json` and `smoke_summary.md`.
- If verdict is `READY` or `USABLE_WITH_WARNINGS`, it runs study (`study/`) and report (`report/`) then writes smoke summary files.
- `USABLE_WITH_WARNINGS` requires careful interpretation of proxy flow (`proxy_used=True`) and high/low availability warnings.

This smoke run is **not** a strategy backtest or order simulation. It is a pipeline safety/diagnostics check.

Do not commit raw CSV (`data/real/*`) or generated output (`output/*`, `reports/*`) to Git.

## 3. Baseline Comparison

Run default validation after the smoke test passes. OFI has hypothesis value
only if it compares well against:

- `time_matched_random_zone`
- `price_near_random_zone`
- `swing_sr_zone`
- `volume_profile_zone`

```bash
python -m scripts.run_ofi_zone_study \
  --input data/real_asset.csv \
  --output output/real_default_validation/study \
  --config-json configs/ofi_default_validation.json

python -m scripts.summarize_ofi_experiment \
  --input output/real_default_validation/study \
  --output output/real_default_validation/report
```

Do not accept a result that only beats naive `random_zone`. Matched and
structure-aware baselines are the relevant controls.

## 4. Train/Test Validation

Use chronological train/test validation to check whether the same configuration
survives a simple out-of-sample split.

```bash
python -m scripts.run_ofi_zone_study \
  --input data/real_asset.csv \
  --output output/real_train_test/study \
  --config-json configs/ofi_train_test_default.json

python -m scripts.summarize_ofi_experiment \
  --input output/real_train_test/study \
  --output output/real_train_test/report
```

Inspect `split_summary.csv`, train/test return degradation, and test retest
count. A strong train result with weak or negative test behavior is not a robust
OFI hypothesis.

## 5. Walk-Forward Validation

Walk-forward is slower, but it gives a better first look at temporal stability.

```bash
python -m scripts.run_ofi_zone_study \
  --input data/real_asset.csv \
  --output output/real_walk_forward/study \
  --config-json configs/ofi_walk_forward_default.json

python -m scripts.summarize_ofi_experiment \
  --input output/real_walk_forward/study \
  --output output/real_walk_forward/report
```

Inspect `walk_forward_results.csv`, `walk_forward_summary.json`, positive fold
ratio, and baseline deltas by fold.

## 6. Small Sweep Robustness Check

Sweep output should be read as robustness evidence, not as permission to pick a
single best config.

```bash
python -m scripts.run_ofi_zone_sweep \
  --input data/real_asset.csv \
  --output output/real_sweep \
  --grid-json configs/ofi_sweep_small.json

python -m scripts.summarize_ofi_experiment \
  --input output/real_sweep \
  --output output/real_sweep_report \
  --sweep
```

Do not trust `best_configs.csv` alone. Use
`sweep_robustness_summary.csv` to check whether nearby settings remain positive
and whether enough configs beat the baselines.

## 7. Batch Runner

Use the batch runner to apply several study configs to one input file and
collect a compact summary.

```bash
python -m scripts.run_ofi_experiment_batch \
  --input data/ofi_synthetic_large.csv \
  --output-root output/ofi_batch \
  --config configs/ofi_loose.json \
  --config configs/ofi_default_validation.json \
  --config configs/ofi_strict.json
```

The runner writes:

- `output/ofi_batch/<config_name>/study/`
- `output/ofi_batch/<config_name>/report/`
- `output/ofi_batch/batch_summary.csv`
- `output/ofi_batch/batch_summary.json`

If one config fails, the batch records `status = failed` and continues. Add
`--fail-fast` to stop on the first failed config.

## 8. What To Inspect First

Read files in this order:

1. `data_diagnostics.json`
2. `experiment_report.md`
3. `baseline_summary.csv`
4. `retests.csv`
5. OOS files: `split_summary.csv` or `walk_forward_results.csv`
6. Sweep files: `sweep_robustness_summary.csv` before `best_configs.csv`
7. Batch files: `batch_summary.csv` before individual reports

## 9. Common Failure Cases

- `FAIL` with low `retest_count`: the quality gate is working; collect more
  data or loosen the first-pass config for diagnostics.
- `proxy_used=True`: the study used approximate flow, so conclusions are weaker.
- Missing high/low data: first-touch outcome quality is degraded.
- OFI loses to `price_near_random_zone`: the exact OFI price may not matter.
- OFI loses to `time_matched_random_zone`: the event time may explain the result.
- OFI loses to `swing_sr_zone` or `volume_profile_zone`: conventional structure
  may explain the result better than flow imbalance.
- Strong `best_configs.csv` but weak robustness: likely overfit.

## 10. Criteria For Further Work

The hypothesis deserves further work only when:

- data diagnostics are clean enough for the intended flow source;
- retest sample size is adequate;
- OFI return after cost is positive;
- OFI performs well against matched random, price-near random, swing SR, and
  volume-profile baselines;
- train/test or walk-forward results do not collapse out of sample;
- sweep robustness is broad enough that the result is not one isolated config.

Passing these checks is still not production readiness. It only justifies
further research. Execution, sizing, broker integration, portfolio risk, and
live trading remain out of scope.
