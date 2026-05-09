from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofi_memory_zones.batch import discover_config_paths, run_ofi_experiment_batch
from ofi_memory_zones.schema import ColumnMapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run multiple OFI study configs as a batch.")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--output-root", required=True, help="Batch output root directory.")
    parser.add_argument("--config", action="append", default=[], help="Config JSON path.")
    parser.add_argument("--config-dir", default=None, help="Directory to discover config JSON files.")
    parser.add_argument("--pattern", default="*.json", help="Glob pattern used with --config-dir.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first failed config.")
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

    config_paths = discover_config_paths(
        config_paths=args.config,
        config_dir=args.config_dir,
        pattern=args.pattern,
    )
    result = run_ofi_experiment_batch(
        input_path=args.input,
        output_root=args.output_root,
        config_paths=config_paths,
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
        fail_fast=args.fail_fast,
    )
    print(f"Wrote batch summary CSV to: {result['batch_summary_csv']}")
    print(f"Wrote batch summary JSON to: {result['batch_summary_json']}")
    print(
        "Batch result: "
        f"{sum(1 for row in result['rows'] if row['status'] == 'success')} succeeded, "
        f"{sum(1 for row in result['rows'] if row['status'] == 'failed')} failed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
