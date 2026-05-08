# AI Handoff

Last updated: 2026-05-09

## Latest Update

今回の目的:

- `AI_HANDOFF.md` を起点に、最も小さく安全な改善としてテスト実行時間の懸念に対応した。
- 研究ロジックやCLI仕様は変更せず、重い統合テストに `integration` マーカーを付け、短時間のhandoff確認コマンドを追加した。

変更ファイル:

- `pyproject.toml`
- `README.md`
- `docs/OFI_MEMORY_ZONE.md`
- `tests/test_data_diagnostics.py`
- `tests/test_experiment_report.py`
- `tests/test_ofi_matched_baselines.py`
- `tests/test_ofi_study.py`
- `tests/test_ofi_sweep.py`
- `tests/test_ofi_synthetic_smoke.py`
- `tests/test_oos_split.py`
- `tests/test_synthetic_cycles.py`
- `AI_HANDOFF.md`

実行コマンド:

- `Get-Content -Raw AI_HANDOFF.md`
- `git status --short`
- `Get-ChildItem -Force | Select-Object Name,Mode,Length`
- `Get-ChildItem -Recurse -File src\\ofi_memory_zones,tests,docs | Select-Object FullName`
- `Get-Content -Raw README.md`
- `Get-Content -Raw docs\\OFI_MEMORY_ZONE.md`
- `Get-Content -Raw src\\ofi_memory_zones\\*.py` の主要ファイル確認
- `Get-ChildItem tests -File | Select-Object Name`
- `python -m pytest -m "not integration"`
- `python -m pytest`
- `git status --short`

テスト結果:

```text
python -m pytest -m "not integration"
24 passed, 12 deselected in 12.40s

python -m pytest
36 passed in 112.68s (0:01:52)
```

最新の `git status --short`:

```text
 M AI_HANDOFF.md
 M README.md
 M docs/OFI_MEMORY_ZONE.md
 M pyproject.toml
 M tests/test_data_diagnostics.py
 M tests/test_experiment_report.py
 M tests/test_ofi_matched_baselines.py
 M tests/test_ofi_study.py
 M tests/test_ofi_sweep.py
 M tests/test_ofi_synthetic_smoke.py
 M tests/test_oos_split.py
 M tests/test_synthetic_cycles.py
```

未解決の懸念:

- フルpytestは改善前より少し短くなったが、まだ約2分かかる。
- `integration` マーカーは粗めの分類で、将来的には `slow`, `cli`, `report`, `sweep` などに分けてもよい。
- 研究ロジック本体の品質は今回変更していない。
- `pyproject.toml` のプロジェクトversionはまだ `0.1.0`。

次にChatGPTへ相談すべき点:

1. `integration` 以外のテスト分類を増やすべきか。
2. CIを想定するなら、quick/fullの2段階テストコマンドをどう運用するか。
3. `pyproject.toml` のversionを実装状態に合わせて更新するか。
4. 実データ検証前に、入力CSVスキーマ診断をさらに厳密化するか。

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

## Changed Files

Changed in this handoff update:

- `AI_HANDOFF.md` was created.

No source code, tests, README, docs, or config files were changed in this pass.

## Commands Run

Commands and outcomes:

- `Get-ChildItem -Force "C:\\Users\\user\\OneDrive\\Desktop" | Where-Object { $_.Name -like 'Imbalance*' } | Select-Object Name,FullName,Mode`
  - Found the active repository at `C:\Users\user\OneDrive\Desktop\Imbalance-Retest`.
- `Get-ChildItem -Force`
  - Confirmed top-level layout: `configs`, `data`, `docs`, `scripts`, `src`,
    `tests`, `pyproject.toml`, `README.md`.
- `git status --short`
  - Result: `fatal: not a git repository (or any of the parent directories): .git`.
  - This workspace is currently not Git-managed.
- `Get-ChildItem -Recurse -File | Select-Object -First 160 FullName`
  - Confirmed repository files and test files.
- `Get-Content -Raw README.md`
  - Reviewed quick start, synthetic examples, validation examples, and report CLI.
