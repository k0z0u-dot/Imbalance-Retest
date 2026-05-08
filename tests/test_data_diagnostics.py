from __future__ import annotations

import pandas as pd
import pytest

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import run_ofi_zone_study

pytestmark = pytest.mark.integration


def test_data_diagnostics_reports_proxy_and_low_retest_warnings(tmp_path) -> None:
    input_path = tmp_path / "signed.csv"
    output_dir = tmp_path / "study"
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=30, freq="min"),
            "close": [100.0 + i * 0.001 for i in range(30)],
            "signed_volume": [1.0, -1.0] * 15,
        }
    )
    data.to_csv(input_path, index=False)

    result = run_ofi_zone_study(
        input_path=input_path,
        output_dir=output_dir,
        columns=ColumnMapping(signed_volume_col="signed_volume"),
        config=OFIMemoryZoneConfig(
            z_window=5,
            reaction_horizon_bars=3,
            baseline_random_trials=2,
        ),
    )

    diagnostics = result["data_diagnostics"]
    assert diagnostics["detected_flow_source"] == "signed_proxy"
    assert diagnostics["proxy_used"] is True
    assert "proxy_used=True" in diagnostics["warnings"]
    assert "retest_count < 200" in diagnostics["warnings"]
