from __future__ import annotations

import pandas as pd
import pytest

from ofi_memory_zones.baselines import generate_swing_sr_zones
from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.retests import detect_retests


def _swing_features() -> pd.DataFrame:
    close = [100.0, 99.9, 99.8, 99.6, 99.85, 100.0, 100.1, 100.4, 100.2, 99.56, 99.7]
    high = [100.05, 99.95, 99.85, 99.65, 99.9, 100.05, 100.15, 100.45, 100.25, 99.62, 99.75]
    low = [99.95, 99.85, 99.75, 99.55, 99.8, 99.95, 100.05, 100.35, 100.15, 99.54, 99.65]
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=len(close), freq="min"),
            "bar_index": range(len(close)),
            "price": close,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": [20.0] * len(close),
            "imbalance": [0.0] * len(close),
            "imbalance_z": [0.0] * len(close),
            "robust_imbalance_z": [0.0] * len(close),
            "total_flow_volume": [20.0] * len(close),
            "atr": [0.1] * len(close),
            "proxy_used": [False] * len(close),
            "source_row_index": range(len(close)),
        }
    )


def test_swing_baseline_generates_support_and_resistance() -> None:
    config = OFIMemoryZoneConfig(
        swing_window=2,
        swing_min_reaction_bps=5.0,
        swing_merge_distance_bps=0.0,
        target_bps=5.0,
        stop_bps=5.0,
        fee_bps=0.0,
        slippage_bps=0.0,
        retest_horizon_bars=2,
    )
    zones = generate_swing_sr_zones(_swing_features(), config)

    assert "initiative_support" in set(zones["zone_type"])
    assert "initiative_resistance" in set(zones["zone_type"])


def test_swing_baseline_uses_same_retest_evaluation_conditions() -> None:
    config = OFIMemoryZoneConfig(
        swing_window=2,
        swing_min_reaction_bps=5.0,
        target_bps=5.0,
        stop_bps=5.0,
        fee_bps=0.0,
        slippage_bps=0.0,
        retest_horizon_bars=2,
        retest_cooldown_bars=10,
    )
    features = _swing_features()
    zones = generate_swing_sr_zones(features, config)
    support_zones = zones[zones["zone_type"] == "initiative_support"]
    retests = detect_retests(features, support_zones, config=config)

    assert not retests.empty
    first = retests.iloc[0]
    assert first["target_price"] == pytest.approx(first["entry_price"] * (1 + 5.0 / 10000.0))
    assert first["stop_price"] == pytest.approx(first["entry_price"] * (1 - 5.0 / 10000.0))
