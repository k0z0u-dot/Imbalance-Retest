from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.strength import posterior_success, strength_components

SUPPORT_TYPES = {"initiative_support", "absorption_support"}
RESISTANCE_TYPES = {"initiative_resistance", "absorption_resistance"}


def generate_zone_events(
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig | None = None,
) -> pd.DataFrame:
    config = config or OFIMemoryZoneConfig()
    _require_feature_columns(features)
    events: list[dict[str, object]] = []
    horizon = int(config.reaction_horizon_bars)
    if horizon <= 0 or len(features) <= horizon:
        return _empty_zone_events()

    for index in range(0, len(features) - horizon):
        row = features.iloc[index]
        if not _passes_volume_filters(row, config):
            continue
        if config.require_local_swing and not _passes_local_swing(features, index, config):
            continue

        future = features.iloc[index + 1 : index + horizon + 1]
        available_row = features.iloc[index + horizon]
        price = float(row["price"])
        if price <= 0 or not math.isfinite(price):
            continue

        future_high = float(future["high"].max())
        future_low = float(future["low"].min())
        up_bps = (future_high - price) / price * 10000.0
        down_bps = (price - future_low) / price * 10000.0
        atr = max(float(row.get("atr", 0.0)), config.eps)
        up_reaction_atr = (up_bps / 10000.0 * price) / atr
        down_reaction_atr = (down_bps / 10000.0 * price) / atr

        positive_event = _passes_positive_imbalance(row, config)
        negative_event = _passes_negative_imbalance(row, config)

        if positive_event and _valid_reaction(up_bps, up_reaction_atr, config):
            events.append(
                _make_event(
                    row=row,
                    available_row=available_row,
                    zone_type="initiative_support",
                    direction="long",
                    reaction_bps=up_bps,
                    reaction_atr=up_reaction_atr,
                    mfe_bps=up_bps,
                    mae_bps=-down_bps,
                    config=config,
                )
            )
        if (
            negative_event
            and down_bps <= config.max_absorption_adverse_bps
            and _valid_reaction(up_bps, up_reaction_atr, config)
        ):
            events.append(
                _make_event(
                    row=row,
                    available_row=available_row,
                    zone_type="absorption_support",
                    direction="long",
                    reaction_bps=up_bps,
                    reaction_atr=up_reaction_atr,
                    mfe_bps=up_bps,
                    mae_bps=-down_bps,
                    config=config,
                )
            )
        if negative_event and _valid_reaction(down_bps, down_reaction_atr, config):
            events.append(
                _make_event(
                    row=row,
                    available_row=available_row,
                    zone_type="initiative_resistance",
                    direction="short",
                    reaction_bps=down_bps,
                    reaction_atr=down_reaction_atr,
                    mfe_bps=down_bps,
                    mae_bps=-up_bps,
                    config=config,
                )
            )
        if (
            positive_event
            and up_bps <= config.max_absorption_adverse_bps
            and _valid_reaction(down_bps, down_reaction_atr, config)
        ):
            events.append(
                _make_event(
                    row=row,
                    available_row=available_row,
                    zone_type="absorption_resistance",
                    direction="short",
                    reaction_bps=down_bps,
                    reaction_atr=down_reaction_atr,
                    mfe_bps=down_bps,
                    mae_bps=-up_bps,
                    config=config,
                )
            )

    if not events:
        return _empty_zone_events()
    frame = pd.DataFrame(events)
    frame.insert(0, "event_id", np.arange(len(frame), dtype=int))
    frame["zone_id"] = frame["event_id"].astype(int)
    return frame[_zone_event_columns()]


def build_zones_from_events(
    zone_events: pd.DataFrame,
    retests: pd.DataFrame | None = None,
    config: OFIMemoryZoneConfig | None = None,
) -> pd.DataFrame:
    config = config or OFIMemoryZoneConfig()
    if zone_events.empty:
        return _empty_zones()

    retests = retests if retests is not None else pd.DataFrame()
    retest_stats = _retest_stats_by_zone(retests)
    zones: list[dict[str, object]] = []

    for _, event in zone_events.iterrows():
        zone_id = int(event["zone_id"])
        stats = retest_stats.get(zone_id, {})
        retest_count = int(stats.get("retest_count", 0))
        success_count = int(stats.get("success_count", 0))
        failure_count = int(stats.get("failure_count", 0))
        posterior_mean, posterior_lower = posterior_success(success_count, retest_count, config)
        components = strength_components(event, failure_count=failure_count)
        zones.append(
            {
                "zone_id": zone_id,
                "source_event_id": int(event["event_id"]),
                "event_timestamp": event["event_timestamp"],
                "available_from": event["available_from"],
                "zone_center_price": float(event["zone_center_price"]),
                "zone_low": float(event["zone_low"]),
                "zone_high": float(event["zone_high"]),
                "zone_type": event["zone_type"],
                "direction": event["direction"],
                "proxy_used": bool(event["proxy_used"]),
                **components,
                "retest_count": retest_count,
                "success_count": success_count,
                "failure_count": failure_count,
                "posterior_success_mean": posterior_mean,
                "posterior_success_lower": posterior_lower,
                "last_retest_timestamp": stats.get("last_retest_timestamp"),
            }
        )
    return pd.DataFrame(zones)[_zone_columns()]


def direction_for_zone_type(zone_type: str) -> str:
    return "long" if zone_type in SUPPORT_TYPES else "short"


def is_support_zone(zone_type: str) -> bool:
    return zone_type in SUPPORT_TYPES


def is_resistance_zone(zone_type: str) -> bool:
    return zone_type in RESISTANCE_TYPES


