from __future__ import annotations

import json

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.synthetic import PATTERN_TYPES, generate_synthetic_ofi_data
from ofi_memory_zones.study import run_ofi_zone_study


def test_synthetic_data_study_detects_intended_zone_types(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    output_dir = tmp_path / "study"

    generate_synthetic_ofi_data(output_path=input_path)
    run_ofi_zone_study(
        input_path=input_path,
        output_dir=output_dir,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        config=OFIMemoryZoneConfig(baseline_random_trials=2),
    )

    for filename in [
        "zone_events.csv",
        "zones.csv",
        "retests.csv",
        "metrics_summary.json",
        "baseline_summary.csv",
        "baseline_trials.csv",
        "data_diagnostics.json",
    ]:
        assert (output_dir / filename).exists()

    zone_events = pd.read_csv(output_dir / "zone_events.csv")
    assert set(PATTERN_TYPES).issubset(set(zone_events["zone_type"]))

    baseline_summary = pd.read_csv(output_dir / "baseline_summary.csv")
    assert {"ofi_memory_zone", "random_zone"}.issubset(set(baseline_summary["baseline_name"]))

    metrics = json.loads((output_dir / "metrics_summary.json").read_text(encoding="utf-8"))
    assert "random_zone" in metrics["baseline_comparison"]
    assert metrics["baseline_comparison"]["random_zone"]["zone_count"] > 0