- `Get-Content -Raw docs\\OFI_MEMORY_ZONE.md`
  - Reviewed detailed design, leakage controls, baselines, OOS, diagnostics, and
    quality gate documentation.
- `Get-Content -Raw pyproject.toml`
  - Confirmed dependencies: `numpy`, `pandas`; dev dependency: `pytest`.
- `Get-Content -Raw src\\ofi_memory_zones\\study.py`
  - Reviewed main study pipeline and output generation.
- `Get-Content -Raw src\\ofi_memory_zones\\config.py`
  - Reviewed current config dataclass and defaults.
- `Get-Content -Raw src\\ofi_memory_zones\\features.py`
  - Reviewed OFI feature construction and flow-source handling.
- `Get-Content -Raw src\\ofi_memory_zones\\zones.py`
  - Reviewed zone generation and leakage control.
- `Get-Content -Raw src\\ofi_memory_zones\\retests.py`
  - Reviewed retest, confirmation, and outcome logic.
- `Get-Content -Raw src\\ofi_memory_zones\\baselines.py`
  - Reviewed random, matched random, swing SR, and volume profile baselines.
- `Get-Content -Raw src\\ofi_memory_zones\\evaluation.py`
  - Reviewed quality gate verdict logic.
- `Get-Content -Raw src\\ofi_memory_zones\\synthetic.py`
  - Reviewed synthetic generator and multi-cycle support.
- `Get-Content -Raw src\\ofi_memory_zones\\reporting.py`
  - Reviewed experiment report and sweep robustness reporting.
- `Get-Content -Raw src\\ofi_memory_zones\\splits.py`
  - Reviewed train/test and walk-forward split logic.
- `Get-Content -Raw src\\ofi_memory_zones\\diagnostics.py`
  - Reviewed diagnostics and warning generation.
- `Get-ChildItem tests -File | Select-Object Name`
  - Confirmed test suite files.
- `python -m pytest`
- `python -m pytest -m "not integration"`
- Slow full-pipeline tests are marked with `integration` for quicker handoff checks.
  - Result: all tests passed.

## Test Result

Latest test run:

```text
36 passed in 136.55s (0:02:16)
```

Command:

```bash
python -m pytest
```

## Current Error / Concern

- The repository is now Git-managed.
- Full pytest currently takes about 1 minute 52 seconds on the latest run.
- Quick handoff check is available with `python -m pytest -m "not integration"`;
  latest result was 24 passed and 12 deselected in 12.40s.
- Some integration tests still run full study pipelines with synthetic data and
  baseline trials, which contributes to runtime.
- Quality gate thresholds are intentionally simple and conservative. They are
  useful for research triage, not production readiness.
- Swing SR and volume profile baselines are simplified controls, not full
  discretionary SR models.
- Retest entry and target/stop ordering remain bar-based approximations.
- The project version in `pyproject.toml` is still `0.1.0` despite iterative
  v0.2-v0.4 style feature additions.
- The latest synthetic generator supports multi-cycle data, but generated
  datasets are still artificial sanity fixtures, not evidence of real-market
  edge.

## Decisions Made

- Treat `C:\Users\user\OneDrive\Desktop\Imbalance-Retest` as the active
  repository. The older `Imbalance-Retest Zone` path was not present.
- Do not modify source code, tests, README, docs, or config files during this
  handoff pass.
- Create `AI_HANDOFF.md` as the single handoff document at repository root.
- Record exact commands and outcomes so the next ChatGPT session can verify
  context quickly.
- Keep the research boundary explicit: no EA, no execution logic, no position
  management.

## What I Want ChatGPT To Do Next

Suggested next tasks to discuss:

1. Decide whether to initialize Git for this repository and commit the current
   working state.
2. Consider reducing test runtime by marking heavier integration tests or adding
   a smaller smoke-test command for quick handoffs.
3. Run a full synthetic quality-gate sanity workflow:
   - generate multi-cycle synthetic data,
   - run study,
   - summarize experiment,
   - confirm report verdict and baseline sections.
4. Review quality gate thresholds against the intended research standard.
5. Consider adding real-data examples or a data schema checklist before running
   external market data.
6. Consider updating `pyproject.toml` version metadata if semantic versioning is
   desired.
