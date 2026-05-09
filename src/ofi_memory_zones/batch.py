from __future__ import annotations

import csv
import json
from pathlib import Path
import re
from typing import Any

from ofi_memory_zones.reporting import summarize_ofi_experiment
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import load_config_json, run_ofi_zone_study


BATCH_SUMMARY_COLUMNS = [
    "config_name",
    "status",
    "verdict",
    "rows",
    "zone_count",
    "retest_count",
    "retest_with_confirmation_count",
    "overall_hit_rate",
    "avg_return_bps_after_cost",
    "median_return_bps_after_cost",
    "profit_factor_like",
    "price_near_random_delta_return",
    "time_matched_random_delta_return",
    "swing_sr_delta_return",
    "volume_profile_delta_return",
    "warnings_count",
    "study_output_dir",
    "report_output_dir",
    "error_message",
]


BASELINE_NAMES = {
    "price_near_random_delta_return": "price_near_random_zone",
    "time_matched_random_delta_return": "time_matched_random_zone",
    "swing_sr_delta_return": "swing_sr_zone",
    "volume_profile_delta_return": "volume_profile_zone",
}


def discover_config_paths(
    *,
    config_paths: list[str | Path] | None = None,
    config_dir: str | Path | None = None,
    pattern: str = "*.json",
) -> list[Path]:
    paths: list[Path] = []
    for path in config_paths or []:
        paths.append(Path(path))
    if config_dir is not None:
        paths.extend(
            path for path in sorted(Path(config_dir).glob(pattern)) if not _is_sweep_grid(path)
        )

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    if not unique:
        raise ValueError("At least one --config or --config-dir match is required.")
    return unique


def run_ofi_experiment_batch(
    *,
    input_path: str | Path,
    output_root: str | Path,
    config_paths: list[str | Path],
    columns: ColumnMapping | None = None,
    fail_fast: bool = False,
) -> dict[str, Any]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for config_path in [Path(path) for path in config_paths]:
        config_name = _unique_config_name(_safe_config_name(config_path), used_names)
        config_output_dir = output / config_name
        study_dir = config_output_dir / "study"
        report_dir = config_output_dir / "report"
        study_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        try:
            config = load_config_json(config_path)
            result = run_ofi_zone_study(
                input_path=input_path,
                output_dir=study_dir,
                columns=columns,
                config=config,
            )
            report = summarize_ofi_experiment(input_dir=study_dir, output_dir=report_dir)
            rows.append(
                _success_row(
                    config_name=config_name,
                    metrics=result["metrics_summary"],
                    report=report,
                    study_dir=study_dir,
                    report_dir=report_dir,
                )
            )
        except Exception as exc:
            if fail_fast:
                raise
            rows.append(
                _failure_row(
                    config_name=config_name,
                    error=exc,
                    study_dir=study_dir,
                    report_dir=report_dir,
                )
            )

    summary_csv = output / "batch_summary.csv"
    summary_json = output / "batch_summary.json"
    _write_summary_csv(summary_csv, rows)
    payload = {
        "input_path": str(Path(input_path)),
        "output_root": str(output),
        "config_count": len(rows),
        "success_count": sum(1 for row in rows if row["status"] == "success"),
        "failure_count": sum(1 for row in rows if row["status"] == "failed"),
        "rows": rows,
    }
    summary_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "batch_summary_csv": str(summary_csv),
        "batch_summary_json": str(summary_json),
        "rows": rows,
    }


def _success_row(
    *,
    config_name: str,
    metrics: dict[str, Any],
    report: dict[str, Any],
    study_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    warnings = list(metrics.get("warnings") or [])
    warnings.extend(list(report.get("warnings") or []))
    row = {
        "config_name": config_name,
        "status": "success",
        "verdict": report.get("verdict"),
        "rows": metrics.get("rows"),
        "zone_count": metrics.get("zone_count"),
        "retest_count": metrics.get("retest_count"),
        "retest_with_confirmation_count": metrics.get("retest_with_confirmation_count"),
        "overall_hit_rate": metrics.get("overall_hit_rate"),
        "avg_return_bps_after_cost": metrics.get("avg_return_bps_after_cost"),
        "median_return_bps_after_cost": metrics.get("median_return_bps_after_cost"),
        "profit_factor_like": metrics.get("profit_factor_like"),
        "warnings_count": len(dict.fromkeys(str(warning) for warning in warnings if warning)),
        "study_output_dir": str(study_dir),
        "report_output_dir": str(report_dir),
        "error_message": "",
    }
    for column, baseline_name in BASELINE_NAMES.items():
        row[column] = _baseline_delta(metrics, baseline_name)
    return _ordered_row(row)


def _failure_row(
    *,
    config_name: str,
    error: Exception,
    study_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    return _ordered_row(
        {
            "config_name": config_name,
            "status": "failed",
            "verdict": "",
            "warnings_count": 0,
            "study_output_dir": str(study_dir),
            "report_output_dir": str(report_dir),
            "error_message": str(error),
        }
    )


def _baseline_delta(metrics: dict[str, Any], baseline_name: str) -> float | None:
    ofi_return = _float_or_none(metrics.get("avg_return_bps_after_cost"))
    baseline = metrics.get("baseline_comparison", {})
    if not isinstance(baseline, dict):
        return None
    baseline_stats = baseline.get(baseline_name, {})
    if not isinstance(baseline_stats, dict):
        return None
    baseline_return = _float_or_none(
        baseline_stats.get(
            "mean_avg_return_bps_after_cost",
            baseline_stats.get("avg_return_bps_after_cost"),
        )
    )
    if ofi_return is None or baseline_return is None:
        return None
    return ofi_return - baseline_return


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(_ordered_row(row) for row in rows)


def _ordered_row(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in BATCH_SUMMARY_COLUMNS}


def _safe_config_name(path: Path) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("._-")
    return name or "config"


def _is_sweep_grid(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and "grid" in payload


def _unique_config_name(name: str, used: set[str]) -> str:
    candidate = name
    index = 2
    while candidate in used:
        candidate = f"{name}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