def _make_event(
    *,
    row: pd.Series,
    available_row: pd.Series,
    zone_type: str,
    direction: str,
    reaction_bps: float,
    reaction_atr: float,
    mfe_bps: float,
    mae_bps: float,
    config: OFIMemoryZoneConfig,
) -> dict[str, object]:
    price = float(row["price"])
    half_width = price * config.zone_width_bps / 10000.0 / 2.0
    return {
        "event_timestamp": row["timestamp"],
        "available_from": available_row["timestamp"],
        "zone_center_price": price,
        "zone_low": price - half_width,
        "zone_high": price + half_width,
        "zone_type": zone_type,
        "direction": direction,
        "imbalance": float(row["imbalance"]),
        "imbalance_z": _finite_or_nan(row.get("imbalance_z")),
        "robust_imbalance_z": _finite_or_nan(row.get("robust_imbalance_z")),
        "total_flow_volume": float(row["total_flow_volume"]),
        "reaction_bps": float(reaction_bps),
        "reaction_atr": float(reaction_atr),
        "mfe_bps": float(mfe_bps),
        "mae_bps": float(mae_bps),
        "proxy_used": bool(row["proxy_used"]),
        "source_row_index": int(row["source_row_index"]),
    }


def _valid_reaction(
    reaction_bps: float,
    reaction_atr: float,
    config: OFIMemoryZoneConfig,
) -> bool:
    if reaction_bps < config.min_reaction_bps:
        return False
    return reaction_atr >= config.min_reaction_atr


def _passes_positive_imbalance(row: pd.Series, config: OFIMemoryZoneConfig) -> bool:
    score = _selected_z(row, config)
    threshold = config.robust_z_threshold if config.use_robust_z else config.imbalance_z_threshold
    return math.isfinite(score) and score >= threshold


def _passes_negative_imbalance(row: pd.Series, config: OFIMemoryZoneConfig) -> bool:
    score = _selected_z(row, config)
    threshold = config.robust_z_threshold if config.use_robust_z else config.imbalance_z_threshold
    return math.isfinite(score) and score <= -threshold


def _selected_z(row: pd.Series, config: OFIMemoryZoneConfig) -> float:
    if config.use_robust_z:
        robust = float(row.get("robust_imbalance_z", np.nan))
        if math.isfinite(robust):
            return robust
    value = float(row.get("imbalance_z", np.nan))
    return value if math.isfinite(value) else float("nan")


def _passes_volume_filters(row: pd.Series, config: OFIMemoryZoneConfig) -> bool:
    if config.min_total_flow_volume is not None:
        if float(row["total_flow_volume"]) < config.min_total_flow_volume:
            return False
    if config.min_volume_z is not None:
        volume_z = float(row.get("volume_z", np.nan))
        if not math.isfinite(volume_z) or volume_z < config.min_volume_z:
            return False
    return True


def _passes_local_swing(features: pd.DataFrame, index: int, config: OFIMemoryZoneConfig) -> bool:
    start = max(0, index - config.local_swing_window)
    end = min(len(features), index + config.local_swing_window + 1)
    window = features.iloc[start:end]
    row = features.iloc[index]
    is_low = float(row["low"]) <= float(window["low"].min())
    is_high = float(row["high"]) >= float(window["high"].max())
    return bool(is_low or is_high)


def _retest_stats_by_zone(retests: pd.DataFrame) -> dict[int, dict[str, object]]:
    if retests.empty or "zone_id" not in retests.columns:
        return {}
    stats: dict[int, dict[str, object]] = {}
    for zone_id, group in retests.groupby("zone_id"):
        target_hits = group["target_hit"].fillna(False).astype(bool)
        stop_hits = group["stop_hit"].fillna(False).astype(bool)
        failures = stop_hits | (~target_hits & group["timeout"].fillna(False).astype(bool))
        stats[int(zone_id)] = {
            "retest_count": int(len(group)),
            "success_count": int(target_hits.sum()),
            "failure_count": int(failures.sum()),
            "last_retest_timestamp": group["retest_timestamp"].max(),
        }
    return stats


def _finite_or_nan(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def _require_feature_columns(features: pd.DataFrame) -> None:
    required = {
        "timestamp",
        "price",
        "high",
        "low",
        "imbalance",
        "imbalance_z",
        "robust_imbalance_z",
        "total_flow_volume",
        "proxy_used",
        "source_row_index",
        "atr",
    }
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"OFI feature frame is missing required columns: {', '.join(missing)}")


def _empty_zone_events() -> pd.DataFrame:
    return pd.DataFrame(columns=_zone_event_columns())


def _empty_zones() -> pd.DataFrame:
    return pd.DataFrame(columns=_zone_columns())


def _zone_event_columns() -> list[str]:
    return [
        "event_id",
        "zone_id",
        "event_timestamp",
        "available_from",
        "zone_center_price",
        "zone_low",
        "zone_high",
        "zone_type",
        "direction",
        "imbalance",
        "imbalance_z",
        "robust_imbalance_z",
        "total_flow_volume",
        "reaction_bps",
        "reaction_atr",
        "mfe_bps",
        "mae_bps",
        "proxy_used",
        "source_row_index",
    ]


def _zone_columns() -> list[str]:
    return [
        "zone_id",
        "source_event_id",
        "event_timestamp",
        "available_from",
        "zone_center_price",
        "zone_low",
        "zone_high",
        "zone_type",
        "direction",
        "proxy_used",
        "zone_strength",
        "imbalance_strength",
        "reaction_strength",
        "absorption_strength",
        "retest_count",
        "success_count",
        "failure_count",
        "posterior_success_mean",
        "posterior_success_lower",
        "last_retest_timestamp",
    ]
