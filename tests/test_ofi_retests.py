from __future__ import annotations

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.retests import detect_retests


def _features(highs: list[float], lows: list[float], closes: list[float]) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01 10:00:00", periods=len(closes), freq="min")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "bar_index": range(len(closes)),
            "price": closes,
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "imbalance": [0.0] * len(closes),
            "imbalance_z": [0.0] * len(closes),
            "robust_imbalance_z": [0.0] * len(closes),
            "total_flow_volume": [10.0] * len(closes),
            "atr": [0.1] * len(closes),
            "proxy_used": [False] * len(closes),
            "source_row_index": range(len(closes)),
        }
    )


def _zone(zone_type: str = "initiative_support", available_from=None) -> pd.DataFrame:
    if available_from is None:
        available_from = pd.Timestamp("2026-01-01 10:02:00")
    direction = "long" if "support" in zone_type else "short"
    return pd.DataFrame(
        [
            {
                "zone_id": 1,
                "source_event_id": 0,
                "event_timestamp": pd.Timestamp("2026-01-01 10:00:00"),
                "available_from": available_from,
                "zone_center_price": 100.0,
                "zone_low": 99.95,
                "zone_high": 100.05,
                "zone_type": zone_type,
                "direction": direction,
                "proxy_used": False,
                "zone_strength": 1.0,
                "imbalance_strength": 3.0,
                "reaction_strength": 1.0,
                "absorption_strength": 0.0,
                "retest_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "posterior_success_mean": 0.6,
                "posterior_success_lower": None,
                "last_retest_timestamp": None,
            }
        ]
    )


def _config() -> OFIMemoryZoneConfig:
    return OFIMemoryZoneConfig(
        target_bps=5.0,
        stop_bps=5.0,
        fee_bps=0.0,
        slippage_bps=0.0,
        retest_horizon_bars=3,
        retest_cooldown_bars=10,
    )


def test_price_entering_zone_generates_retest() -> None:
    features = _features(
        highs=[99.8, 99.9, 100.02, 100.06],
        lows=[99.7, 99.8, 99.98, 100.00],
        closes=[99.75, 99.85, 100.0, 100.04],
    )

    retests = detect_retests(features, _zone(), _config())

    assert len(retests) == 1
    assert retests.loc[0, "retest_timestamp"] == features.loc[2, "timestamp"]


def test_retest_before_available_from_is_ignored() -> None:
    features = _features(
        highs=[100.02, 100.03, 99.90, 99.92],
        lows=[99.98, 99.99, 99.80, 99.82],
        closes=[100.0, 100.01, 99.85, 99.90],
    )
    zone = _zone(available_from=pd.Timestamp("2026-01-01 10:02:00"))

    retests = detect_retests(features, zone, _config())

    assert retests.empty


def test_support_target_first_is_success() -> None:
    features = _features(
        highs=[99.8, 99.9, 100.02, 100.06],
        lows=[99.7, 99.8, 99.98, 99.99],
        closes=[99.75, 99.85, 100.0, 100.04],
    )

    retests = detect_retests(features, _zone("initiative_support"), _config())

    assert bool(retests.loc[0, "target_hit"]) is True
    assert retests.loc[0, "outcome"] == "target_first"


def test_support_stop_first_is_failure() -> None:
    features = _features(
        highs=[99.8, 99.9, 100.02, 100.01],
        lows=[99.7, 99.8, 99.98, 99.94],
        closes=[99.75, 99.85, 100.0, 99.96],
    )

    retests = detect_retests(features, _zone("initiative_support"), _config())

    assert bool(retests.loc[0, "stop_hit"]) is True
    assert retests.loc[0, "outcome"] == "stop_first"


def test_resistance_target_and_stop_are_reversed() -> None:
    features = _features(
        highs=[100.2, 100.1, 100.02, 100.01],
        lows=[100.1, 100.08, 99.98, 99.94],
        closes=[100.15, 100.09, 100.0, 99.96],
    )

    retests = detect_retests(features, _zone("initiative_resistance"), _config())

    assert bool(retests.loc[0, "target_hit"]) is True
    assert bool(retests.loc[0, "stop_hit"]) is False
    assert retests.loc[0, "target_price"] < retests.loc[0, "entry_price"]
    assert retests.loc[0, "stop_price"] > retests.loc[0, "entry_price"]


def test_same_bar_target_and_stop_uses_conservative_stop_first() -> None:
    features = _features(
        highs=[99.8, 99.9, 100.06, 100.0],
        lows=[99.7, 99.8, 99.94, 99.99],
        closes=[99.75, 99.85, 100.0, 100.0],
    )

    retests = detect_retests(features, _zone("initiative_support"), _config())

    assert bool(retests.loc[0, "target_hit"]) is False
    assert bool(retests.loc[0, "stop_hit"]) is True
    assert retests.loc[0, "outcome"] == "stop_first"
