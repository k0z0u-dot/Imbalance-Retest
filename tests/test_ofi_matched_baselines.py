from __future__ import annotations

import pandas as pd
import pytest

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.synthetic import generate_synthetic_ofi_data
from ofi_memory_zones.study import run_ofi_zone_study

pytestmark = pytest.mark.integration


def test_matched_random_baselines_and_trials_are_reported(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    output_dir = tmp_path / "study"
    generate_synthetic_ofi_data(output_path=input_path)

    run_ofi_zone_study(
        input_path=input_path,
        output_dir=output_dir,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        config=OFIMemoryZoneConfig(baseline_random_trials=3),
    )

    trials = pd.read_csv(output_dir / "baseline_trials.csv")
    summary = pd.read_csv(output_dir / "baseline_summary.csv")
    for baseline_name in [
        "random_zone",
        "time_matched_random_zone",
        "price_near_random_zone",
    ]:
        assert baseline_name in set(trials["baseline_name"])
        assert len(trials[trials["baseline_name"] == baseline_name]) == 3
        row = summary[summary["baseline_name"] == baseline_name].iloc[0]
        assert row["trials"] == 3
        assert pd.notna(row["ofi_percentile_vs_baseline"])


def test_price_near_random_baseline_is_in_summary(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    output_dir = tmp_path / "study"
    generate_synthetic_ofi_data(output_path=input_path)

    run_ofi_zone_study(
        input_path=input_path,
        output_dir=output_dir,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        config=OFIMemoryZoneConfig(
            baseline_random_trials=2,
            price_near_random_min_offset_bps=5.0,
            price_near_random_max_offset_bps=20.0,
        ),
    )

    summary = pd.read_csv(output_dir / "baseline_summary.csv")
    assert "time_matched_random_zone" in set(summary["baseline_name"])
    assert "price_near_random_zone" in set(summary["baseline_name"])
