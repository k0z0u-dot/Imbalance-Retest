from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ofi_memory_zones import batch
from ofi_memory_zones.study import load_config_json


def _write_config(path: Path, **overrides: object) -> Path:
    values = {"baseline_random_trials": 1, **overrides}
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def _metrics(avg_return: float = 5.0) -> dict[str, object]:
    return {
        "rows": 100,
        "zone_count": 4,
        "retest_count": 12,
        "retest_with_confirmation_count": 3,
        "overall_hit_rate": 0.5,
        "avg_return_bps_after_cost": avg_return,
        "median_return_bps_after_cost": 4.0,
        "profit_factor_like": 1.5,
        "warnings": ["low retest count"],
        "baseline_comparison": {
            "price_near_random_zone": {"mean_avg_return_bps_after_cost": 2.0},
            "time_matched_random_zone": {"mean_avg_return_bps_after_cost": 1.0},
            "swing_sr_zone": {"mean_avg_return_bps_after_cost": 3.0},
            "volume_profile_zone": {"mean_avg_return_bps_after_cost": 4.0},
        },
    }


def test_batch_runner_accepts_multiple_explicit_configs_and_writes_outputs(
    tmp_path,
    monkeypatch,
) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("timestamp,close\n2026-01-01,100\n", encoding="utf-8")
    configs = [
        _write_config(tmp_path / "loose.json", baseline_random_trials=1),
        _write_config(tmp_path / "strict.json", baseline_random_trials=2),
    ]

    def fake_study(*, input_path, output_dir, columns, config):  # noqa: ANN001
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        (Path(output_dir) / "metrics_summary.json").write_text("{}", encoding="utf-8")
        return {"metrics_summary": _metrics(avg_return=float(config.baseline_random_trials) + 4.0)}

    def fake_report(*, input_dir, output_dir):  # noqa: ANN001
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        (Path(output_dir) / "experiment_report.md").write_text("# report\n", encoding="utf-8")
        return {"verdict": "INCONCLUSIVE", "warnings": ["report warning"]}

    monkeypatch.setattr(batch, "run_ofi_zone_study", fake_study)
    monkeypatch.setattr(batch, "summarize_ofi_experiment", fake_report)

    result = batch.run_ofi_experiment_batch(
        input_path=input_path,
        output_root=tmp_path / "batch",
        config_paths=configs,
    )

    rows = result["rows"]
    assert [row["config_name"] for row in rows] == ["loose", "strict"]
    assert all(row["status"] == "success" for row in rows)
    assert rows[0]["price_near_random_delta_return"] == 3.0
    assert rows[0]["volume_profile_delta_return"] == 1.0
    assert rows[0]["warnings_count"] == 2
    assert (tmp_path / "batch" / "loose" / "study").is_dir()
    assert (tmp_path / "batch" / "loose" / "report" / "experiment_report.md").exists()
    assert Path(result["batch_summary_csv"]).exists()
    assert Path(result["batch_summary_json"]).exists()

    with Path(result["batch_summary_csv"]).open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert csv_rows[0]["config_name"] == "loose"
    assert csv_rows[0]["status"] == "success"

    payload = json.loads(Path(result["batch_summary_json"]).read_text(encoding="utf-8"))
    assert payload["success_count"] == 2
    assert payload["failure_count"] == 0


def test_batch_runner_records_failed_config_and_continues(tmp_path, monkeypatch) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("timestamp,close\n2026-01-01,100\n", encoding="utf-8")
    good = _write_config(tmp_path / "good.json")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"unknown_key": True}), encoding="utf-8")

    def fake_study(*, input_path, output_dir, columns, config):  # noqa: ANN001
        return {"metrics_summary": _metrics()}

    def fake_report(*, input_dir, output_dir):  # noqa: ANN001
        return {"verdict": "FAIL", "warnings": []}

    monkeypatch.setattr(batch, "run_ofi_zone_study", fake_study)
    monkeypatch.setattr(batch, "summarize_ofi_experiment", fake_report)

    result = batch.run_ofi_experiment_batch(
        input_path=input_path,
        output_root=tmp_path / "batch",
        config_paths=[good, bad],
    )

    assert [row["status"] for row in result["rows"]] == ["success", "failed"]
    assert "Unknown OFI memory zone config key" in result["rows"][1]["error_message"]


def test_batch_runner_fail_fast_raises_on_failed_config(tmp_path) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("timestamp,close\n2026-01-01,100\n", encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"unknown_key": True}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown OFI memory zone config key"):
        batch.run_ofi_experiment_batch(
            input_path=input_path,
            output_root=tmp_path / "batch",
            config_paths=[bad],
            fail_fast=True,
        )


def test_discover_config_paths_accepts_explicit_and_directory_matches(tmp_path) -> None:
    explicit = _write_config(tmp_path / "explicit.json")
    discovered = _write_config(tmp_path / "discovered.json")
    sweep_grid = tmp_path / "ofi_sweep_small.json"
    sweep_grid.write_text(json.dumps({"grid": {"baseline_random_trials": [1]}}), encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("{}", encoding="utf-8")

    paths = batch.discover_config_paths(
        config_paths=[explicit],
        config_dir=tmp_path,
        pattern="*.json",
    )

    assert [path.name for path in paths] == ["explicit.json", "discovered.json"]


def test_protocol_and_reusable_config_files_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    expected_configs = [
        "ofi_synthetic_sanity.json",
        "ofi_loose.json",
        "ofi_default_validation.json",
        "ofi_strict.json",
        "ofi_train_test_default.json",
        "ofi_walk_forward_default.json",
        "ofi_sweep_small.json",
    ]
    for name in expected_configs:
        path = repo_root / "configs" / name
        assert path.exists(), name
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        assert isinstance(payload, dict)
        if name != "ofi_sweep_small.json":
            load_config_json(path)
        else:
            assert "grid" in payload
    assert (repo_root / "docs" / "OFI_EXPERIMENT_PROTOCOL.md").exists()
