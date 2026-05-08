from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.zones import is_support_zone


def detect_retests(
    features: pd.DataFrame,
    zones: pd.DataFrame,
    config: OFIMemoryZoneConfig | None = None,
) -> pd.DataFrame:
    config = config or OFIMemoryZoneConfig()
    if zones.empty or features.empty:
        return _empty_retests()

    timestamps = pd.to_datetime(features["timestamp"])
    retests: list[dict[str, object]] = []
    last_retest_index: dict[int, int] = {}

    for _, zone in zones.sort_values("available_from").iterrows():
        zone_id = int(zone["zone_id"])
        available_from = pd.to_datetime(zone["available_from"])
        active_start_positions = np.flatnonzero((timestamps >= available_from).to_numpy())
        if len(active_start_positions) == 0:
            continue
        active_start = int(active_start_positions[0])
        active_end = len(features)
        if config.max_zone_age_bars is not None:
            active_end = min(active_end, active_start + int(config.max_zone_age_bars) + 1)

        for index in range(active_start, active_end):
            if index <= int(zone.get("source_event_index", -1)):
                continue
            if zone_id in last_retest_index:
                if index - last_retest_index[zone_id] < config.retest_cooldown_bars:
                    continue
            row = features.iloc[index]
            if not _bar_intersects_zone(row, zone):
                continue

            retest = _make_retest(features, index, zone, config)
            retests.append(retest)
            last_retest_index[zone_id] = index

    if not retests:
        return _empty_retests()
    frame = pd.DataFrame(retests)
    frame.insert(0, "retest_id", np.arange(len(frame), dtype=int))
    return frame[_retest_columns()]


def _make_retest(
    features: pd.DataFrame,
    index: int,
    zone: pd.Series,
    config: OFIMemoryZoneConfig,
) -> dict[str, object]:
    row = features.iloc[index]
    zone_type = str(zone["zone_type"])
    direction = str(zone["direction"])
    entry_price = _entry_price(row, zone)
    target_price, stop_price = _target_stop(entry_price, zone_type, config)
    confirmation = _confirmation(features, index, zone, config)
    outcome = _outcome(features, index, entry_price, target_price, stop_price, zone_type, config)

    return {
        "retest_timestamp": row["timestamp"],
        "zone_id": int(zone["zone_id"]),
        "zone_type": zone_type,
        "direction": direction,
        "entry_price": entry_price,
        "zone_center_price": float(zone["zone_center_price"]),
        "confirmation_type": confirmation["confirmation_type"],
        "confirmation_found": bool(confirmation["confirmation_found"]),
        "confirmation_imbalance_z": confirmation["confirmation_imbalance_z"],
        "target_price": target_price,
        "stop_price": stop_price,
        **outcome,
        "proxy_used": bool(row["proxy_used"]) or bool(zone["proxy_used"]),
    }


def _bar_intersects_zone(row: pd.Series, zone: pd.Series) -> bool:
    return float(row["low"]) <= float(zone["zone_high"]) and float(row["high"]) >= float(
        zone["zone_low"]
    )


def _entry_price(row: pd.Series, zone: pd.Series) -> float:
    close = float(row["close"])
    low = float(zone["zone_low"])
    high = float(zone["zone_high"])
    if math.isfinite(close):
        return min(max(close, low), high)
    return float(zone["zone_center_price"])


def _target_stop(
    entry_price: float,
    zone_type: str,
    config: OFIMemoryZoneConfig,
) -> tuple[float, float]:
    if is_support_zone(zone_type):
        target = entry_price * (1.0 + config.target_bps / 10000.0)
        stop = entry_price * (1.0 - config.stop_bps / 10000.0)
    else:
        target = entry_price * (1.0 - config.target_bps / 10000.0)
        stop = entry_price * (1.0 + config.stop_bps / 10000.0)
    return float(target), float(stop)


def _confirmation(
    features: pd.DataFrame,
    index: int,
    zone: pd.Series,
    config: OFIMemoryZoneConfig,
) -> dict[str, object]:
    end = min(len(features), index + config.confirmation_window_bars + 1)
    window = features.iloc[index:end]
    threshold = config.confirmation_z_threshold
    zone_type = str(zone["zone_type"])

    if zone_type == "initiative_support":
        matches = window[window["imbalance_z"] >= threshold]
        return _confirmation_result(matches, "same_direction_flow")
    if zone_type == "initiative_resistance":
        matches = window[window["imbalance_z"] <= -threshold]
        return _confirmation_result(matches, "same_direction_flow")
    if zone_type == "absorption_support":
        return _absorption_confirmation(
            window=window,
            primary_mask=(window["imbalance_z"] <= -threshold),
            reversal_mask=(window["imbalance_z"] >= threshold),
            breach_mask=(window["low"] < float(zone["zone_low"])),
        )
    if zone_type == "absorption_resistance":
        return _absorption_confirmation(
            window=window,
            primary_mask=(window["imbalance_z"] >= threshold),
            reversal_mask=(window["imbalance_z"] <= -threshold),
            breach_mask=(window["high"] > float(zone["zone_high"])),
        )
    return {
        "confirmation_found": False,
        "confirmation_type": "none",
        "confirmation_imbalance_z": np.nan,
    }


