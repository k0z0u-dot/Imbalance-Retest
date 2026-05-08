from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(slots=True)
class OFIMemoryZoneConfig:
    imbalance_z_threshold: float = 2.0
    robust_z_threshold: float = 2.5
    z_window: int = 100
    min_total_flow_volume: float | None = None
    min_volume_z: float | None = None
    reaction_horizon_bars: int = 20
    min_reaction_bps: float = 5.0
    max_absorption_adverse_bps: float = 3.0
    atr_window: int = 50
    min_reaction_atr: float = 0.2
    price_bin_bps: float = 5.0
    zone_width_bps: float = 8.0
    merge_distance_bps: float = 10.0
    retest_horizon_bars: int = 20
    retest_cooldown_bars: int = 10
    confirmation_window_bars: int = 5
    confirmation_z_threshold: float = 1.5
    target_bps: float = 8.0
    stop_bps: float = 6.0
    fee_bps: float = 1.5
    slippage_bps: float = 1.0
    cost_round_trip: bool = True
    conservative_stop_first: bool = True
    max_zone_age_bars: int | None = 1000
    use_robust_z: bool = True
    require_local_swing: bool = False
    local_swing_window: int = 10
    prior_alpha: float = 6.0
    prior_beta: float = 4.0
    posterior_lower_quantile: float = 0.1
    random_seed: int = 42
    baseline_random_seed: int = 42
    baseline_random_zone_count: int | None = None
    baseline_random_trials: int = 50
    price_near_random_min_offset_bps: float = 10.0
    price_near_random_max_offset_bps: float = 50.0
    swing_window: int = 10
    swing_min_reaction_bps: float = 5.0
    swing_zone_width_bps: float = 8.0
    swing_merge_distance_bps: float = 10.0
    volume_profile_bin_bps: float = 10.0
    volume_profile_top_n: int = 10
    volume_profile_lookback_bars: int = 200
    volume_profile_zone_width_bps: float = 8.0
    split_mode: str = "none"
    train_ratio: float = 0.7
    wf_train_bars: int = 1000
    wf_test_bars: int = 300
    wf_step_bars: int = 300
    eps: float = 1e-9

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "OFIMemoryZoneConfig":
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"Unknown OFI memory zone config key(s): {', '.join(unknown)}")
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
