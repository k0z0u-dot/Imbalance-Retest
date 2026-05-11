from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofi_memory_zones.input_inspection import inspect_input_csv, write_input_diagnostics_reports
from ofi_memory_zones.schema import ColumnMapping


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect OFI input CSV readiness before study runs.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
    diagnostics = inspect_input_csv(args.input, columns)
    write_input_diagnostics_reports(diagnostics, args.input, args.output)
    print(f"Wrote input diagnostics to: {Path(args.output).resolve()}")
    print(f"Readiness verdict: {diagnostics['readiness_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
