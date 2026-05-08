from __future__ import annotations

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.strength import calculate_zone_strength, posterior_success


def test_three_wins_zero_losses_posterior_is_not_one_hundred_percent() -> None:
    mean, _ = posterior_success(success_count=3, retest_count=3, config=OFIMemoryZoneConfig())

    assert mean < 1.0
    assert mean == (6 + 3) / (6 + 4 + 3)


def test_posterior_moves_toward_observed_results_as_retests_increase() -> None:
    config = OFIMemoryZoneConfig()
    small_sample_mean, _ = posterior_success(success_count=3, retest_count=3, config=config)
    large_sample_mean, _ = posterior_success(success_count=30, retest_count=30, config=config)

    assert large_sample_mean > small_sample_mean
    assert abs(1.0 - large_sample_mean) < abs(1.0 - small_sample_mean)


def test_failure_count_reduces_zone_strength() -> None:
    base = calculate_zone_strength(
        imbalance_z=3.0,
        reaction_atr=0.5,
        mfe_bps=10.0,
        mae_bps=-5.0,
        failure_count=0,
    )
    with_failures = calculate_zone_strength(
        imbalance_z=3.0,
        reaction_atr=0.5,
        mfe_bps=10.0,
        mae_bps=-5.0,
        failure_count=3,
    )

    assert with_failures < base
