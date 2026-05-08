from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from ofi_memory_zones.evaluation import evaluate_study_quality


def summarize_ofi_experiment(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    sweep: bool = False,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if sweep:
        return summarize_sweep_experiment(input_dir=input_path, output_dir=output_path)
    return summarize_study_experiment(input_dir=input_path, output_dir=output_path)


def summarize_study_experiment(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    metrics = _read_json(input_path / "metrics_summary.json", warnings)
    diagnostics = _read_json(input_path / "data_diagnostics.json", warnings)
    baseline_summary = _read_csv(input_path / "baseline_summary.csv", warnings)
    event_type_summary = _read_csv(input_path / "event_type_summary.csv", warnings)
    confirmation_summary = _read_csv(input_path / "confirmation_summary.csv", warnings)
    split_summary = _read_csv(input_path / "split_summary.csv", warnings, required=False)
    train_metrics = _read_json(input_path / "train_metrics_summary.json", warnings, required=False)
    test_metrics = _read_json(input_path / "test_metrics_summary.json", warnings, required=False)
    walk_forward_results = _read_csv(
        input_path / "walk_forward_results.csv",
        warnings,
        required=False,
    )
    walk_forward_summary = _read_json(
        input_path / "walk_forward_summary.json",
        warnings,
        required=False,
    )

    quality = evaluate_study_quality(
        metrics,
        baseline_summary,
        diagnostics,
        split_summary=split_summary,
        walk_forward_summary=walk_forward_summary,
    )
    warnings.extend(quality.get("warnings", []))

    report = {
        "data_quality": _data_quality(metrics, diagnostics, split_summary),
        "ofi_performance": _ofi_performance(metrics),
        "event_type_breakdown": _records(event_type_summary),
        "confirmation_breakdown": _records(confirmation_summary),
        "baseline_comparison": _records(baseline_summary),
        "oos_walk_forward": _oos_section(
            split_summary=split_summary,
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            walk_forward_results=walk_forward_results,
            walk_forward_summary=walk_forward_summary,
        ),
        "quality_gate": quality,
        "verdict": quality["verdict"],
        "warnings": _unique(warnings),
    }
    _write_report(output_path, report, _study_markdown(report))
    return report


def summarize_sweep_experiment(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    sweep_results = _read_csv(input_path / "sweep_results.csv", warnings)
    robustness_summary = build_sweep_robustness_summary(sweep_results)
    robustness_summary.to_csv(output_path / "sweep_robustness_summary.csv", index=False)
    robustness_markdown = _sweep_robustness_markdown(robustness_summary)
    (output_path / "sweep_robustness_report.md").write_text(
        robustness_markdown,
        encoding="utf-8",
    )
    report = {
        "sweep": True,
        "config_count": int(len(sweep_results)),
        "robustness_summary": _records(robustness_summary),
        "warnings": _unique(warnings),
    }
    _write_report(output_path, report, _sweep_markdown(report, robustness_markdown))
    return report


def build_sweep_robustness_summary(sweep_results: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "section",
        "parameter",
        "value",
        "config_count",
        "eligible_config_count",
        "excluded_low_retest_count_configs",
        "top_20_percent_config_count",
        "top20_median_hit_rate",
        "top20_median_avg_return_bps_after_cost",
        "median_retest_count",
        "positive_return_config_ratio",
        "baseline_exceed_config_ratio",
        "ofi_percentile_ge_80_config_ratio",
    ]
    if sweep_results.empty:
        return pd.DataFrame(columns=columns)

    frame = sweep_results.copy()
    frame["retest_count_num"] = pd.to_numeric(frame.get("retest_count"), errors="coerce")
    frame["avg_return_num"] = pd.to_numeric(
        frame.get("avg_return_bps_after_cost"),
        errors="coerce",
    )
    frame["hit_rate_num"] = pd.to_numeric(frame.get("hit_rate"), errors="coerce")
    frame["baseline_delta_num"] = pd.to_numeric(
        frame.get("delta_avg_return_bps_after_cost_vs_random_zone"),
        errors="coerce",
    )
    frame["ofi_percentile_num"] = pd.to_numeric(
        frame.get("random_zone_ofi_percentile_vs_baseline"),
        errors="coerce",
    )
    eligible = frame[frame["retest_count_num"].fillna(0) >= 200]
    ranking_base = eligible if not eligible.empty else frame
    top_count = max(1, math.ceil(len(ranking_base) * 0.2))
    top20 = ranking_base.sort_values("avg_return_num", ascending=False).head(top_count)

    rows = [
        {
            "section": "global",
            "parameter": "all",
            "value": "all",
            "config_count": int(len(frame)),
            "eligible_config_count": int(len(eligible)),
            "excluded_low_retest_count_configs": int((frame["retest_count_num"].fillna(0) < 200).sum()),
            "top_20_percent_config_count": int(len(top20)),
            "top20_median_hit_rate": _median(top20, "hit_rate_num"),
            "top20_median_avg_return_bps_after_cost": _median(top20, "avg_return_num"),
            "median_retest_count": _median(frame, "retest_count_num"),
            "positive_return_config_ratio": _ratio(frame["avg_return_num"] > 0),
            "baseline_exceed_config_ratio": _ratio(frame["baseline_delta_num"] > 0),
            "ofi_percentile_ge_80_config_ratio": _ratio(frame["ofi_percentile_num"] >= 80),
        }
    ]

    config_columns = _extract_config_columns(frame)
    for parameter in config_columns:
        for value, group in frame.groupby(parameter, dropna=False):
            eligible_group = group[group["retest_count_num"].fillna(0) >= 200]
            ranking_group = eligible_group if not eligible_group.empty else group
            group_top_count = max(1, math.ceil(len(ranking_group) * 0.2))
            group_top20 = ranking_group.sort_values("avg_return_num", ascending=False).head(
                group_top_count
            )
            rows.append(
                {
                    "section": "parameter",
                    "parameter": parameter,
                    "value": str(value),
                    "config_count": int(len(group)),
                    "eligible_config_count": int(len(eligible_group)),
                    "excluded_low_retest_count_configs": int(
                        (group["retest_count_num"].fillna(0) < 200).sum()
                    ),
                    "top_20_percent_config_count": int(len(group_top20)),
                    "top20_median_hit_rate": _median(group_top20, "hit_rate_num"),
                    "top20_median_avg_return_bps_after_cost": _median(
                        group_top20,
                        "avg_return_num",
                    ),
                    "median_retest_count": _median(group, "retest_count_num"),
                    "positive_return_config_ratio": _ratio(group["avg_return_num"] > 0),
                    "baseline_exceed_config_ratio": _ratio(group["baseline_delta_num"] > 0),
                    "ofi_percentile_ge_80_config_ratio": _ratio(group["ofi_percentile_num"] >= 80),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def _extract_config_columns(frame: pd.DataFrame) -> list[str]:
    if "config_json" not in frame.columns:
        return []
    parsed_rows: list[dict[str, Any]] = []
    for raw in frame["config_json"]:
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        parsed_rows.append(parsed)
    configs = pd.DataFrame(parsed_rows)
    if configs.empty:
        return []
    useful: list[str] = []
    for column in configs.columns:
        if configs[column].nunique(dropna=False) > 1:
            safe_column = f"config.{column}"
            frame[safe_column] = configs[column].astype(str)
            useful.append(safe_column)
    return useful


def _data_quality(
    metrics: dict[str, Any],
    diagnostics: dict[str, Any],
    split_summary: pd.DataFrame,
) -> dict[str, Any]:
    test_retest_count = None
    if not split_summary.empty and "test_retest_count" in split_summary.columns:
        test_retest_count = _safe_value(split_summary.iloc[0].get("test_retest_count"))
    return {
        "rows": diagnostics.get("rows", metrics.get("rows")),
        "start_timestamp": diagnostics.get("start_timestamp", metrics.get("start_timestamp")),
        "end_timestamp": diagnostics.get("end_timestamp", metrics.get("end_timestamp")),
        "detected_flow_source": diagnostics.get("detected_flow_source", metrics.get("flow_source")),
        "proxy_used": diagnostics.get("proxy_used", metrics.get("proxy_used")),
        "warnings": diagnostics.get("warnings", metrics.get("warnings", [])),
        "retest_count": metrics.get("retest_count"),
        "test_retest_count": test_retest_count,
    }


def _ofi_performance(metrics: dict[str, Any]) -> dict[str, Any]:
    mfe = _float_or_none(metrics.get("avg_mfe_bps"))
    mae = _float_or_none(metrics.get("avg_mae_bps"))
    return {
        "overall_hit_rate": metrics.get("overall_hit_rate"),
        "avg_return_bps_after_cost": metrics.get("avg_return_bps_after_cost"),
        "median_return_bps_after_cost": metrics.get("median_return_bps_after_cost"),
        "profit_factor_like": metrics.get("profit_factor_like"),
        "avg_mfe_bps": metrics.get("avg_mfe_bps"),
        "avg_mae_bps": metrics.get("avg_mae_bps"),
        "mfe_mae_ratio": (mfe / abs(mae)) if mfe is not None and mae not in (None, 0.0) else None,
    }


def _oos_section(
    *,
    split_summary: pd.DataFrame,
    train_metrics: dict[str, Any],
    test_metrics: dict[str, Any],
    walk_forward_results: pd.DataFrame,
    walk_forward_summary: dict[str, Any],
) -> dict[str, Any]:
    positive_fold_ratio = None
    fold_returns: list[dict[str, Any]] = []
    if not walk_forward_results.empty:
        returns = pd.to_numeric(
            walk_forward_results.get("avg_return_bps_after_cost"),
            errors="coerce",
        )
        positive_fold_ratio = _ratio(returns > 0)
        fold_returns = _records(
            walk_forward_results[
                [
                    column
                    for column in [
                        "fold_id",
                        "avg_return_bps_after_cost",
                        "baseline_delta_return",
                        "baseline_delta_hit_rate",
                    ]
                    if column in walk_forward_results.columns
                ]
            ]
        )
    return {
        "train_return": train_metrics.get("avg_return_bps_after_cost"),
        "test_return": test_metrics.get("avg_return_bps_after_cost"),
        "split_summary": _records(split_summary),
        "walk_forward_summary": walk_forward_summary,
        "fold_returns": fold_returns,
        "positive_fold_ratio": positive_fold_ratio,
    }


def _study_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OFI Memory Zone Experiment Report",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        "This is a research hypothesis verdict, not a trading or execution decision.",
        "",
        "## Data Quality",
        _dict_table(report["data_quality"]),
        "",
        "## OFI Performance",
        _dict_table(report["ofi_performance"]),
        "",
        "## Event Type Breakdown",
        _frame_markdown(pd.DataFrame(report["event_type_breakdown"])),
        "",
        "## Confirmation Breakdown",
        _frame_markdown(pd.DataFrame(report["confirmation_breakdown"])),
        "",
        "## Baseline Comparison",
        _frame_markdown(pd.DataFrame(report["baseline_comparison"])),
        "",
        "## OOS / Walk-forward",
        _dict_table(report["oos_walk_forward"]),
        "",
        "## Quality Gate",
        _dict_table(report["quality_gate"]),
    ]
    return "\n".join(lines) + "\n"


def _sweep_markdown(report: dict[str, Any], robustness_markdown: str) -> str:
    return "\n".join(
        [
            "# OFI Memory Zone Sweep Report",
            "",
            "This report emphasizes parameter-region robustness, not a single best config.",
            "",
            f"Config count: {report['config_count']}",
            "",
            robustness_markdown,
        ]
    )


def _sweep_robustness_markdown(robustness_summary: pd.DataFrame) -> str:
    global_rows = robustness_summary[robustness_summary["section"] == "global"]
    parameter_rows = robustness_summary[robustness_summary["section"] == "parameter"]
    lines = [
        "## Sweep Robustness",
        "",
        "### Global",
        _frame_markdown(global_rows),
        "",
        "### Parameter Stability",
        _frame_markdown(parameter_rows),
    ]
    return "\n".join(lines) + "\n"


def _write_report(output_path: Path, report: dict[str, Any], markdown: str) -> None:
    (output_path / "experiment_report.json").write_text(
        json.dumps(_json_ready(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_path / "experiment_report.md").write_text(markdown, encoding="utf-8")


def _read_json(path: Path, warnings: list[str], required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            warnings.append(f"Missing required file: {path.name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path, warnings: list[str], required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            warnings.append(f"Missing required file: {path.name}")
        return pd.DataFrame()
    return pd.read_csv(path)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return [_json_ready(row) for row in frame.to_dict(orient="records")]


def _dict_table(values: dict[str, Any]) -> str:
    if not values:
        return "_No data._"
    lines = ["| Field | Value |", "|---|---|"]
    for key, value in values.items():
        lines.append(f"| `{key}` | {json.dumps(_json_ready(value), ensure_ascii=False)} |")
    return "\n".join(lines)


def _frame_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No data._"
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = [_markdown_cell(row[column]) for column in frame.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _markdown_cell(value: Any) -> str:
    ready = _json_ready(value)
    if isinstance(ready, (dict, list)):
        text = json.dumps(ready, ensure_ascii=False)
    else:
        text = "" if ready is None else str(ready)
    return text.replace("|", "\\|").replace("\n", " ")


def _median(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_numeric(frame[column], errors="coerce").median()
    return None if pd.isna(value) else float(value)


def _ratio(mask: pd.Series) -> float | None:
    if len(mask) == 0:
        return None
    return float(mask.fillna(False).astype(bool).mean())


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_value(value: Any) -> Any:
    return _json_ready(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return _records(value)
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            number = float(value)
            return number if math.isfinite(number) else None
    except Exception:
        pass
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))
