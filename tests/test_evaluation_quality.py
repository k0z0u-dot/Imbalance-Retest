from __future__ import annotations

import pandas as pd

from ofi_memory_zones.evaluation import evaluate_study_quality


def _winning_baselines() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "baseline_name": "random_zone",
                "ofi_percentile_vs_baseline": 90.0,
                "delta_avg_return_vs_ofi": -2.0,
            },
            {
                "baseline_name": "time_matched_random_zone",
                "ofi_percentile_vs_baseline": 80.0,
                "delta_avg_return_vs_ofi": -1.0,
            },
            {
                "baseline_name": "price_near_random_zone",
                "ofi_percentile_vs_baseline": 80.0,
                "delta_avg_return_vs_ofi": -1.0,
            },
            {
                "baseline_name": "swing_sr_zone",
                "ofi_percentile_vs_baseline": 75.0,
                "delta_avg_return_vs_ofi": 0.5,
            },
        ]
    )


def test_retest_count_shortage_is_inconclusive_or_fail() -> None:
    result = evaluate_study_quality(
        {"retest_count": 100, "avg_return_bps_after_cost": 2.0, "proxy_used": False},
        _winning_baselines(),
        {"warnings": []},
    )

    assert result["verdict"] in {"INCONCLUSIVE", "FAIL"}
    assert "retest_count < 200" in result["failed_gates"]


def test_non_positive_average_return_fails() -> None:
    result = evaluate_study_quality(
        {"retest_count": 300, "avg_return_bps_after_cost": 0.0, "proxy_used": False},
        _winning_baselines(),
        {"warnings": []},
    )

    assert result["verdict"] == "FAIL"
    assert "OFI avg_return_bps_after_cost <= 0" in result["failed_gates"]


def test_baseline_win_can_pass_or_weak_pass() -> None:
    result = evaluate_study_quality(
        {"retest_count": 300, "avg_return_bps_after_cost": 3.0, "proxy_used": False},
        _winning_baselines(),
        {"warnings": []},
    )

    assert result["verdict"] in {"PASS", "WEAK_PASS"}


def test_proxy_used_adds_warning() -> None:
    result = evaluate_study_quality(
        {"retest_count": 300, "avg_return_bps_after_cost": 3.0, "proxy_used": True},
        _winning_baselines(),
        {"warnings": [], "proxy_used": True},
    )

    assert "proxy_used=True" in result["warnings"]
