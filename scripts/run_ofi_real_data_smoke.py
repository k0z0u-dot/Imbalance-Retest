from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ofi_memory_zones.input_inspection import (
    NOT_READY,
    inspect_input_csv,
    write_input_diagnostics_reports,
)
from ofi_memory_zones.reporting import summarize_ofi_experiment
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.study import load_config_json, run_ofi_zone_study


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run real-data OFI smoke pipeline safely.")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--output-root", required=True, help="Root output directory for smoke run.")
    parser.add_argument("--config-json", required=True, help="Study config JSON path.")
    parser.add_argument("--not-ready-exit-code", type=int, default=1)
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
    output_root = Path(args.output_root)
    inspection_dir = output_root / "input_inspection"
    study_dir = output_root / "study"
    report_dir = output_root / "report"
    output_root.mkdir(parents=True, exist_ok=True)

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
    write_input_diagnostics_reports(diagnostics, args.input, inspection_dir)

    study_executed = False
    report_executed = False
    report_payload: dict[str, Any] = {}

    if diagnostics.get("readiness_verdict") != NOT_READY:
        config = load_config_json(args.config_json)
        run_ofi_zone_study(input_path=args.input, output_dir=study_dir, columns=columns, config=config)
        study_executed = True
        report_payload = summarize_ofi_experiment(input_dir=study_dir, output_dir=report_dir)
        report_executed = True

    summary = _build_smoke_summary(
        diagnostics=diagnostics,
        input_path=args.input,
        config_path=args.config_json,
        study_executed=study_executed,
        report_executed=report_executed,
        report_payload=report_payload,
        output_root=output_root,
    )
    _write_smoke_summary(output_root, summary)

    if diagnostics.get("readiness_verdict") == NOT_READY:
        print(f"Readiness verdict is NOT_READY. Study/report skipped. See: {output_root.resolve()}")
        return int(args.not_ready_exit_code)

    print(f"Smoke pipeline completed. See: {output_root.resolve()}")
    return 0


def _build_smoke_summary(*, diagnostics: dict[str, Any], input_path: str, config_path: str, study_executed: bool, report_executed: bool, report_payload: dict[str, Any], output_root: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "input_path": str(Path(input_path)),
        "config_path": str(Path(config_path)),
        "readiness_verdict": diagnostics.get("readiness_verdict"),
        "detected_flow_source": diagnostics.get("detected_flow_source"),
        "proxy_used": diagnostics.get("proxy_used"),
        "high_low_available": diagnostics.get("high_low_available"),
        "rows": diagnostics.get("rows"),
        "start_timestamp": diagnostics.get("start_timestamp"),
        "end_timestamp": diagnostics.get("end_timestamp"),
        "warnings": diagnostics.get("warnings", []),
        "study_executed": study_executed,
        "report_executed": report_executed,
        "zone_count": None,
        "retest_count": None,
        "overall_hit_rate": None,
        "avg_return_bps_after_cost": None,
        "baseline_comparison_summary": None,
        "quality_gate_verdict": None,
        "next_review_checklist": [
            "input_inspection/input_diagnostics.md を確認する",
            "proxy_used=True や high/low 欠損の警告を確認する",
            "report/experiment_report.md の Quality Gate を確認する",
            "baseline comparison を確認し random_zone 以外も比較する",
            "これは strategy backtest ではないことを前提に解釈する",
        ],
    }
    if study_executed:
        metrics_path = output_root / "study" / "metrics_summary.json"
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
            summary["zone_count"] = metrics.get("zone_count")
            summary["retest_count"] = metrics.get("retest_count")
            summary["overall_hit_rate"] = metrics.get("overall_hit_rate")
            summary["avg_return_bps_after_cost"] = metrics.get("avg_return_bps_after_cost")
            baseline_cmp = metrics.get("baseline_comparison")
            if isinstance(baseline_cmp, dict):
                summary["baseline_comparison_summary"] = {
                    "baseline_names": sorted(baseline_cmp.keys()),
                    "count": len(baseline_cmp),
                }
    if report_executed:
        summary["quality_gate_verdict"] = report_payload.get("verdict")
    return summary


def _write_smoke_summary(output_root: Path, summary: dict[str, Any]) -> None:
    (output_root / "smoke_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    warning_lines = "\n".join(f"- {w}" for w in summary.get("warnings", [])) or "- None"
    checklist_lines = "\n".join(f"- {w}" for w in summary.get("next_review_checklist", []))
    md = f"""# OFI Real-data Smoke Summary

## Input
- input_path: {summary['input_path']}
- config_path: {summary['config_path']}
- readiness_verdict: {summary['readiness_verdict']}
- detected_flow_source: {summary['detected_flow_source']}
- proxy_used: {summary['proxy_used']}
- high_low_available: {summary['high_low_available']}
- rows: {summary['rows']}
- start_timestamp: {summary['start_timestamp']}
- end_timestamp: {summary['end_timestamp']}

## Pipeline Status
- study_executed: {summary['study_executed']}
- report_executed: {summary['report_executed']}

## Key Metrics
- zone_count: {summary['zone_count']}
- retest_count: {summary['retest_count']}
- overall_hit_rate: {summary['overall_hit_rate']}
- avg_return_bps_after_cost: {summary['avg_return_bps_after_cost']}
- baseline_comparison_summary: {summary['baseline_comparison_summary']}
- quality_gate_verdict: {summary['quality_gate_verdict']}

## Warnings
{warning_lines}

## Next Review Checklist
{checklist_lines}
"""
    (output_root / "smoke_summary.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
