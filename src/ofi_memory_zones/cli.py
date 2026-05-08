from __future__ import annotations

import argparse
import json
from pathlib import Path

from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import load_config_json, run_ofi_zone_study


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config_json(args.config_json)
    columns = ColumnMapping(
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
    )
    result = run_ofi_zone_study(
        input_path=args.input,
        output_dir=args.output,
        columns=columns,
        config=config,
    )
    print(json.dumps(result["metrics_summary"], indent=2, ensure_ascii=False))
    print(f"\nWrote OFI zone study outputs to: {Path(args.output).resolve()}")
    if args.no_plots:
        print("Plots disabled (--no-plots).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an OFI Memory Zone / Imbalance-Retest Zone research study."
    )
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--output", required=True, help="Output directory.")
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
    parser.add_argument("--config-json", default=None, help="Optional JSON config override.")
    parser.add_argument("--no-plots", action="store_true", help="Accepted for compatibility; v0 emits CSV/JSON.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
