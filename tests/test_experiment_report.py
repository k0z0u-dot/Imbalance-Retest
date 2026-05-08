from __future__ import annotations

import json

import pandas as pd
import pytest

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.reporting import summarize_ofi_experiment
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import run_ofi_zone_study
from ofi_memory_zones.sweep import run_ofi_zone_sweep
from ofi_memory_zones.synthetic import generate_synthetic_ofi_data

pytestmark = pytest.mark.integration


def test_study_output_generates_experiment_report(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    study_dir = tmp_path / "study"
    report_dir = tmp_path / "report"
    generate_synthetic_ofi_data(output_path=input_path)
    run_ofi_zone_study(
        input_path=input_path,
        output_dir=study_dir,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        config=OFIMemoryZoneConfig(baseline_random_trials=2),
    )

    report = summarize_ofi_experiment(input_dir=study_dir, output_dir=report_dir)

    assert (report_dir / "experiment_report.md").exists()
    assert (report_dir / "experiment_report.json").exists()
    assert report["verdict"] in {"PASS", "WEAK_PASS", "INCONCLUSIVE", "FAIL"}
    payload = json.loads((report_dir / "experiment_report.json").read_text(encoding="utf-8"))
    assert "baseline_comparison" in payload


def test_missing_baseline_summary_does_not_crash(tmp_path) -> None:
    study_dir = tmp_path / "study"
    report_dir = tmp_path / "report"
    study_dir.mkdir()
    (study_dir / "metrics_summary.json").write_text(
        json.dumps(
            {
                "rows": 10,
                "retest_count": 0,
                "avg_return_bps_after_cost": None,
                "proxy_used": False,
            }
        ),
        encoding="utf-8",
    )
    (study_dir / "data_diagnostics.json").write_text(
        json.dumps({"warnings": [], "proxy_used": False}),
        encoding="utf-8",
    )

    report = summarize_ofi_experiment(input_dir=study_dir, output_dir=report_dir)

    assert (report_dir / "experiment_report.md").exists()
    assert any("baseline_summary.csv" in warning for warning in report["warnings"])


def test_sweep_output_generates_robustness_summary(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    grid_path = tmp_path / "grid.json"
    sweep_dir = tmp_path / "sweep"
    report_dir = tmp_path / "sweep_report"
    generate_synthetic_ofi_data(output_path=input_path)
    grid_path.write_text(
        json.dumps(
            {
                "grid": {
                    "use_robust_z": [True, False],
                    "imbalance_z_threshold": [2.0],
                    "robust_z_threshold": [2.5],
                    "reaction_horizon_bars": [20],
                    "baseline_random_trials": [1],
                }
            }
        ),
        encoding="utf-8",
    )
    run_ofi_zone_sweep(
        input_path=input_path,
        output_dir=sweep_dir,
        grid_json_path=grid_path,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        best_limit=1,
    )

    summarize_ofi_experiment(input_dir=sweep_dir, output_dir=report_dir, sweep=True)

    assert (report_dir / "sweep_robustness_summary.csv").exists()
    assert (report_dir / "sweep_robustness_report.md").exists()
    summary = pd.read_csv(report_dir / "sweep_robustness_summary.csv")
    assert "positive_return_config_ratio" in summary.columns
    assert "ofi_percentile_ge_80_config_ratio" in summary.columns
