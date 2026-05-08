# OFI Memory Zone

## Purpose

This module is an observational research tool for **OFI Memory Zones** /
**Imbalance-Retest Zones**. It is not a trading EA and does not make live order
decisions. The first question is whether price areas created by abnormal taker
flow imbalance react more often, or with better MFE/MAE, when revisited later.

v0.4 still does not implement entry/exit automation, position management, or
live execution. It adds validation tools so OFI zones can be compared with
random, matched random, swing SR, and volume-profile baselines, plus simple
out-of-sample checks and experiment-level quality reports.

## Hypothesis

When a price area sees abnormal order-flow imbalance and price subsequently
reacts in a meaningful direction, that area may retain flow memory. Later
retests are logged to see whether confirmation flow or repeated absorption
improves hit rate, return after costs, and excursion statistics.

## Zone Types

`initiative_support` means aggressive buy flow appeared and price later moved
up. It is treated as a support candidate.

`absorption_support` means aggressive sell flow appeared, price did not run far
lower, and price later moved up. It is treated as passive buy absorption.

`initiative_resistance` means aggressive sell flow appeared and price later
moved down. It is treated as a resistance candidate.

`absorption_resistance` means aggressive buy flow appeared, price did not run
far higher, and price later moved down. It is treated as passive sell absorption.

## Leakage Control

Zone generation is allowed to inspect `reaction_horizon_bars` after the
imbalance event to decide whether the event became a valid research zone.
However, the zone is not eligible for retest detection until `available_from`,
which is the timestamp at the end of the reaction horizon.

Example: if the imbalance event is at 10:00 and the reaction horizon ends at
10:10, the zone is recorded around the 10:00 price, but retests from 10:00
through before 10:10 are ignored.

## Input Data

Required:

- `timestamp`
- price column such as `close` or `price`

Preferred flow source:

- `taker_buy_volume` and `taker_sell_volume`

Supported proxies:

- `buy_volume` and `sell_volume`
- raw trades with `side` plus `size` / `qty`
- `signed_volume`

If no explicit flow or supported proxy exists, the module raises an error. It
does not infer OFI from candle shape or price movement.

## CLI Example

```bash
python -m scripts.run_ofi_zone_study \
  --input data/sample.csv \
  --output output/ofi_zone_study \
  --timestamp-col timestamp \
  --price-col close
```

Optional config overrides:

```bash
python -m scripts.run_ofi_zone_study \
  --input data/sample.csv \
  --output output/ofi_zone_study \
  --config-json configs/ofi_zone_config.json
```

## Synthetic Data

Generate a deterministic sample with all four intended event patterns:

```bash
python -m scripts.generate_ofi_synthetic_data \
  --output data/ofi_synthetic.csv
```

The generated CSV contains:

- `initiative_support`
- `absorption_support`
- `initiative_resistance`
- `absorption_resistance`

It can be passed directly to the study runner:

```bash
python -m scripts.run_ofi_zone_study \
  --input data/ofi_synthetic.csv \
  --output output/ofi_synthetic_study \
  --timestamp-col timestamp \
  --price-col close
```

For quality-gate and report wiring, generate multiple cycles. Each cycle
contains all four OFI pattern types and timestamps remain monotonic:

```bash
python -m scripts.generate_ofi_synthetic_data \
  --output data/ofi_synthetic_large.csv \
  --cycles 20 \
  --seed 42

python -m scripts.run_ofi_zone_study \
  --input data/ofi_synthetic_large.csv \
  --output output/ofi_synthetic_large_study
```

Useful generator options:

- `--cycles`: repeat the four-pattern synthetic sequence
- `--start-price`: base price level, default `10000`
- `--cycle-price-offset-bps`: price offset per cycle, default `20`
- `--noise-scale`: background price noise
- `--seed`: random seed, default `42`

## Output Files

`ofi_features.csv` contains normalized OHLC/price columns, taker buy/sell flow,
signed volume, imbalance, rolling z-score, robust z-score, volume z-score, ATR,
proxy flag, and source row index.

`zone_events.csv` contains the original imbalance events that passed reaction
filters, including `event_timestamp`, `available_from`, zone bounds, zone type,
direction, imbalance statistics, reaction statistics, proxy flag, and source row.

