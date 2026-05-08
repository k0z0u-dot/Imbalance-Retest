from __future__ import annotations

import json

import pandas as pd
import pytest

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.synthetic import generate_synthetic_ofi_data
from ofi_memory_zones.study import run_ofi_zone_study

pytestmark = pytest.mark.integration


def test_train_test_split_is_chronological_and_writes_outputs(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    output_dir = tmp_path / "study"
    generate_synthetic_ofi_data(output_path=input_path)

    run_ofi_zone_study(
        input_path=input_path,
        output_dir=output_dir,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        config=OFIMemoryZoneConfig(
            split_mode="train_test",
            train_ratio=0.7,
            baseline_random_trials=2,
        ),
    )

    split_summary = pd.read_csv(output_dir / "split_summary.csv")
    row = split_summary.iloc[0]
    assert pd.Timestamp(row["train_end"]) < pd.Timestamp(row["test_start"])
    assert (output_dir / "train_metrics_summary.json").exists()
    assert (output_dir / "test_metrics_summary.json").exists()
    train_metrics = json.loads((output_dir / "train_metrics_summary.json").read_text(encoding="utf-8"))
    test_metrics = json.loads((output_dir / "test_metrics_summary.json").read_text(encoding="utf-8"))
    assert pd.Timestamp(train_metrics["end_timestamp"]) < pd.Timestamp(test_metrics["start_timestamp"])
