from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def build_event_type_summary(zones: pd.DataFrame, retests: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "zone_type",
        "zone_count",
        "retest_count",
        "confirmation_rate",
        "hit_rate",
        "avg_return_bps_after_cost",
        "median_return_bps_after_cost",
        "avg_mfe_bps",
        "avg_mae_bps",
        "avg_bars_to_outcome",
    ]
    zone_types = sorted(set(zones.get("zone_type", pd.Series(dtype=str)).dropna().astype(str)))
    rows: list[dict[str, object]] = []
    for zone_type in zone_types:
        zone_count = int((zones["zone_type"] == zone_type).sum()) if not zones.empty else 0
        group = retests[retests["zone_type"] == zone_type] if not retests.empty else pd.DataFrame()
        rows.append(
            {
                "zone_type": zone_type,
                "zone_count": zone_count,
                "retest_count": int(len(group)),
                "confirmation_rate": _mean_bool(group, "confirmation_found"),
                "hit_rate": _mean_bool(group, "target_hit"),
                "avg_return_bps_after_cost": _mean(group, "return_bps_after_cost"),
                "median_return_bps_after_cost": _median(group, "return_bps_after_cost"),
                "avg_mfe_bps": _mean(group, "mfe_bps"),
                "avg_mae_bps": _mean(group, "mae_bps"),
                "avg_bars_to_outcome": _mean(group, "bars_to_outcome"),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_confirmation_summary(retests: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "confirmation_type",
        "retest_count",
        "hit_rate",
        "avg_return_bps_after_cost",
        "median_return_bps_after_cost",
        "avg_mfe_bps",
        "avg_mae_bps",
    ]
    if retests.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    for confirmation_type, group in retests.groupby("confirmation_type", dropna=False):
        rows.append(
            {
                "confirmation_type": confirmation_type,
                "retest_count": int(len(group)),
                "hit_rate": _mean_bool(group, "target_hit"),
                "avg_return_bps_after_cost": _mean(group, "return_bps_after_cost"),
                "median_return_bps_after_cost": _median(group, "return_bps_after_cost"),
                "avg_mfe_bps": _mean(group, "mfe_bps"),
                "avg_mae_bps": _mean(group, "mae_bps"),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_metrics_summary(
    *,
    features: pd.DataFrame,
    zones: pd.DataFrame,
    retests: pd.DataFrame,
    metadata: dict[str, object],
    event_type_summary: pd.DataFrame,
    confirmation_summary: pd.DataFrame,
    baseline_summary: pd.DataFrame | None = None,
    warnings: list[str] | None = None,
    cost_model: str = "round_trip",
) -> dict[str, object]:
    warnings = warnings or []
    confirmed = (
        retests[retests["confirmation_found"].fillna(False).astype(bool)]
        if not retests.empty
        else pd.DataFrame()
    )
    summary = {
        "rows": int(len(features)),
        "start_timestamp": metadata.get("start_timestamp"),
        "end_timestamp": metadata.get("end_timestamp"),
        "proxy_used": bool(metadata.get("proxy_used", False)),
        "flow_source": metadata.get("flow_source"),
        "zone_count": int(len(zones)),
        "retest_count": int(len(retests)),
        "retest_with_confirmation_count": int(len(confirmed)),
        "overall_hit_rate": _mean_bool(retests, "target_hit"),
        "hit_rate_after_confirmation": _mean_bool(confirmed, "target_hit"),
        "avg_return_bps_after_cost": _mean(retests, "return_bps_after_cost"),
        "median_return_bps_after_cost": _median(retests, "return_bps_after_cost"),
        "avg_mfe_bps": _mean(retests, "mfe_bps"),
        "avg_mae_bps": _mean(retests, "mae_bps"),
        "profit_factor_like": _profit_factor_like(retests),
        "cost_model": cost_model,
        "by_zone_type": _records_by_key(event_type_summary, "zone_type"),
        "by_confirmation_type": _records_by_key(confirmation_summary, "confirmation_type"),
        "baseline_comparison": _records_by_key(
            baseline_summary if baseline_summary is not None else pd.DataFrame(),
            "baseline_name",
        ),
        "warnings": warnings,
    }
    return _json_ready(summary)


def summarize_retests(retests: pd.DataFrame) -> dict[str, float | int | None]:
    return {
        "retest_count": int(len(retests)),
        "confirmation_rate": _mean_bool(retests, "confirmation_found"),
        "hit_rate": _mean_bool(retests, "target_hit"),
        "avg_return_bps_after_cost": _mean(retests, "return_bps_after_cost"),
        "median_return_bps_after_cost": _median(retests, "return_bps_after_cost"),
        "avg_mfe_bps": _mean(retests, "mfe_bps"),
        "avg_mae_bps": _mean(retests, "mae_bps"),
        "avg_bars_to_outcome": _mean(retests, "bars_to_outcome"),
        "profit_factor_like": profit_factor_like(retests),
    }


def _records_by_key(frame: pd.DataFrame, key: str) -> dict[str, dict[str, object]]:
    if frame.empty or key not in frame.columns:
        return {}
    records: dict[str, dict[str, object]] = {}
    for _, row in frame.iterrows():
        row_dict = row.to_dict()
        name = str(row_dict.pop(key))
        records[name] = _json_ready(row_dict)
    return records


def profit_factor_like(retests: pd.DataFrame) -> float | None:
    if retests.empty or "return_bps_after_cost" not in retests.columns:
        return None
    returns = pd.to_numeric(retests["return_bps_after_cost"], errors="coerce").dropna()
    positive = float(returns[returns > 0].sum())
    negative = float(returns[returns < 0].sum())
    if negative == 0.0:
        return None if positive == 0.0 else float("inf")
    return positive / abs(negative)


def _profit_factor_like(retests: pd.DataFrame) -> float | None:
    return profit_factor_like(retests)


def _mean_bool(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    return _safe_float(frame[column].fillna(False).astype(bool).mean())


def _mean(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    return _safe_float(pd.to_numeric(frame[column], errors="coerce").mean())


def _median(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    return _safe_float(pd.to_numeric(frame[column], errors="coerce").median())


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
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
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value
