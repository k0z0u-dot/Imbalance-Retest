from __future__ import annotations

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.zones import generate_zone_events


def _features_for_event(
    *,
    event_z: float,
    future_high: float,
    future_low: float,
    event_price: float = 100.0,
) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01 10:00:00", periods=6, freq="min")
    prices = [100.0, 100.0, event_price, event_price, event_price, event_price]
    highs = [100.01, 100.01, event_price + 0.01, event_price + 0.01, future_high, event_price]
    lows = [99.99, 99.99, event_price - 0.01, event_price - 0.01, future_low, event_price]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "bar_index": range(6),
            "price": prices,
            "open": prices,
            "high": highs,
            "low": lows,
            "close": prices,
            "imbalance": [0.0, 0.0, 0.8 if event_z > 0 else -0.8, 0.0, 0.0, 0.0],
            "imbalance_z": [0.0, 0.0, event_z, 0.0, 0.0, 0.0],
            "robust_imbalance_z": [0.0, 0.0, event_z, 0.0, 0.0, 0.0],
            "total_flow_volume": [10.0, 10.0, 100.0, 10.0, 10.0, 10.0],
            "volume_z": [0.0] * 6,
            "atr": [0.1] * 6,
            "proxy_used": [False] * 6,
            "source_row_index": range(6),
        }
    )


def _config() -> OFIMemoryZoneConfig:
    return OFIMemoryZoneConfig(
        use_robust_z=False,
        imbalance_z_threshold=2.0,
        reaction_horizon_bars=2,
        min_reaction_bps=5.0,
        max_absorption_adverse_bps=3.0,
        min_reaction_atr=0.0,
    )


def test_buy_imbalance_future_up_generates_initiative_support() -> None:
    events = generate_zone_events(
        _features_for_event(event_z=3.0, future_high=100.10, future_low=99.99),
        _config(),
    )

    assert "initiative_support" in set(events["zone_type"])


def test_sell_imbalance_downside_failure_future_up_generates_absorption_support() -> None:
    events = generate_zone_events(
        _features_for_event(event_z=-3.0, future_high=100.10, future_low=99.98),
        _config(),
    )

    assert "absorption_support" in set(events["zone_type"])


def test_sell_imbalance_future_down_generates_initiative_resistance() -> None:
    events = generate_zone_events(
        _features_for_event(event_z=-3.0, future_high=100.01, future_low=99.90),
        _config(),
    )

    assert "initiative_resistance" in set(events["zone_type"])


def test_buy_imbalance_upside_failure_future_down_generates_absorption_resistance() -> None:
    events = generate_zone_events(
        _features_for_event(event_z=3.0, future_high=100.02, future_low=99.90),
        _config(),
    )

    assert "absorption_resistance" in set(events["zone_type"])


def test_available_from_is_after_reaction_horizon() -> None:
    features = _features_for_event(event_z=3.0, future_high=100.10, future_low=99.99)
    events = generate_zone_events(features, _config())
    event = events[events["zone_type"] == "initiative_support"].iloc[0]

    assert event["event_timestamp"] == features.loc[2, "timestamp"]
    assert event["available_from"] == features.loc[4, "timestamp"]
    assert event["available_from"] > event["event_timestamp"]
