from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofi_memory_zones.reporting import summarize_ofi_experiment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize an OFI Memory Zone experiment.")
    parser.add_argument("--input", required=True, help="Study or sweep output directory.")
    parser.add_argument("--output", required=True, help="Report output directory.")
    parser.add_argument("--sweep", action="store_true", help="Interpret input as sweep output.")
    args = parser.parse_args(argv)

    report = summarize_ofi_experiment(input_dir=args.input, output_dir=args.output, sweep=args.sweep)
    if args.sweep:
        print(f"Wrote sweep experiment report to: {Path(args.output).resolve()}")
    else:
        print(f"Wrote experiment report to: {Path(args.output).resolve()}")
        print(f"Verdict: {report.get('verdict')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
