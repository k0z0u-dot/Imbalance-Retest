from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping


def build_data_diagnostics(
    *,
    raw: pd.DataFrame,
    features: pd.DataFrame,
    metadata: dict[str, object],
    columns: ColumnMapping,
    zones: pd.DataFrame,
    retests: pd.DataFrame,
    baseline_trials: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    split_summary: pd.DataFrame | None = None,
) -> dict[str, object]:
    missing_columns = _missing_columns(raw, columns)
    warnings = _diagnostic_warnings(
        raw=raw,
        features=features,
        metadata=metadata,
        columns=columns,
        zones=zones,
        retests=retests,
        baseline_trials=baseline_trials,
        config=config,
        split_summary=split_summary,
    )
    diagnostics = {
        "rows": int(len(features)),
        "start_timestamp": metadata.get("start_timestamp"),
        "end_timestamp": metadata.get("end_timestamp"),
        "detected_flow_source": metadata.get("flow_source"),
        "proxy_used": bool(metadata.get("proxy_used", False)),
        "missing_columns": missing_columns,
        "null_rate_by_required_column": _null_rates(raw, columns),
        "taker_buy_volume_coverage": _coverage(raw, columns.taker_buy_col),
        "taker_sell_volume_coverage": _coverage(raw, columns.taker_sell_col),
        "signed_volume_coverage": _coverage(raw, columns.signed_volume_col),
        "total_flow_volume_stats": _series_stats(features.get("total_flow_volume")),
        "imbalance_z_stats": _series_stats(features.get("imbalance_z")),
        "robust_imbalance_z_stats": _series_stats(features.get("robust_imbalance_z")),
        "zone_count_by_type": _count_by(zones, "zone_type"),
        "retest_count_by_type": _count_by(retests, "zone_type"),
        "warnings": warnings,
    }
    return _json_ready(diagnostics)


def _missing_columns(raw: pd.DataFrame, columns: ColumnMapping) -> list[str]:
    expected = [
        columns.timestamp_col,
        columns.price_col,
        columns.high_col,
        columns.low_col,
        columns.close_col,
    ]
    return sorted({column for column in expected if column and column not in raw.columns})


def _null_rates(raw: pd.DataFrame, columns: ColumnMapping) -> dict[str, float | None]:
    candidates = [
        columns.timestamp_col,
        columns.price_col,
        columns.high_col,
        columns.low_col,
        columns.close_col,
        columns.taker_buy_col,
        columns.taker_sell_col,
        columns.buy_volume_col,
        columns.sell_volume_col,
        columns.signed_volume_col,
    ]
    rates: dict[str, float | None] = {}
    for column in candidates:
        if not column:
            continue
        rates[column] = float(raw[column].isna().mean()) if column in raw.columns and len(raw) else None
    return rates


def _coverage(raw: pd.DataFrame, column: str | None) -> float:
    if not column or column not in raw.columns or len(raw) == 0:
        return 0.0
    return float(raw[column].notna().mean())


def _series_stats(series: pd.Series | None) -> dict[str, float | int | None]:
    if series is None:
        return {"count": 0, "mean": None, "std": None, "min": None, "median": None, "max": None}
    numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if numeric.empty:
        return {"count": 0, "mean": None, "std": None, "min": None, "median": None, "max": None}
    return {
        "count": int(len(numeric)),
        "mean": float(numeric.mean()),
        "std": float(numeric.std(ddof=0)),
        "min": float(numeric.min()),
        "median": float(numeric.median()),
        "max": float(numeric.max()),
    }


def _count_by(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].value_counts().sort_index().items()}


def _diagnostic_warnings(
    *,
    raw: pd.DataFrame,
    features: pd.DataFrame,
    metadata: dict[str, object],
    columns: ColumnMapping,
    zones: pd.DataFrame,
    retests: pd.DataFrame,
    baseline_trials: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    split_summary: pd.DataFrame | None,
) -> list[str]:
    warnings: list[str] = []
    if len(retests) < 200:
        warnings.append("retest_count < 200")
    if metadata.get("proxy_used"):
        warnings.append("proxy_used=True")
    if not columns.volume_col or columns.volume_col not in raw.columns:
        warnings.append("volume data missing")
    if not columns.high_col or not columns.low_col:
        warnings.append("high/low missing, using close-based outcome")
    if not zones.empty and "zone_type" in zones.columns:
        share = float(zones["zone_type"].value_counts(normalize=True).max())
        if share > 0.8:
            warnings.append("one zone_type dominates more than 80%")
    if int(config.baseline_random_trials) < 20:
        warnings.append("baseline trials too few")
    if features.get("total_flow_volume") is not None:
        total_flow = pd.to_numeric(features["total_flow_volume"], errors="coerce")
        if total_flow.notna().sum() == 0 or float(total_flow.fillna(0).sum()) <= 0.0:
            warnings.append("volume data missing")
    if split_summary is not None and not split_summary.empty:
        if "test_retest_count" in split_summary.columns:
            for value in split_summary["test_retest_count"]:
                try:
                    if float(value) < 50:
                        warnings.append("test period retest_count too low")
                except (TypeError, ValueError):
                    warnings.append("test period retest_count too low")
    if baseline_trials.empty:
        warnings.append("baseline trials missing")
    return sorted(set(warnings))


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
