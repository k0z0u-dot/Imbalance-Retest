from __future__ import annotations

from typing import Any

import pandas as pd


def evaluate_study_quality(
    metrics_summary: dict[str, Any],
    baseline_summary: pd.DataFrame | list[dict[str, Any]] | None,
    diagnostics: dict[str, Any] | None,
    split_summary: pd.DataFrame | list[dict[str, Any]] | None = None,
    walk_forward_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = _coerce_frame(baseline_summary)
    split = _coerce_frame(split_summary)
    diagnostics = diagnostics or {}

    passed_gates: list[str] = []
    failed_gates: list[str] = []
    reasons: list[str] = []
    warnings: list[str] = list(metrics_summary.get("warnings") or [])
    warnings.extend(list(diagnostics.get("warnings") or []))

    retest_count = _float(metrics_summary.get("retest_count"), 0.0)
    avg_return = _optional_float(metrics_summary.get("avg_return_bps_after_cost"))

    if retest_count >= 200:
        passed_gates.append("retest_count >= 200")
    elif retest_count < 50:
        failed_gates.append("retest_count < 50")
        reasons.append("Retest sample is too small for a research conclusion.")
    else:
        failed_gates.append("retest_count < 200")
        reasons.append("Retest sample is below the preferred 200-event threshold.")

    if bool(metrics_summary.get("proxy_used")) or bool(diagnostics.get("proxy_used")):
        warnings.append("proxy_used=True")
    else:
        passed_gates.append("proxy_used is False")

    if avg_return is not None and avg_return > 0:
        passed_gates.append("OFI avg_return_bps_after_cost > 0")
    else:
        failed_gates.append("OFI avg_return_bps_after_cost <= 0")
        reasons.append("OFI average return after cost is not positive.")

    _check_percentile_gate(
        baseline,
        "random_zone",
        80.0,
        passed_gates,
        failed_gates,
        reasons,
    )
    _check_percentile_gate(
        baseline,
        "time_matched_random_zone",
        70.0,
        passed_gates,
        failed_gates,
        reasons,
    )
    price_near_ok = _check_percentile_gate(
        baseline,
        "price_near_random_zone",
        70.0,
        passed_gates,
        failed_gates,
        reasons,
    )
    _check_swing_gate(baseline, passed_gates, failed_gates, reasons)

    positive_fold_ratio = None
    if walk_forward_summary:
        positive_fold_ratio = _optional_float(walk_forward_summary.get("positive_fold_ratio"))
        if positive_fold_ratio is None:
            positive_fold_ratio = _optional_float(
                walk_forward_summary.get("mean_positive_fold_ratio")
            )
        if positive_fold_ratio is not None and positive_fold_ratio >= 0.5:
            passed_gates.append("walk-forward positive fold ratio >= 0.5")
        else:
            failed_gates.append("walk-forward positive fold ratio < 0.5")
            reasons.append("Walk-forward positive fold ratio is below 0.5.")

    if not split.empty:
        _check_split_gate(split, failed_gates, reasons)

    severe_warnings = _severe_warnings(warnings)
    if severe_warnings:
        failed_gates.append("major data-quality warning")
        reasons.append("Major data-quality warnings are present: " + "; ".join(severe_warnings))

    price_near_clear_loss = _baseline_clear_loss(baseline, "price_near_random_zone", margin_bps=1.0)
    if price_near_clear_loss:
        failed_gates.append("price_near_random_zone clearly outperforms OFI")
        reasons.append("OFI clearly underperforms the price-near random baseline.")

    verdict = _verdict(
        retest_count=retest_count,
        avg_return=avg_return,
        failed_gates=failed_gates,
        passed_gates=passed_gates,
        price_near_ok=price_near_ok,
        severe_warnings=severe_warnings,
        price_near_clear_loss=price_near_clear_loss,
    )
    return {
        "verdict": verdict,
        "reasons": _unique(reasons),
        "failed_gates": _unique(failed_gates),
        "passed_gates": _unique(passed_gates),
        "warnings": _unique(warnings),
    }


def _check_percentile_gate(
    baseline: pd.DataFrame,
    baseline_name: str,
    threshold: float,
    passed_gates: list[str],
    failed_gates: list[str],
    reasons: list[str],
) -> bool:
    row = _baseline_row(baseline, baseline_name)
    if row is None:
        failed_gates.append(f"{baseline_name} baseline missing")
        reasons.append(f"{baseline_name} baseline is missing.")
        return False
    percentile = _optional_float(row.get("ofi_percentile_vs_baseline"))
    if percentile is not None and percentile >= threshold:
        passed_gates.append(f"OFI percentile vs {baseline_name} >= {threshold:g}")
        return True
    failed_gates.append(f"OFI percentile vs {baseline_name} < {threshold:g}")
    reasons.append(f"OFI percentile vs {baseline_name} is below {threshold:g}.")
    return False


def _check_swing_gate(
    baseline: pd.DataFrame,
    passed_gates: list[str],
    failed_gates: list[str],
    reasons: list[str],
) -> None:
    row = _baseline_row(baseline, "swing_sr_zone")
    if row is None:
        failed_gates.append("swing_sr_zone baseline missing")
        reasons.append("swing_sr_zone baseline is missing.")
        return
    delta = _optional_float(row.get("delta_avg_return_vs_ofi"))
    if delta is None:
        failed_gates.append("swing_sr_zone comparison unavailable")
        reasons.append("swing_sr_zone return comparison is unavailable.")
        return
    # delta is baseline mean minus OFI. Allow small underperformance within 2 bps.
    if delta <= 2.0:
        passed_gates.append("OFI is not materially worse than swing_sr_zone")
    else:
        failed_gates.append("OFI materially underperforms swing_sr_zone")
        reasons.append("OFI average return is materially below swing SR baseline.")


def _check_split_gate(
    split: pd.DataFrame,
    failed_gates: list[str],
    reasons: list[str],
) -> None:
    for _, row in split.iterrows():
        train_return = _optional_float(row.get("train_avg_return_bps_after_cost"))
        test_return = _optional_float(row.get("test_avg_return_bps_after_cost"))
        degradation = _optional_float(row.get("avg_return_bps_after_cost_degradation"))
        if train_return is not None and train_return > 0 and test_return is not None:
            if test_return <= 0 or (degradation is not None and degradation > max(5.0, abs(train_return))):
                failed_gates.append("test period return degrades materially")
                reasons.append("Test period return materially degrades versus train.")


def _verdict(
    *,
    retest_count: float,
    avg_return: float | None,
    failed_gates: list[str],
    passed_gates: list[str],
    price_near_ok: bool,
    severe_warnings: list[str],
    price_near_clear_loss: bool,
) -> str:
    if (
        retest_count < 50
        or avg_return is None
        or avg_return <= 0
        or price_near_clear_loss
        or "test period return degrades materially" in failed_gates
        or severe_warnings
    ):
        return "FAIL"
    if retest_count < 200:
        return "INCONCLUSIVE"
    required_failures = [
        gate
        for gate in failed_gates
        if "baseline missing" in gate or "percentile" in gate or "swing" in gate
    ]
    if not required_failures and price_near_ok and len(passed_gates) >= 6:
        return "PASS"
    if avg_return > 0 and price_near_ok and len(passed_gates) >= 4:
        return "WEAK_PASS"
    return "INCONCLUSIVE"


def _baseline_clear_loss(
    baseline: pd.DataFrame,
    baseline_name: str,
    margin_bps: float,
) -> bool:
    row = _baseline_row(baseline, baseline_name)
    if row is None:
        return False
    delta = _optional_float(row.get("delta_avg_return_vs_ofi"))
    percentile = _optional_float(row.get("ofi_percentile_vs_baseline"))
    return bool((delta is not None and delta > margin_bps) or (percentile is not None and percentile < 40.0))


def _severe_warnings(warnings: list[str]) -> list[str]:
    severe_markers = [
        "volume data missing",
        "high/low missing",
        "baseline trials missing",
    ]
    return [warning for warning in warnings if any(marker in warning for marker in severe_markers)]


def _baseline_row(baseline: pd.DataFrame, baseline_name: str) -> dict[str, Any] | None:
    if baseline.empty or "baseline_name" not in baseline.columns:
        return None
    matches = baseline[baseline["baseline_name"] == baseline_name]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _coerce_frame(value: pd.DataFrame | list[dict[str, Any]] | None) -> pd.DataFrame:
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value
    return pd.DataFrame(value)


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any, default: float) -> float:
    parsed = _optional_float(value)
    return default if parsed is None else parsed


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))
