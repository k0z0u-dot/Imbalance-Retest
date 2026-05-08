from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofi_memory_zones.synthetic import generate_synthetic_ofi_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic OFI Memory Zone sample data.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--rows", type=int, default=560)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--start-price", type=float, default=10000.0)
    parser.add_argument("--cycle-price-offset-bps", type=float, default=20.0)
    parser.add_argument("--noise-scale", type=float, default=0.002)
    parser.add_argument("--start-timestamp", default="2026-01-01 09:00:00")
    parser.add_argument("--freq", default="min")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    data = generate_synthetic_ofi_data(
        output_path=args.output,
        rows=args.rows,
        cycles=args.cycles,
        start_price=args.start_price,
        cycle_price_offset_bps=args.cycle_price_offset_bps,
        noise_scale=args.noise_scale,
        start_timestamp=args.start_timestamp,
        freq=args.freq,
        seed=args.seed,
    )
    print(f"Wrote {len(data)} synthetic rows to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
