from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.features import OFIDataError, build_ofi_features
from ofi_memory_zones.schema import ColumnMapping


def test_taker_buy_sell_imbalance_is_calculated() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="min"),
            "close": [100.0, 100.1, 100.2],
            "high": [100.1, 100.2, 100.3],
            "low": [99.9, 100.0, 100.1],
            "taker_buy_volume": [10.0, 2.0, 0.0],
            "taker_sell_volume": [5.0, 6.0, 4.0],
        }
    )

    features, metadata = build_ofi_features(
        data,
        ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        OFIMemoryZoneConfig(z_window=2),
    )

    assert features.loc[0, "imbalance"] == pytest.approx((10.0 - 5.0) / 15.0)
    assert features.loc[1, "signed_volume"] == pytest.approx(-4.0)
    assert features.loc[2, "total_flow_volume"] == pytest.approx(4.0)
    assert metadata["flow_source"] == "taker"
    assert metadata["proxy_used"] is False


def test_signed_volume_proxy_marks_proxy_used() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="min"),
            "close": [100.0, 99.9],
            "signed_volume": [7.0, -3.0],
        }
    )

    features, metadata = build_ofi_features(
        data,
        ColumnMapping(signed_volume_col="signed_volume"),
        OFIMemoryZoneConfig(z_window=2),
    )

    assert features.loc[0, "taker_buy_volume"] == pytest.approx(7.0)
    assert features.loc[0, "taker_sell_volume"] == pytest.approx(0.0)
    assert features.loc[1, "taker_buy_volume"] == pytest.approx(0.0)
    assert features.loc[1, "taker_sell_volume"] == pytest.approx(3.0)
    assert features["proxy_used"].all()
    assert metadata["proxy_used"] is True


def test_missing_flow_information_raises_clear_error() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="min"),
            "close": [100.0, 100.1],
        }
    )

    with pytest.raises(OFIDataError, match="No usable OFI flow columns"):
        build_ofi_features(data, ColumnMapping(), OFIMemoryZoneConfig())


def test_robust_z_avoids_inf_values() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=8, freq="min"),
            "close": np.linspace(100.0, 100.7, 8),
            "signed_volume": [0.0, 0.0, 0.0, 0.0, 5.0, -5.0, 0.0, 1.0],
        }
    )

    features, _ = build_ofi_features(
        data,
        ColumnMapping(signed_volume_col="signed_volume"),
        OFIMemoryZoneConfig(z_window=3),
    )

    finite_or_nan = features["robust_imbalance_z"].replace([np.inf, -np.inf], np.nan)
    assert features["robust_imbalance_z"].isna().sum() >= 1
    assert finite_or_nan.equals(features["robust_imbalance_z"])
