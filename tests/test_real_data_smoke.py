from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd


def test_not_ready_input_stops_before_study_and_report(tmp_path) -> None:
    input_path = tmp_path / "not_ready.csv"
    out = tmp_path / "smoke"
    pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=4, freq="min"), "close": [1, 2, 3, 4]}).to_csv(input_path, index=False)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_ofi_real_data_smoke",
            "--input",
            str(input_path),
            "--output-root",
            str(out),
            "--config-json",
            "configs/ofi_loose.json",
        ],
        check=False,
    )
    assert result.returncode == 1
    assert (out / "input_inspection" / "input_diagnostics.json").exists()
    assert not (out / "study").exists()
    assert not (out / "report").exists()
    payload = json.loads((out / "smoke_summary.json").read_text(encoding="utf-8"))
    assert payload["readiness_verdict"] == "NOT_READY"
    assert payload["study_executed"] is False
    assert payload["report_executed"] is False


def test_ready_like_input_runs_full_smoke_pipeline(tmp_path) -> None:
    input_path = tmp_path / "ready.csv"
    out = tmp_path / "smoke"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=20, freq="min"),
            "open": [100.0] * 20,
            "high": [100.1] * 20,
            "low": [99.9] * 20,
            "close": [100.0 + (i % 3) * 0.01 for i in range(20)],
            "taker_buy_volume": [10 + (i % 5) for i in range(20)],
            "taker_sell_volume": [9 + (i % 4) for i in range(20)],
        }
    ).to_csv(input_path, index=False)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_ofi_real_data_smoke",
            "--input",
            str(input_path),
            "--output-root",
            str(out),
            "--config-json",
            "configs/ofi_loose.json",
        ],
        check=True,
    )

    assert (out / "input_inspection" / "input_diagnostics.json").exists()
    assert (out / "study" / "metrics_summary.json").exists()
    assert (out / "report" / "experiment_report.json").exists()
    assert (out / "smoke_summary.json").exists()
    payload = json.loads((out / "smoke_summary.json").read_text(encoding="utf-8"))
    assert payload["readiness_verdict"] in {"READY", "USABLE_WITH_WARNINGS"}
    assert payload["study_executed"] is True
    assert payload["report_executed"] is True
