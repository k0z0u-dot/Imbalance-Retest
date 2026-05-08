from __future__ import annotations

import json

import pandas as pd

from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.sweep import run_ofi_zone_sweep
from ofi_memory_zones.synthetic import generate_synthetic_ofi_data


def test_parameter_sweep_writes_all_and_best_results(tmp_path) -> None:
    input_path = tmp_path / "synthetic.csv"
    grid_path = tmp_path / "grid.json"
    output_dir = tmp_path / "sweep"

    generate_synthetic_ofi_data(output_path=input_path)
    grid_path.write_text(
        json.dumps(
            {
                "grid": {
                    "use_robust_z": [True, False],
                    "imbalance_z_threshold": [2.0],
                    "robust_z_threshold": [2.5],
                    "reaction_horizon_bars": [20],
                    "min_reaction_bps": [5.0],
                    "min_reaction_atr": [0.2],
                    "baseline_random_trials": [2],
                }
            }
        ),
        encoding="utf-8",
    )

    paths = run_ofi_zone_sweep(
        input_path=input_path,
        output_dir=output_dir,
        grid_json_path=grid_path,
        columns=ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"),
        best_limit=1,
    )

    sweep = pd.read_csv(paths["sweep_results"])
    best = pd.read_csv(paths["best_configs"])
    assert len(sweep) == 2
    assert len(best) == 1
    assert "initiative_support_hit_rate" in sweep.columns
    assert "delta_hit_rate_vs_random_zone" in sweep.columns
    assert (output_dir / "config_000" / "metrics_summary.json").exists()
