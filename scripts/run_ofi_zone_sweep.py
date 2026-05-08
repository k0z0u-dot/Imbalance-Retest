from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import load_config_json
from ofi_memory_zones.sweep import run_ofi_zone_sweep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an OFI Memory Zone parameter sweep.")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--output", required=True, help="Output directory.")
    parser.add_argument("--grid-json", required=True, help="JSON grid or list of config overrides.")
    parser.add_argument("--base-config-json", default=None, help="Optional base config JSON.")
    parser.add_argument("--best-limit", type=int, default=20)
    parser.add_argument("--timestamp-col", default="timestamp")
    parser.add_argument("--price-col", default="close")
    parser.add_argument("--high-col", default="high")
    parser.add_argument("--low-col", default="low")
    parser.add_argument("--open-col", default="open")
    parser.add_argument("--close-col", default="close")
    parser.add_argument("--taker-buy-col", default=None)
    parser.add_argument("--taker-sell-col", default=None)
    parser.add_argument("--buy-volume-col", default=None)
    parser.add_argument("--sell-volume-col", default=None)
    parser.add_argument("--signed-volume-col", default=None)
    parser.add_argument("--side-col", default=None)
    parser.add_argument("--size-col", default=None)
    args = parser.parse_args(argv)

    paths = run_ofi_zone_sweep(
        input_path=args.input,
        output_dir=args.output,
        grid_json_path=args.grid_json,
        columns=ColumnMapping(
            timestamp_col=args.timestamp_col,
            price_col=args.price_col,
            high_col=args.high_col,
            low_col=args.low_col,
            open_col=args.open_col,
            close_col=args.close_col,
            taker_buy_col=args.taker_buy_col,
            taker_sell_col=args.taker_sell_col,
            buy_volume_col=args.buy_volume_col,
            sell_volume_col=args.sell_volume_col,
            signed_volume_col=args.signed_volume_col,
            side_col=args.side_col,
            size_col=args.size_col,
        ),
        base_config=load_config_json(args.base_config_json),
        best_limit=args.best_limit,
    )
    print(f"Wrote sweep results to: {paths['sweep_results']}")
    print(f"Wrote ranked configs to: {paths['best_configs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
