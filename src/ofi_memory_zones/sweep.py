from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import run_ofi_zone_study


ZONE_TYPES = [
    "initiative_support",
    "absorption_support",
    "initiative_resistance",
    "absorption_resistance",
]


def run_ofi_zone_sweep(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    grid_json_path: str | Path,
    columns: ColumnMapping | None = None,
    base_config: OFIMemoryZoneConfig | None = None,
    best_limit: int = 20,
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    configs = load_sweep_configs(grid_json_path, base_config or OFIMemoryZoneConfig())

    rows: list[dict[str, object]] = []
    for config_index, config in enumerate(configs):
        config_id = f"config_{config_index:03d}"
        study_output = output / config_id
        result = run_ofi_zone_study(
            input_path=input_path,
            output_dir=study_output,
            columns=columns,
            config=config,
        )
        rows.append(_sweep_row(config_id, config, result["metrics_summary"]))

    sweep_results = pd.DataFrame(rows)
    sweep_path = output / "sweep_results.csv"
    best_path = output / "best_configs.csv"
    sweep_results.to_csv(sweep_path, index=False)
    _best_configs(sweep_results, best_limit).to_csv(best_path, index=False)
    return {"sweep_results": str(sweep_path), "best_configs": str(best_path)}


def load_sweep_configs(
    grid_json_path: str | Path,
    base_config: OFIMemoryZoneConfig,
) -> list[OFIMemoryZoneConfig]:
    payload = json.loads(Path(grid_json_path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        overrides = payload
    elif isinstance(payload, dict):
        grid = payload.get("grid", payload)
        if not isinstance(grid, dict):
            raise ValueError("Sweep JSON 'grid' must be an object.")
        overrides = _expand_grid(grid)
    else:
        raise ValueError("Sweep JSON must be an object grid or a list of config overrides.")

    configs: list[OFIMemoryZoneConfig] = []
    base_values = base_config.to_dict()
    for override in overrides:
        if not isinstance(override, dict):
            raise ValueError("Each sweep config override must be a JSON object.")
        values = {**base_values, **override}
        configs.append(OFIMemoryZoneConfig.from_dict(values))
    if not configs:
        raise ValueError("Sweep grid produced no configurations.")
    return configs


def _expand_grid(grid: dict[str, Any]) -> list[dict[str, Any]]:
    keys = list(grid)
    values_by_key = [value if isinstance(value, list) else [value] for value in grid.values()]
    return [dict(zip(keys, values)) for values in itertools.product(*values_by_key)]


def _sweep_row(
    config_id: str,
    config: OFIMemoryZoneConfig,
    metrics: dict[str, Any],
) -> dict[str, object]:
    row: dict[str, object] = {
        "config_id": config_id,
        "zone_count": metrics.get("zone_count"),
        "retest_count": metrics.get("retest_count"),
        "confirmation_rate": _safe_div(
            metrics.get("retest_with_confirmation_count"),
            metrics.get("retest_count"),
        ),
        "hit_rate": metrics.get("overall_hit_rate"),
        "avg_return_bps_after_cost": metrics.get("avg_return_bps_after_cost"),
        "median_return_bps_after_cost": metrics.get("median_return_bps_after_cost"),
        "avg_mfe_bps": metrics.get("avg_mfe_bps"),
        "avg_mae_bps": metrics.get("avg_mae_bps"),
        "profit_factor_like": metrics.get("profit_factor_like"),
        "config_json": json.dumps(config.to_dict(), sort_keys=True),
    }
    by_zone_type = metrics.get("by_zone_type", {})
    if isinstance(by_zone_type, dict):
        for zone_type in ZONE_TYPES:
            stats = by_zone_type.get(zone_type, {})
            if not isinstance(stats, dict):
                stats = {}
            prefix = zone_type
            row[f"{prefix}_zone_count"] = stats.get("zone_count")
            row[f"{prefix}_retest_count"] = stats.get("retest_count")
            row[f"{prefix}_hit_rate"] = stats.get("hit_rate")
            row[f"{prefix}_avg_return_bps_after_cost"] = stats.get(
                "avg_return_bps_after_cost"
            )
            row[f"{prefix}_avg_mfe_bps"] = stats.get("avg_mfe_bps")
            row[f"{prefix}_avg_mae_bps"] = stats.get("avg_mae_bps")
    baseline = metrics.get("baseline_comparison", {})
    if isinstance(baseline, dict):
        for baseline_name in [
            "random_zone",
            "time_matched_random_zone",
            "price_near_random_zone",
            "swing_sr_zone",
            "volume_profile_zone",
        ]:
            stats = baseline.get(baseline_name, {})
            if not isinstance(stats, dict):
                continue
            prefix = baseline_name
            baseline_hit_rate = stats.get("mean_hit_rate", stats.get("hit_rate"))
            baseline_return = stats.get(
                "mean_avg_return_bps_after_cost",
                stats.get("avg_return_bps_after_cost"),
            )
            row[f"{prefix}_hit_rate"] = baseline_hit_rate
            row[f"{prefix}_avg_return_bps_after_cost"] = baseline_return
            row[f"{prefix}_ofi_percentile_vs_baseline"] = stats.get(
                "ofi_percentile_vs_baseline"
            )
            row[f"delta_hit_rate_vs_{prefix}"] = _delta(
                metrics.get("overall_hit_rate"),
                baseline_hit_rate,
            )
            row[f"delta_avg_return_bps_after_cost_vs_{prefix}"] = _delta(
                metrics.get("avg_return_bps_after_cost"),
                baseline_return,
            )
    return row


def _best_configs(sweep_results: pd.DataFrame, best_limit: int) -> pd.DataFrame:
    if sweep_results.empty:
        return sweep_results
    sortable = sweep_results.copy()
    sortable["_avg_return_sort"] = pd.to_numeric(
        sortable["avg_return_bps_after_cost"],
        errors="coerce",
    ).fillna(float("-inf"))
    sortable["_hit_rate_sort"] = pd.to_numeric(sortable["hit_rate"], errors="coerce").fillna(-1.0)
    sortable["_retest_sort"] = pd.to_numeric(sortable["retest_count"], errors="coerce").fillna(0)
    sortable = sortable.sort_values(
        ["_avg_return_sort", "_hit_rate_sort", "_retest_sort"],
        ascending=[False, False, False],
    )
    return sortable.drop(columns=["_avg_return_sort", "_hit_rate_sort", "_retest_sort"]).head(
        best_limit
    )


def _safe_div(numerator: object, denominator: object) -> float | None:
    try:
        denominator_float = float(denominator)
        if denominator_float == 0.0:
            return None
        return float(numerator) / denominator_float
    except (TypeError, ValueError):
        return None


def _delta(value: object, baseline: object) -> float | None:
    try:
        if value is None or baseline is None:
            return None
        return float(value) - float(baseline)
    except (TypeError, ValueError):
        return None
