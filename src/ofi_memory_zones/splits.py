from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ofi_memory_zones.baselines import build_baseline_results
from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.metrics import (
    build_confirmation_summary,
    build_event_type_summary,
    build_metrics_summary,
)
from ofi_memory_zones.retests import detect_retests
from ofi_memory_zones.zones import build_zones_from_events, generate_zone_events


def run_oos_outputs(
    *,
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    output_dir: Path,
    cost_model: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object] | None]:
    split_summary = pd.DataFrame()
    walk_forward_results = pd.DataFrame()
    walk_forward_summary: dict[str, object] | None = None

    if config.split_mode == "train_test":
        train_metrics, test_metrics, split_summary = _run_train_test_split(
            features,
            config,
            cost_model,
        )
        (output_dir / "train_metrics_summary.json").write_text(
            json.dumps(train_metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "test_metrics_summary.json").write_text(
            json.dumps(test_metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        split_summary.to_csv(output_dir / "split_summary.csv", index=False)
    elif config.split_mode == "walk_forward":
        walk_forward_results, walk_forward_summary = _run_walk_forward(
            features,
            config,
            cost_model,
        )
        walk_forward_results.to_csv(output_dir / "walk_forward_results.csv", index=False)
        (output_dir / "walk_forward_summary.json").write_text(
            json.dumps(walk_forward_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    elif config.split_mode != "none":
        raise ValueError("split_mode must be one of: none, train_test, walk_forward")

    return split_summary, walk_forward_results, walk_forward_summary


def _run_train_test_split(
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    cost_model: str,
) -> tuple[dict[str, object], dict[str, object], pd.DataFrame]:
    split_index = int(len(features) * float(config.train_ratio))
    split_index = min(max(split_index, 1), max(len(features) - 1, 1))
    train_features = features.iloc[:split_index].reset_index(drop=True)
    test_features = features.iloc[split_index:].reset_index(drop=True)
    train_metrics = _evaluate_features(train_features, config, cost_model)
    test_metrics = _evaluate_features(test_features, config, cost_model)
    row = {
        "split_mode": "train_test",
        "train_start": _timestamp(train_features, 0),
        "train_end": _timestamp(train_features, -1),
        "test_start": _timestamp(test_features, 0),
        "test_end": _timestamp(test_features, -1),
        "train_zone_count": train_metrics.get("zone_count"),
        "test_zone_count": test_metrics.get("zone_count"),
        "train_retest_count": train_metrics.get("retest_count"),
        "test_retest_count": test_metrics.get("retest_count"),
        "train_hit_rate": train_metrics.get("overall_hit_rate"),
        "test_hit_rate": test_metrics.get("overall_hit_rate"),
        "hit_rate_degradation": _subtract(
            train_metrics.get("overall_hit_rate"),
            test_metrics.get("overall_hit_rate"),
        ),
        "train_avg_return_bps_after_cost": train_metrics.get("avg_return_bps_after_cost"),
        "test_avg_return_bps_after_cost": test_metrics.get("avg_return_bps_after_cost"),
        "avg_return_bps_after_cost_degradation": _subtract(
            train_metrics.get("avg_return_bps_after_cost"),
            test_metrics.get("avg_return_bps_after_cost"),
        ),
    }
    return train_metrics, test_metrics, pd.DataFrame([row])


def _run_walk_forward(
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    cost_model: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    train_bars = max(int(config.wf_train_bars), 1)
    test_bars = max(int(config.wf_test_bars), 1)
    step_bars = max(int(config.wf_step_bars), 1)
    rows: list[dict[str, object]] = []
    fold_id = 0
    start = 0
    while start + train_bars + test_bars <= len(features):
        train = features.iloc[start : start + train_bars].reset_index(drop=True)
        test = features.iloc[start + train_bars : start + train_bars + test_bars].reset_index(
            drop=True
        )
        metrics = _evaluate_features(test, config, cost_model)
        random_stats = metrics.get("baseline_comparison", {}).get("random_zone", {})
        rows.append(
            {
                "fold_id": fold_id,
                "train_start": _timestamp(train, 0),
                "train_end": _timestamp(train, -1),
                "test_start": _timestamp(test, 0),
                "test_end": _timestamp(test, -1),
                "zone_count": metrics.get("zone_count"),
                "retest_count": metrics.get("retest_count"),
                "hit_rate": metrics.get("overall_hit_rate"),
                "avg_return_bps_after_cost": metrics.get("avg_return_bps_after_cost"),
                "baseline_delta_return": _subtract(
                    metrics.get("avg_return_bps_after_cost"),
                    random_stats.get("mean_avg_return_bps_after_cost")
                    if isinstance(random_stats, dict)
                    else None,
                ),
                "baseline_delta_hit_rate": _subtract(
                    metrics.get("overall_hit_rate"),
                    random_stats.get("mean_hit_rate") if isinstance(random_stats, dict) else None,
                ),
            }
        )
        fold_id += 1
        start += step_bars

    frame = pd.DataFrame(rows)
    summary = {
        "folds": int(len(frame)),
        "mean_hit_rate": _mean(frame, "hit_rate"),
        "median_hit_rate": _median(frame, "hit_rate"),
        "mean_avg_return_bps_after_cost": _mean(frame, "avg_return_bps_after_cost"),
        "median_avg_return_bps_after_cost": _median(frame, "avg_return_bps_after_cost"),
        "mean_baseline_delta_return": _mean(frame, "baseline_delta_return"),
        "mean_baseline_delta_hit_rate": _mean(frame, "baseline_delta_hit_rate"),
    }
    return frame, summary


def _evaluate_features(
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    cost_model: str,
) -> dict[str, object]:
    if features.empty:
        metadata = {"rows": 0, "start_timestamp": None, "end_timestamp": None}
    else:
        metadata = {
            "rows": int(len(features)),
            "start_timestamp": pd.to_datetime(features["timestamp"].iloc[0]).isoformat(),
            "end_timestamp": pd.to_datetime(features["timestamp"].iloc[-1]).isoformat(),
            "proxy_used": bool(features["proxy_used"].any()),
            "flow_source": "split_features",
        }
    zone_events = generate_zone_events(features, config=config)
    initial_zones = build_zones_from_events(zone_events, retests=None, config=config)
    retests = detect_retests(features, initial_zones, config=config)
    zones = build_zones_from_events(zone_events, retests=retests, config=config)
    event_type_summary = build_event_type_summary(zones, retests)
    confirmation_summary = build_confirmation_summary(retests)
    baseline_summary, _ = build_baseline_results(
        features=features,
        ofi_zones=zones,
        ofi_retests=retests,
        config=config,
    )
    warnings = []
    if retests.empty:
        warnings.append("No retests were detected in this split.")
    return build_metrics_summary(
        features=features,
        zones=zones,
        retests=retests,
        metadata=metadata,
        event_type_summary=event_type_summary,
        confirmation_summary=confirmation_summary,
        baseline_summary=baseline_summary,
        warnings=warnings,
        cost_model=cost_model,
    )


def _timestamp(frame: pd.DataFrame, index: int) -> str | None:
    if frame.empty:
        return None
    return pd.to_datetime(frame["timestamp"].iloc[index]).isoformat()


def _subtract(left: Any, right: Any) -> float | None:
    try:
        if left is None or right is None:
            return None
        return float(left) - float(right)
    except (TypeError, ValueError):
        return None


def _mean(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_numeric(frame[column], errors="coerce").mean()
    return None if pd.isna(value) else float(value)


def _median(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_numeric(frame[column], errors="coerce").median()
    return None if pd.isna(value) else float(value)