`zones.csv` contains active zones with strength fields, retest counts,
success/failure counts, Beta posterior success estimates, and last retest time.

`retests.csv` contains every detected revisit after `available_from`, including
confirmation type, target/stop levels, first-touch outcome, MFE/MAE, and return
after costs.

`event_type_summary.csv` groups retest statistics by zone type.

`confirmation_summary.csv` groups retest statistics by confirmation type.

`baseline_trials.csv` stores per-trial baseline results.

`baseline_summary.csv` aggregates OFI and baseline zones under the same
`retest_horizon_bars`, target, stop, fee, and slippage settings. v0.3 includes
`random_zone`, `time_matched_random_zone`, `price_near_random_zone`,
`swing_sr_zone`, and `volume_profile_zone`.

`metrics_summary.json` gives the study-level view: rows, date range, proxy
usage, counts, hit rates, average/median returns after costs, MFE/MAE, a
profit-factor-like ratio, summaries by type, baseline comparison, and warnings.

`data_diagnostics.json` describes data quality, detected flow source, coverage,
sample size warnings, and zone/retest balance.

If `split_mode` is `train_test`, the runner also writes
`train_metrics_summary.json`, `test_metrics_summary.json`, and
`split_summary.csv`.

If `split_mode` is `walk_forward`, the runner writes
`walk_forward_results.csv` and `walk_forward_summary.json`.

The report summarizer writes `experiment_report.md` and
`experiment_report.json`. In sweep mode it also writes
`sweep_robustness_summary.csv` and `sweep_robustness_report.md`.

`config.json` records the exact configuration used for the run.

## Reading metrics_summary.json

`overall_hit_rate` is the target-hit rate across all retests.

`hit_rate_after_confirmation` uses only retests where confirmation was found.

`avg_return_bps_after_cost` subtracts the configured cost model. By default v0
uses round-trip cost:

```text
2 * (fee_bps + slippage_bps)
```

`profit_factor_like` is the sum of positive after-cost retest returns divided
by the absolute sum of negative after-cost retest returns. It is descriptive,
not a strategy equity curve.

## Baseline Comparison

`random_zone` samples random event bars, creates zones using the same
`zone_width_bps`, waits the same `reaction_horizon_bars` before
`available_from`, then evaluates retests with the same target/stop/cost logic
as OFI zones. This avoids giving random zones immediate hindsight access.

`time_matched_random_zone` keeps each OFI zone's `event_timestamp`,
`available_from`, direction, and zone type, but replaces only the price level
with a random observed price. This tests whether the time period around OFI
events was favorable regardless of the OFI price.

`price_near_random_zone` keeps each OFI zone's timing and direction, but shifts
the center price by a random offset between
`price_near_random_min_offset_bps` and `price_near_random_max_offset_bps`. This
tests whether nearby prices would have worked without the exact OFI level.

`swing_sr_zone` builds conventional chart SR zones from confirmed local lows and
highs. A swing is only available after the right side of `swing_window` has
elapsed, so it does not use future bars before the baseline zone is eligible.

`volume_profile_zone` builds zones from top volume price bins over a trailing
`volume_profile_lookback_bars` window. This tests whether the apparent OFI edge
is explained by high-volume prices rather than imbalance memory.

OFI has hypothesis value only after it clears these baselines. Be skeptical of
an OFI edge that only beats naive random zones but fails against time-matched,
price-near, swing SR, or volume-profile comparisons.

Use `baseline_summary.csv` to compare:

- `trials`
- `mean_hit_rate`
- `median_hit_rate`
- `std_hit_rate`
- `mean_avg_return_bps_after_cost`
- `median_avg_return_bps_after_cost`
- `std_avg_return_bps_after_cost`
- `ofi_hit_rate`
- `ofi_avg_return_bps_after_cost`
- `delta_hit_rate_vs_ofi`
- `delta_avg_return_vs_ofi`
- `ofi_percentile_vs_baseline`

The same data is also embedded in `metrics_summary.json` under
`baseline_comparison`.

`ofi_percentile_vs_baseline` reports where the OFI average return sits inside
the baseline trial distribution. Higher means OFI outperformed more baseline
trials.