def _confirmation_result(matches: pd.DataFrame, confirmation_type: str) -> dict[str, object]:
    if matches.empty:
        return {
            "confirmation_found": False,
            "confirmation_type": "none",
            "confirmation_imbalance_z": np.nan,
        }
    selected = matches.iloc[0]
    return {
        "confirmation_found": True,
        "confirmation_type": confirmation_type,
        "confirmation_imbalance_z": float(selected["imbalance_z"]),
    }


def _absorption_confirmation(
    *,
    window: pd.DataFrame,
    primary_mask: pd.Series,
    reversal_mask: pd.Series,
    breach_mask: pd.Series,
) -> dict[str, object]:
    if bool(breach_mask.any()):
        return {
            "confirmation_found": False,
            "confirmation_type": "none",
            "confirmation_imbalance_z": np.nan,
        }
    primary_positions = np.flatnonzero(primary_mask.to_numpy())
    if len(primary_positions) == 0:
        return {
            "confirmation_found": False,
            "confirmation_type": "none",
            "confirmation_imbalance_z": np.nan,
        }
    first_primary_pos = int(primary_positions[0])
    after_primary = reversal_mask.iloc[first_primary_pos + 1 :]
    confirmation_type = "absorption_then_reversal" if bool(after_primary.any()) else "absorption_repeated"
    selected = window.iloc[first_primary_pos]
    return {
        "confirmation_found": True,
        "confirmation_type": confirmation_type,
        "confirmation_imbalance_z": float(selected["imbalance_z"]),
    }


def _outcome(
    features: pd.DataFrame,
    index: int,
    entry_price: float,
    target_price: float,
    stop_price: float,
    zone_type: str,
    config: OFIMemoryZoneConfig,
) -> dict[str, object]:
    end = min(len(features), index + config.retest_horizon_bars + 1)
    window = features.iloc[index:end]
    long_side = is_support_zone(zone_type)
    target_hit = False
    stop_hit = False
    timeout = False
    bars_to_outcome = len(window) - 1
    outcome = "timeout"

    for offset, (_, bar) in enumerate(window.iterrows()):
        high = float(bar["high"])
        low = float(bar["low"])
        if long_side:
            hit_target = high >= target_price
            hit_stop = low <= stop_price
        else:
            hit_target = low <= target_price
            hit_stop = high >= stop_price

        if hit_target and hit_stop:
            bars_to_outcome = offset
            if config.conservative_stop_first:
                stop_hit = True
                outcome = "stop_first"
            else:
                target_hit = True
                outcome = "target_first"
            break
        if hit_stop:
            bars_to_outcome = offset
            stop_hit = True
            outcome = "stop_first"
            break
        if hit_target:
            bars_to_outcome = offset
            target_hit = True
            outcome = "target_first"
            break
    else:
        timeout = True

    mfe_bps, mae_bps = _mfe_mae(window, entry_price, long_side)
    raw_return_bps = _raw_return_bps(
        window=window,
        entry_price=entry_price,
        long_side=long_side,
        target_hit=target_hit,
        stop_hit=stop_hit,
        config=config,
    )
    cost = _round_trip_cost_bps(config)
    return {
        "outcome": outcome,
        "target_hit": bool(target_hit),
        "stop_hit": bool(stop_hit),
        "timeout": bool(timeout),
        "bars_to_outcome": int(bars_to_outcome),
        "mfe_bps": float(mfe_bps),
        "mae_bps": float(mae_bps),
        "return_bps_after_cost": float(raw_return_bps - cost),
    }


def _mfe_mae(window: pd.DataFrame, entry_price: float, long_side: bool) -> tuple[float, float]:
    if window.empty:
        return 0.0, 0.0
    if long_side:
        mfe = (float(window["high"].max()) - entry_price) / entry_price * 10000.0
        mae = (float(window["low"].min()) - entry_price) / entry_price * 10000.0
    else:
        mfe = (entry_price - float(window["low"].min())) / entry_price * 10000.0
        mae = (entry_price - float(window["high"].max())) / entry_price * 10000.0
    return float(max(mfe, 0.0)), float(min(mae, 0.0))


def _raw_return_bps(
    *,
    window: pd.DataFrame,
    entry_price: float,
    long_side: bool,
    target_hit: bool,
    stop_hit: bool,
    config: OFIMemoryZoneConfig,
) -> float:
    if target_hit:
        return float(config.target_bps)
    if stop_hit:
        return float(-config.stop_bps)
    final_close = float(window.iloc[-1]["close"]) if len(window) else entry_price
    if long_side:
        return (final_close - entry_price) / entry_price * 10000.0
    return (entry_price - final_close) / entry_price * 10000.0


def _round_trip_cost_bps(config: OFIMemoryZoneConfig) -> float:
    base = config.fee_bps + config.slippage_bps
    return float(2.0 * base if config.cost_round_trip else base)


def _empty_retests() -> pd.DataFrame:
    return pd.DataFrame(columns=_retest_columns())


def _retest_columns() -> list[str]:
    return [
        "retest_id",
        "retest_timestamp",
        "zone_id",
        "zone_type",
        "direction",
        "entry_price",
        "zone_center_price",
        "confirmation_type",
        "confirmation_found",
        "confirmation_imbalance_z",
        "target_price",
        "stop_price",
        "outcome",
        "target_hit",
        "stop_hit",
        "timeout",
        "bars_to_outcome",
        "mfe_bps",
        "mae_bps",
        "return_bps_after_cost",
        "proxy_used",
    ]
