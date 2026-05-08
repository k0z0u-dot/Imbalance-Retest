from __future__ import annotations

import math
from typing import Any

import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig

try:  # scipy is optional for consumers of the package.
    from scipy.stats import beta as scipy_beta
except Exception:  # pragma: no cover - depends on environment
    scipy_beta = None


def posterior_success(
    success_count: int,
    retest_count: int,
    config: OFIMemoryZoneConfig,
) -> tuple[float, float | None]:
    alpha = config.prior_alpha + success_count
    beta = config.prior_beta + max(retest_count - success_count, 0)
    mean = alpha / (alpha + beta)
    lower = None
    if scipy_beta is not None:
        lower = float(scipy_beta.ppf(config.posterior_lower_quantile, alpha, beta))
    return float(mean), lower


def calculate_zone_strength(
    *,
    imbalance_z: float,
    reaction_atr: float,
    mfe_bps: float,
    mae_bps: float,
    age_bars: int = 0,
    failure_count: int = 0,
    absorption_strength: float = 0.0,
) -> float:
    """Default v0 strength formula, isolated for later replacement."""

    imbalance_strength = _finite_abs(imbalance_z)
    reaction_strength = _finite_positive(reaction_atr)
    efficiency = max(0.0, _finite_positive(mfe_bps) / max(abs(_finite_float(mae_bps)), 1e-9))
    age_penalty = max(age_bars, 0) * 0.001
    failure_penalty = max(failure_count, 0) * 0.75
    return float(
        imbalance_strength
        + reaction_strength
        + efficiency
        + max(absorption_strength, 0.0)
        - age_penalty
        - failure_penalty
    )


def strength_components(
    event: pd.Series | dict[str, Any],
    *,
    age_bars: int = 0,
    failure_count: int = 0,
) -> dict[str, float]:
    imbalance_z = _event_float(event, "imbalance_z")
    robust_z = _event_float(event, "robust_imbalance_z")
    selected_imbalance = robust_z if math.isfinite(robust_z) else imbalance_z
    reaction_atr = _event_float(event, "reaction_atr")
    mfe_bps = _event_float(event, "mfe_bps")
    mae_bps = _event_float(event, "mae_bps")
    absorption_strength = (
        _finite_abs(selected_imbalance) * 0.5
        if str(event.get("zone_type", "")).startswith("absorption")
        else 0.0
    )
    zone_strength = calculate_zone_strength(
        imbalance_z=selected_imbalance,
        reaction_atr=reaction_atr,
        mfe_bps=mfe_bps,
        mae_bps=mae_bps,
        age_bars=age_bars,
        failure_count=failure_count,
        absorption_strength=absorption_strength,
    )
    return {
        "zone_strength": zone_strength,
        "imbalance_strength": _finite_abs(selected_imbalance),
        "reaction_strength": _finite_positive(reaction_atr),
        "absorption_strength": absorption_strength,
    }


def _event_float(event: pd.Series | dict[str, Any], key: str) -> float:
    return _finite_float(event.get(key, float("nan")))


def _finite_float(value: Any) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return value


def _finite_abs(value: Any) -> float:
    return abs(_finite_float(value))


def _finite_positive(value: Any) -> float:
    return max(_finite_float(value), 0.0)
