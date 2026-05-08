from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ofi_memory_zones.baselines import build_baseline_results
from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.diagnostics import build_data_diagnostics
from ofi_memory_zones.features import build_ofi_features
from ofi_memory_zones.metrics import (
    build_confirmation_summary,
    build_event_type_summary,
    build_metrics_summary,
)
from ofi_memory_zones.retests import detect_retests
from ofi_memory_zones.schema import ColumnMapping
from ofi_memory_zones.splits import run_oos_outputs
from ofi_memory_zones.zones import build_zones_from_events, generate_zone_events


def run_ofi_zone_study(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    columns: ColumnMapping | None = None,
    config: OFIMemoryZoneConfig | None = None,
) -> dict[str, Any]:
    config = config or OFIMemoryZoneConfig()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(input_path)
    columns = infer_column_mapping(raw, columns or ColumnMapping())
    features, metadata = build_ofi_features(raw, columns=columns, config=config)
    zone_events = generate_zone_events(features, config=config)
    initial_zones = build_zones_from_events(zone_events, retests=None, config=config)
    retests = detect_retests(features, initial_zones, config=config)
    zones = build_zones_from_events(zone_events, retests=retests, config=config)

    warnings = _study_warnings(features, zone_events, retests, metadata)
    event_type_summary = build_event_type_summary(zones, retests)
    confirmation_summary = build_confirmation_summary(retests)
    baseline_summary, baseline_trials = build_baseline_results(
        features=features,
        ofi_zones=zones,
        ofi_retests=retests,
        config=config,
    )
    cost_model = (
        "round_trip: 2 * (fee_bps + slippage_bps)"
        if config.cost_round_trip
        else "single_side: fee_bps + slippage_bps"
    )
    split_summary, walk_forward_results, walk_forward_summary = run_oos_outputs(
        features=features,
        config=config,
        output_dir=output,
        cost_model=cost_model,
    )
    metrics_summary = build_metrics_summary(
        features=features,
        zones=zones,
        retests=retests,
        metadata=metadata,
        event_type_summary=event_type_summary,
        confirmation_summary=confirmation_summary,
        baseline_summary=baseline_summary,
        warnings=warnings,
        cost_model=cost_model,
    )
    data_diagnostics = build_data_diagnostics(
        raw=raw,
        features=features,
        metadata=metadata,
        columns=columns,
        zones=zones,
        retests=retests,
        baseline_trials=baseline_trials,
        config=config,
        split_summary=split_summary,
    )

    paths = {
        "ofi_features": output / "ofi_features.csv",
        "zone_events": output / "zone_events.csv",
        "zones": output / "zones.csv",
        "retests": output / "retests.csv",
        "event_type_summary": output / "event_type_summary.csv",
        "confirmation_summary": output / "confirmation_summary.csv",
        "baseline_summary": output / "baseline_summary.csv",
        "baseline_trials": output / "baseline_trials.csv",
        "metrics_summary": output / "metrics_summary.json",
        "data_diagnostics": output / "data_diagnostics.json",
        "config": output / "config.json",
    }
    features.to_csv(paths["ofi_features"], index=False)
    zone_events.to_csv(paths["zone_events"], index=False)
    zones.to_csv(paths["zones"], index=False)
    retests.to_csv(paths["retests"], index=False)
    event_type_summary.to_csv(paths["event_type_summary"], index=False)
    confirmation_summary.to_csv(paths["confirmation_summary"], index=False)
    baseline_summary.to_csv(paths["baseline_summary"], index=False)
    baseline_trials.to_csv(paths["baseline_trials"], index=False)
    paths["metrics_summary"].write_text(
        json.dumps(metrics_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths["data_diagnostics"].write_text(
        json.dumps(data_diagnostics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths["config"].write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if config.split_mode == "train_test":
        paths["train_metrics_summary"] = output / "train_metrics_summary.json"
        paths["test_metrics_summary"] = output / "test_metrics_summary.json"
        paths["split_summary"] = output / "split_summary.csv"
    elif config.split_mode == "walk_forward":
        paths["walk_forward_results"] = output / "walk_forward_results.csv"
        paths["walk_forward_summary"] = output / "walk_forward_summary.json"

    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "metrics_summary": metrics_summary,
        "data_diagnostics": data_diagnostics,
        "split_summary": split_summary,
        "walk_forward_results": walk_forward_results,
        "walk_forward_summary": walk_forward_summary,
        "columns": columns,
        "config": config,
    }


def load_config_json(path: str | Path | None) -> OFIMemoryZoneConfig:
    if path is None:
        return OFIMemoryZoneConfig()
    values = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(values, dict):
        raise ValueError("--config-json must contain a JSON object.")
    return OFIMemoryZoneConfig.from_dict(values)


def infer_column_mapping(data: pd.DataFrame, columns: ColumnMapping) -> ColumnMapping:
    return ColumnMapping(
        timestamp_col=columns.timestamp_col,
        price_col=_first_existing(data, [columns.price_col, columns.close_col, "close", "price"]),
        high_col=_first_optional(data, [columns.high_col, "high"]),
        low_col=_first_optional(data, [columns.low_col, "low"]),
        open_col=_first_optional(data, [columns.open_col, "open"]),
        close_col=_first_optional(data, [columns.close_col, columns.price_col, "close", "price"]),
        volume_col=_first_optional(data, [columns.volume_col, "volume"]),
        taker_buy_col=_first_optional(
            data,
            [
                columns.taker_buy_col,
                "taker_buy_volume",
                "taker_buy_qty",
                "taker_buy_base_volume",
            ],
        ),
        taker_sell_col=_first_optional(
            data,
            [
                columns.taker_sell_col,
                "taker_sell_volume",
                "taker_sell_qty",
                "taker_sell_base_volume",
            ],
        ),
        buy_volume_col=_first_optional(data, [columns.buy_volume_col, "buy_volume"]),
        sell_volume_col=_first_optional(data, [columns.sell_volume_col, "sell_volume"]),
        signed_volume_col=_first_optional(data, [columns.signed_volume_col, "signed_volume"]),
        side_col=_first_optional(data, [columns.side_col, "side"]),
        size_col=_first_optional(data, [columns.size_col, "size", "qty", "quantity"]),
    )


def _study_warnings(
    features: pd.DataFrame,
    zone_events: pd.DataFrame,
    retests: pd.DataFrame,
    metadata: dict[str, object],
) -> list[str]:
    warnings: list[str] = []
    if metadata.get("proxy_used"):
        warnings.append("Flow proxy was used; results are not based on explicit taker buy/sell volume.")
    if zone_events.empty:
        warnings.append("No OFI memory zone events were generated with the current thresholds.")
    if retests.empty:
        warnings.append("No retests were detected after zone availability times.")
    if features["imbalance_z"].dropna().empty and features["robust_imbalance_z"].dropna().empty:
        warnings.append("Rolling z-score columns are empty; lower z_window or provide more history.")
    return warnings


def _first_existing(data: pd.DataFrame, candidates: list[str | None]) -> str:
    for candidate in candidates:
        if candidate and candidate in data.columns:
            return candidate
    fallback = next((candidate for candidate in candidates if candidate), None)
    if fallback is None:
        raise ValueError("No candidate column was provided.")
    return fallback


def _first_optional(data: pd.DataFrame, candidates: list[str | None]) -> str | None:
    for candidate in candidates:
        if candidate and candidate in data.columns:
            return candidate
    return None
