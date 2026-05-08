from __future__ import annotations

import json

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import run_ofi_zone_study


def test_run_ofi_zone_study_writes_expected_outputs(tmp_path) -> None:
    input_path = tmp_path / "sample.csv"
    output_dir = tmp_path / "study"
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01 10:00:00", periods=8, freq="min"),
            "open": [100.0, 100.0, 100.0, 100.0, 100.08, 100.2, 100.0, 100.04],
            "high": [100.01, 100.01, 100.01, 100.02, 100.10, 100.21, 100.02, 100.10],
            "low": [99.99, 99.99, 99.99, 100.00, 100.07, 100.19, 99.98, 100.02],
            "close": [100.0, 100.0, 100.0, 100.01, 100.08, 100.2, 100.0, 100.08],
            "taker_buy_volume": [5.0, 5.0, 100.0, 5.0, 5.0, 5.0, 20.0, 5.0],
            "taker_sell_volume": [5.0, 5.0, 0.0, 5.0, 5.0, 5.0, 2.0, 5.0],
        }
    )
    data.to_csv(input_path, index=False)

    result = run_ofi_zone_study(
        input_path=input_path,
        output_dir=output_dir,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        config=OFIMemoryZoneConfig(
            use_robust_z=False,
            z_window=2,
            reaction_horizon_bars=2,
            min_reaction_bps=5.0,
            min_reaction_atr=0.0,
            retest_horizon_bars=2,
            retest_cooldown_bars=10,
            target_bps=5.0,
            stop_bps=5.0,
            fee_bps=0.0,
            slippage_bps=0.0,
            baseline_random_trials=2,
        ),
    )

    expected = {
        "ofi_features.csv",
        "zone_events.csv",
        "zones.csv",
        "retests.csv",
        "event_type_summary.csv",
        "confirmation_summary.csv",
        "baseline_summary.csv",
        "baseline_trials.csv",
        "metrics_summary.json",
        "data_diagnostics.json",
        "config.json",
    }
    assert expected == {path.name for path in output_dir.iterdir()}
    metrics = json.loads((output_dir / "metrics_summary.json").read_text(encoding="utf-8"))
    assert metrics["rows"] == 8
    assert metrics["zone_count"] >= 1
    assert "random_zone" in metrics["baseline_comparison"]
    assert result["metrics_summary"]["cost_model"] == "round_trip: 2 * (fee_bps + slippage_bps)"
