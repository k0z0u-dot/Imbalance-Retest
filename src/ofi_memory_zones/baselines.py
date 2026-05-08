from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.metrics import summarize_retests
from ofi_memory_zones.retests import detect_retests


RANDOM_BASELINES = [
    "random_zone",
    "time_matched_random_zone",
    "price_near_random_zone",
]


def build_baseline_results(
    *,
    features: pd.DataFrame,
    ofi_zones: pd.DataFrame,
    ofi_retests: pd.DataFrame,
    config: OFIMemoryZoneConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    trial_rows: list[dict[str, object]] = []
    ofi_stats = summarize_retests(ofi_retests)
    trial_rows.append(
        _trial_row(
            baseline_name="ofi_memory_zone",
            trial_id=0,
            zones=ofi_zones,
            stats=ofi_stats,
        )
    )

    random_trials = max(int(config.baseline_random_trials), 1)
    for trial_id in range(random_trials):
        seed = _seed(config, trial_id)
        for baseline_name, zones in [
            (
                "random_zone",
                generate_random_baseline_zones(
                    features,
                    len(ofi_zones),
                    config,
                    seed=seed + 10_000,
                    zone_id_base=1_000_000 + trial_id * 100_000,
                ),
            ),
            (
                "time_matched_random_zone",
                generate_time_matched_random_zones(
                    features,
                    ofi_zones,
                    config,
                    seed=seed + 20_000,
                    zone_id_base=2_000_000 + trial_id * 100_000,
                ),
            ),
            (
                "price_near_random_zone",
                generate_price_near_random_zones(
                    ofi_zones,
                    config,
                    seed=seed + 30_000,
                    zone_id_base=3_000_000 + trial_id * 100_000,
                ),
            ),
        ]:
            retests = detect_retests(features, zones, config=config)
            trial_rows.append(
                _trial_row(
                    baseline_name=baseline_name,
                    trial_id=trial_id,
                    zones=zones,
                    stats=summarize_retests(retests),
                )
            )

    for baseline_name, zones in [
        ("swing_sr_zone", generate_swing_sr_zones(features, config)),
        ("volume_profile_zone", generate_volume_profile_zones(features, config)),
    ]:
        retests = detect_retests(features, zones, config=config)
        trial_rows.append(
            _trial_row(
                baseline_name=baseline_name,
                trial_id=0,
                zones=zones,
                stats=summarize_retests(retests),
            )
        )

    trials = pd.DataFrame(trial_rows, columns=_trial_columns())
    summary = summarize_baseline_trials(trials, ofi_stats)
    return summary, trials


def build_baseline_summary(
    *,
    features: pd.DataFrame,
    ofi_zones: pd.DataFrame,
    ofi_retests: pd.DataFrame,
    config: OFIMemoryZoneConfig,
) -> pd.DataFrame:
    summary, _ = build_baseline_results(
        features=features,
        ofi_zones=ofi_zones,
        ofi_retests=ofi_retests,
        config=config,
    )
    return summary


def summarize_baseline_trials(
    baseline_trials: pd.DataFrame,
    ofi_stats: dict[str, float | int | None],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    ofi_hit_rate = _float_or_none(ofi_stats.get("hit_rate"))
    ofi_return = _float_or_none(ofi_stats.get("avg_return_bps_after_cost"))
    for baseline_name, group in baseline_trials.groupby("baseline_name", sort=False):
        hit_rates = pd.to_numeric(group["hit_rate"], errors="coerce").dropna()
        returns = pd.to_numeric(group["avg_return_bps_after_cost"], errors="coerce").dropna()
        row = {
            "baseline_name": baseline_name,
            "trials": int(len(group)),
            "zone_count": _median_numeric(group, "zone_count"),
            "retest_count": _median_numeric(group, "retest_count"),
            "mean_hit_rate": _mean_series(hit_rates),
            "median_hit_rate": _median_series(hit_rates),
            "std_hit_rate": _std_series(hit_rates),
            "mean_avg_return_bps_after_cost": _mean_series(returns),
            "median_avg_return_bps_after_cost": _median_series(returns),
            "std_avg_return_bps_after_cost": _std_series(returns),
            "ofi_hit_rate": ofi_hit_rate,
            "ofi_avg_return_bps_after_cost": ofi_return,
            "delta_hit_rate_vs_ofi": _delta(_mean_series(hit_rates), ofi_hit_rate),
            "delta_avg_return_vs_ofi": _delta(_mean_series(returns), ofi_return),
            "ofi_percentile_vs_baseline": _percentile(returns, ofi_return),
            # Compatibility aliases for v0.2 consumers.
            "hit_rate": _mean_series(hit_rates),
            "avg_return_bps_after_cost": _mean_series(returns),
            "delta_avg_return_bps_after_cost_vs_ofi": _delta(
                _mean_series(returns),
                ofi_return,
            ),
        }
        if baseline_name == "ofi_memory_zone":
            row["delta_hit_rate_vs_ofi"] = 0.0
            row["delta_avg_return_vs_ofi"] = 0.0
            row["delta_avg_return_bps_after_cost_vs_ofi"] = 0.0
            row["ofi_percentile_vs_baseline"] = 100.0
        rows.append(row)
    return pd.DataFrame(rows, columns=_summary_columns())


def generate_random_baseline_zones(
    features: pd.DataFrame,
    ofi_zone_count: int,
    config: OFIMemoryZoneConfig,
    *,
    seed: int | None = None,
    zone_id_base: int = 1_000_000,
) -> pd.DataFrame:
    columns = _zone_columns()
    if features.empty:
        return pd.DataFrame(columns=columns)

    horizon = max(int(config.reaction_horizon_bars), 1)
    candidate_count = max(len(features) - horizon, 0)
    if candidate_count <= 0:
        return pd.DataFrame(columns=columns)

    requested_count = (
        int(config.baseline_random_zone_count)
        if config.baseline_random_zone_count is not None
        else max(int(ofi_zone_count), 1)
    )
    zone_count = min(requested_count, candidate_count)
    if zone_count <= 0:
        return pd.DataFrame(columns=columns)

    rng = np.random.default_rng(seed if seed is not None else _seed(config, 0))
    sampled_indices = np.sort(rng.choice(np.arange(candidate_count), size=zone_count, replace=False))
    rows: list[dict[str, object]] = []
    for offset, event_index in enumerate(sampled_indices):
        row = features.iloc[int(event_index)]
        available_row = features.iloc[int(event_index) + horizon]
        support = bool(rng.integers(0, 2))
        rows.append(
            _zone_row(
                zone_id=zone_id_base + offset,
                event_timestamp=row["timestamp"],
                available_from=available_row["timestamp"],
                center_price=float(row["price"]),
                zone_type="initiative_support" if support else "initiative_resistance",
                direction="long" if support else "short",
                width_bps=config.zone_width_bps,
                proxy_used=bool(row["proxy_used"]),
            )
        )
    return pd.DataFrame(rows, columns=columns)


def generate_time_matched_random_zones(
    features: pd.DataFrame,
    ofi_zones: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    *,
    seed: int | None = None,
    zone_id_base: int = 2_000_000,
) -> pd.DataFrame:
    if features.empty or ofi_zones.empty:
        return pd.DataFrame(columns=_zone_columns())

    rng = np.random.default_rng(seed if seed is not None else _seed(config, 0))
    prices = pd.to_numeric(features["price"], errors="coerce").dropna().to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for offset, (_, zone) in enumerate(ofi_zones.iterrows()):
        center = float(rng.choice(prices))
        rows.append(
            _zone_row(
                zone_id=zone_id_base + offset,
                event_timestamp=zone["event_timestamp"],
                available_from=zone["available_from"],
                center_price=center,
                zone_type=str(zone["zone_type"]),
                direction=str(zone["direction"]),
                width_bps=config.zone_width_bps,
                proxy_used=bool(zone["proxy_used"]),
            )
        )
    return pd.DataFrame(rows, columns=_zone_columns())


def generate_price_near_random_zones(
    ofi_zones: pd.DataFrame,
    config: OFIMemoryZoneConfig,
    *,
    seed: int | None = None,
    zone_id_base: int = 3_000_000,
) -> pd.DataFrame:
    if ofi_zones.empty:
        return pd.DataFrame(columns=_zone_columns())
    rng = np.random.default_rng(seed if seed is not None else _seed(config, 0))
    min_offset = min(config.price_near_random_min_offset_bps, config.price_near_random_max_offset_bps)
    max_offset = max(config.price_near_random_min_offset_bps, config.price_near_random_max_offset_bps)
    rows: list[dict[str, object]] = []
    for offset, (_, zone) in enumerate(ofi_zones.iterrows()):
        center = float(zone["zone_center_price"])
        offset_bps = float(rng.uniform(min_offset, max_offset))
        sign = -1.0 if bool(rng.integers(0, 2)) else 1.0
        shifted_center = center * (1.0 + sign * offset_bps / 10000.0)
        rows.append(
            _zone_row(
                zone_id=zone_id_base + offset,
                event_timestamp=zone["event_timestamp"],
                available_from=zone["available_from"],
                center_price=shifted_center,
                zone_type=str(zone["zone_type"]),
                direction=str(zone["direction"]),
                width_bps=config.zone_width_bps,
                proxy_used=bool(zone["proxy_used"]),
            )
        )
    return pd.DataFrame(rows, columns=_zone_columns())


def generate_swing_sr_zones(
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig,
) -> pd.DataFrame:
    columns = _zone_columns()
    window = max(int(config.swing_window), 1)
    if len(features) < window * 2 + 1:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    last_center_by_type: dict[str, float] = {}
    for index in range(window, len(features) - window):
        local = features.iloc[index - window : index + window + 1]
        row = features.iloc[index]
        available_row = features.iloc[index + window]
        low = float(row["low"])
        high = float(row["high"])
        if low <= float(local["low"].min()):
            future_high = float(features.iloc[index + 1 : index + window + 1]["high"].max())
            reaction_bps = (future_high - low) / max(low, config.eps) * 10000.0
            if reaction_bps >= config.swing_min_reaction_bps:
                _append_merged_zone(
                    rows,
                    last_center_by_type,
                    zone_type="initiative_support",
                    direction="long",
                    center=low,
                    event_timestamp=row["timestamp"],
                    available_from=available_row["timestamp"],
                    width_bps=config.swing_zone_width_bps,
                    merge_distance_bps=config.swing_merge_distance_bps,
                    proxy_used=bool(row["proxy_used"]),
                    zone_id_base=4_000_000,
                )
        if high >= float(local["high"].max()):
            future_low = float(features.iloc[index + 1 : index + window + 1]["low"].min())
            reaction_bps = (high - future_low) / max(high, config.eps) * 10000.0
            if reaction_bps >= config.swing_min_reaction_bps:
                _append_merged_zone(
                    rows,
                    last_center_by_type,
                    zone_type="initiative_resistance",
                    direction="short",
                    center=high,
                    event_timestamp=row["timestamp"],
                    available_from=available_row["timestamp"],
                    width_bps=config.swing_zone_width_bps,
                    merge_distance_bps=config.swing_merge_distance_bps,
                    proxy_used=bool(row["proxy_used"]),
                    zone_id_base=4_000_000,
                )
    return pd.DataFrame(rows, columns=columns)


def generate_volume_profile_zones(
    features: pd.DataFrame,
    config: OFIMemoryZoneConfig,
) -> pd.DataFrame:
    columns = _zone_columns()
    lookback = max(int(config.volume_profile_lookback_bars), 2)
    top_n = max(int(config.volume_profile_top_n), 1)
    if len(features) < lookback:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    zone_id = 5_000_000
    for end_index in range(lookback - 1, len(features), lookback):
        window = features.iloc[end_index - lookback + 1 : end_index + 1]
        current = features.iloc[end_index]
        current_price = float(current["price"])
        bin_width = current_price * config.volume_profile_bin_bps / 10000.0
        if bin_width <= 0:
            continue
        centers = (np.floor(window["price"].astype(float) / bin_width) * bin_width) + bin_width / 2.0
        volume = pd.to_numeric(window.get("volume", window["total_flow_volume"]), errors="coerce")
        profile = (
            pd.DataFrame({"center": centers, "volume": volume.fillna(window["total_flow_volume"])})
            .groupby("center", as_index=False)["volume"]
            .sum()
            .sort_values("volume", ascending=False)
            .head(top_n)
        )
        for _, level in profile.iterrows():
            center = float(level["center"])
            support = center <= current_price
            rows.append(
                _zone_row(
                    zone_id=zone_id,
                    event_timestamp=window.iloc[0]["timestamp"],
                    available_from=current["timestamp"],
                    center_price=center,
                    zone_type="initiative_support" if support else "initiative_resistance",
                    direction="long" if support else "short",
                    width_bps=config.volume_profile_zone_width_bps,
                    proxy_used=bool(current["proxy_used"]),
                )
            )
            zone_id += 1
    return pd.DataFrame(rows, columns=columns)


def _append_merged_zone(
    rows: list[dict[str, object]],
    last_center_by_type: dict[str, float],
    *,
    zone_type: str,
    direction: str,
    center: float,
    event_timestamp: object,
    available_from: object,
    width_bps: float,
    merge_distance_bps: float,
    proxy_used: bool,
    zone_id_base: int,
) -> None:
    last_center = last_center_by_type.get(zone_type)
    if last_center is not None:
        distance_bps = abs(center - last_center) / max(abs(last_center), 1e-9) * 10000.0
        if distance_bps <= merge_distance_bps:
            return
    last_center_by_type[zone_type] = center
    rows.append(
        _zone_row(
            zone_id=zone_id_base + len(rows),
            event_timestamp=event_timestamp,
            available_from=available_from,
            center_price=center,
            zone_type=zone_type,
            direction=direction,
            width_bps=width_bps,
            proxy_used=proxy_used,
        )
    )


def _zone_row(
    *,
    zone_id: int,
    event_timestamp: object,
    available_from: object,
    center_price: float,
    zone_type: str,
    direction: str,
    width_bps: float,
    proxy_used: bool,
) -> dict[str, object]:
    half_width = center_price * width_bps / 10000.0 / 2.0
    return {
        "zone_id": int(zone_id),
        "source_event_id": -1,
        "event_timestamp": event_timestamp,
        "available_from": available_from,
        "zone_center_price": center_price,
        "zone_low": center_price - half_width,
        "zone_high": center_price + half_width,
        "zone_type": zone_type,
        "direction": direction,
        "proxy_used": bool(proxy_used),
        "zone_strength": np.nan,
        "imbalance_strength": np.nan,
        "reaction_strength": np.nan,
        "absorption_strength": np.nan,
        "retest_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "posterior_success_mean": np.nan,
        "posterior_success_lower": np.nan,
        "last_retest_timestamp": None,
    }


def _trial_row(
    *,
    baseline_name: str,
    trial_id: int,
    zones: pd.DataFrame,
    stats: dict[str, float | int | None],
) -> dict[str, object]:
    return {
        "baseline_name": baseline_name,
        "trial_id": int(trial_id),
        "zone_count": int(len(zones)),
        **stats,
    }


def _seed(config: OFIMemoryZoneConfig, trial_id: int) -> int:
    seed = config.random_seed if config.random_seed != 42 else config.baseline_random_seed
    return int(seed) + int(trial_id)


def _delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return float(value - baseline)


def _float_or_none(value: object) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _mean_series(series: pd.Series) -> float | None:
    return _float_or_none(series.mean()) if len(series) else None


def _median_series(series: pd.Series) -> float | None:
    return _float_or_none(series.median()) if len(series) else None


def _std_series(series: pd.Series) -> float | None:
    return _float_or_none(series.std(ddof=0)) if len(series) else None


def _median_numeric(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return _median_series(values)


def _percentile(baseline_values: pd.Series, ofi_value: float | None) -> float | None:
    if ofi_value is None or baseline_values.empty:
        return None
    values = pd.to_numeric(baseline_values, errors="coerce").dropna()
    if values.empty:
        return None
    return float((values <= ofi_value).mean() * 100.0)


def _trial_columns() -> list[str]:
    return [
        "baseline_name",
        "trial_id",
        "zone_count",
        "retest_count",
        "confirmation_rate",
        "hit_rate",
        "avg_return_bps_after_cost",
        "median_return_bps_after_cost",
        "avg_mfe_bps",
        "avg_mae_bps",
        "avg_bars_to_outcome",
        "profit_factor_like",
    ]


def _summary_columns() -> list[str]:
    return [
        "baseline_name",
        "trials",
        "zone_count",
        "retest_count",
        "mean_hit_rate",
        "median_hit_rate",
        "std_hit_rate",
        "mean_avg_return_bps_after_cost",
        "median_avg_return_bps_after_cost",
        "std_avg_return_bps_after_cost",
        "ofi_hit_rate",
        "ofi_avg_return_bps_after_cost",
        "delta_hit_rate_vs_ofi",
        "delta_avg_return_vs_ofi",
        "ofi_percentile_vs_baseline",
        "hit_rate",
        "avg_return_bps_after_cost",
        "delta_avg_return_bps_after_cost_vs_ofi",
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