Use `baseline_trials.csv` to inspect trial-level instability. Important fields:

- `baseline_name`
- `trial_id`
- `zone_count`
- `retest_count`
- `hit_rate`
- `avg_return_bps_after_cost`
- `profit_factor_like`

`random_seed`, `baseline_random_trials`, and `baseline_random_zone_count` are
configurable. If `baseline_random_zone_count` is omitted, random baselines use
the same count as generated OFI zones, capped by available candidate bars.

Recommended minimum:

```json
{
  "baseline_random_trials": 50
}
```

## Parameter Sweep

Create a grid JSON:

```json
{
  "grid": {
    "use_robust_z": [true, false],
    "imbalance_z_threshold": [1.8, 2.0, 2.5],
    "robust_z_threshold": [2.2, 2.5, 3.0],
    "reaction_horizon_bars": [10, 20],
    "zone_width_bps": [6.0, 8.0, 12.0]
  }
}
```

Run:

```bash
python -m scripts.run_ofi_zone_sweep \
  --input data/ofi_synthetic.csv \
  --output output/ofi_sweep \
  --grid-json configs/ofi_sweep_grid.json
```

Each configuration is executed into its own subdirectory. The runner writes:

- `sweep_results.csv`: every tested configuration and its metrics
- `best_configs.csv`: ranked view of the same results

`sweep_results.csv` includes top-level metrics plus flattened by-zone-type
metrics such as `initiative_support_hit_rate` and baseline deltas such as
`delta_hit_rate_vs_random_zone`.

Treat sweep output as sensitivity analysis. It is not an optimization target
for live trading until validated out of sample.

## OOS and Walk-Forward

Simple chronological train/test split:

```json
{
  "split_mode": "train_test",
  "train_ratio": 0.7
}
```

```bash
python -m scripts.run_ofi_zone_study \
  --input data/sample.csv \
  --output output/ofi_train_test \
  --config-json configs/ofi_train_test.json
```

Outputs:

- `train_metrics_summary.json`
- `test_metrics_summary.json`
- `split_summary.csv`

`split_summary.csv` includes train/test date boundaries, zone/retest counts,
train/test hit rate, train/test average return, and degradation fields.

Walk-forward:

```json
{
  "split_mode": "walk_forward",
  "wf_train_bars": 1000,
  "wf_test_bars": 300,
  "wf_step_bars": 300
}
```

```bash
python -m scripts.run_ofi_zone_study \
  --input data/sample.csv \
  --output output/ofi_walk_forward \
  --config-json configs/ofi_walk_forward.json
```

Outputs:

- `walk_forward_results.csv`
- `walk_forward_summary.json`

Each fold records `fold_id`, train/test boundaries, test `zone_count`,
`retest_count`, `hit_rate`, `avg_return_bps_after_cost`,
`baseline_delta_return`, and `baseline_delta_hit_rate`.

## Experiment Reports

Generate a report for one study directory:

```bash
python -m scripts.summarize_ofi_experiment \
  --input output/ofi_train_test \
  --output output/ofi_train_test_report
```

Generate a sweep report:

```bash
python -m scripts.summarize_ofi_experiment \
  --input output/ofi_sweep \
  --output output/ofi_sweep_report \
  --sweep
```

`experiment_report.md` is the human-readable version. It contains:

- Data Quality
- OFI Performance
- Event Type Breakdown
- Confirmation Breakdown
- Baseline Comparison
- OOS / Walk-forward
- Quality Gate and Verdict

`experiment_report.json` contains the same sections in machine-readable form.

## Quality Gate

The quality gate is a research-hypothesis screen, not a trading decision. It
returns:

- `PASS`: OFI has enough retests, positive after-cost return, and clears the
  configured baseline percentile gates.
- `WEAK_PASS`: OFI is positive and clears core matched baseline checks, but the
  evidence is not as broad.
- `INCONCLUSIVE`: data is insufficient or required comparisons are missing.
- `FAIL`: OFI is negative after costs, sample size is critically low, price-near
  random clearly outperforms OFI, OOS return degrades materially, or severe data
  quality warnings are present.

Initial gates:

