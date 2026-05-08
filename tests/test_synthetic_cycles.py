from __future__ import annotations

import json

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import run_ofi_zone_study
from ofi_memory_zones.synthetic import generate_synthetic_ofi_data


def test_synthetic_cycles_increase_rows_and_keep_timestamps_monotonic(tmp_path) -> None:
    one_cycle = generate_synthetic_ofi_data(output_path=tmp_path / "c1.csv", cycles=1, seed=42)
    five_cycles = generate_synthetic_ofi_data(output_path=tmp_path / "c5.csv", cycles=5, seed=42)

    assert len(five_cycles) == len(one_cycle) * 5
    assert pd.to_datetime(five_cycles["timestamp"]).is_monotonic_increasing


def test_synthetic_cycles_increase_study_zone_and_retest_counts(tmp_path) -> None:
    one_cycle_path = tmp_path / "c1.csv"
    five_cycles_path = tmp_path / "c5.csv"
    generate_synthetic_ofi_data(output_path=one_cycle_path, cycles=1, seed=42)
    generate_synthetic_ofi_data(output_path=five_cycles_path, cycles=5, seed=42)
    config = OFIMemoryZoneConfig(
        baseline_random_trials=1,
        volume_profile_top_n=1,
        volume_profile_lookback_bars=200,
    )
    columns = ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume")

    run_ofi_zone_study(
        input_path=one_cycle_path,
        output_dir=tmp_path / "study_c1",
        columns=columns,
        config=config,
    )
    run_ofi_zone_study(
        input_path=five_cycles_path,
        output_dir=tmp_path / "study_c5",
        columns=columns,
        config=config,
    )
    c1 = json.loads((tmp_path / "study_c1" / "metrics_summary.json").read_text(encoding="utf-8"))
    c5 = json.loads((tmp_path / "study_c5" / "metrics_summary.json").read_text(encoding="utf-8"))
    zone_events = pd.read_csv(tmp_path / "study_c5" / "zone_events.csv")

    assert c5["zone_count"] > c1["zone_count"]
    assert c5["retest_count"] > c1["retest_count"]
    assert c5["retest_count"] >= 50
    assert zone_events["zone_type"].nunique() >= 2