- `retest_count >= 200` preferred
- `retest_count < 50` fails
- `avg_return_bps_after_cost > 0`
- OFI percentile vs `random_zone >= 80`
- OFI percentile vs `time_matched_random_zone >= 70`
- OFI percentile vs `price_near_random_zone >= 70`
- OFI should not materially underperform `swing_sr_zone`
- if walk-forward exists, positive fold ratio should be at least `0.5`

`proxy_used=True` is a warning rather than an automatic failure. Severe data
warnings such as missing volume or missing high/low can fail the gate because
the study no longer measures the intended hypothesis cleanly.

## Sweep Robustness

Sweep reporting is designed to avoid best-config overconfidence. In sweep mode
the summarizer writes:

- `sweep_robustness_summary.csv`
- `sweep_robustness_report.md`

`sweep_robustness_summary.csv` includes:

- `section`
- `parameter`
- `value`
- `config_count`
- `eligible_config_count`
- `excluded_low_retest_count_configs`
- `top_20_percent_config_count`
- `top20_median_hit_rate`
- `top20_median_avg_return_bps_after_cost`
- `median_retest_count`
- `positive_return_config_ratio`
- `baseline_exceed_config_ratio`
- `ofi_percentile_ge_80_config_ratio`

The global row summarizes the whole sweep. Parameter rows show which parameter
values are stable across a wider region. A single high-return config is weak
evidence if neighboring parameter values fail, have too few retests, or only win
against naive random baselines.

Do not trust `best_configs.csv` alone. A useful OFI hypothesis should remain
reasonably stable across nearby thresholds, horizons, and zone widths.

## Data Diagnostics

`data_diagnostics.json` is intended for real-data runs where data quality is the
most common failure mode. Main fields:

- `rows`
- `start_timestamp`
- `end_timestamp`
- `detected_flow_source`
- `proxy_used`
- `missing_columns`
- `null_rate_by_required_column`
- `taker_buy_volume_coverage`
- `taker_sell_volume_coverage`
- `signed_volume_coverage`
- `total_flow_volume_stats`
- `imbalance_z_stats`
- `robust_imbalance_z_stats`
- `zone_count_by_type`
- `retest_count_by_type`
- `warnings`

Warnings include low retest count, proxy flow usage, missing volume data,
missing high/low, zone-type dominance, too few baseline trials, and low test
period retest count.

## Why This Is Still Not an EA

The module is intentionally limited to hypothesis testing. It does not answer
position sizing, portfolio exposure, order placement, latency, exchange
constraints, adverse selection, or live risk controls. OFI must first beat
random, matched random, swing SR, volume profile, and OOS checks before any
separate execution research would be justified.

## Test Commands

Full validation:

```bash
python -m pytest
```

Quick handoff check:

```bash
python -m pytest -m "not integration"
```

Tests marked `integration` run full study, sweep, or report pipelines and are
intentionally slower.

## Known Limitations

- v0 treats each valid event as its own zone; merge distance is configured for
  compatibility and future expansion.
- v0.2 random baseline is a null model, not a replacement for a fully specified
  conventional SR baseline.
- v0.3 swing SR and volume profile baselines are intentionally simple research
  controls. They are not full discretionary SR models.
- Train/test and walk-forward outputs evaluate fixed config behavior; they do
  not implement automatic parameter selection.
- Retest entry price is approximated from the retest bar and zone bounds.
- Intrabar ordering is unknown; if target and stop are both touched in one bar,
  v0 defaults to conservative stop-first.
- Confirmation is intentionally simple and only uses imbalance z-score patterns.
- Results depend strongly on feed quality and whether true taker volume is
  available.
- Parameter sweeps can overfit quickly. Keep all results and validate promising
  settings on separate time periods or instruments.
- The quality gate is deliberately simple. It is meant to block weak research
  claims, not to certify production readiness.

## Future Extensions

- ATR-based and tick-size-based zone widths.
- More explicit merged-zone lifecycle management.
- Swing high/low or manually specified conventional SR baselines.
- Volume-matched and session-matched random baselines.
- Session/time-of-day segmentation.
- Quote-book OFI from best bid/ask size changes.
- Bootstrap confidence intervals for hit rate and return metrics.
- Plotting overlays that match the host repository's reporting style.
