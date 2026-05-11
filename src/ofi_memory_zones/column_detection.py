from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from ofi_memory_zones.schema import ColumnMapping

_FLOW_CANDIDATES: dict[str, tuple[str, ...]] = {
    "taker_buy_col": (
        "taker_buy_volume",
        "taker_buy",
        "buy_taker_volume",
        "aggressive_buy_volume",
    ),
    "taker_sell_col": (
        "taker_sell_volume",
        "taker_sell",
        "sell_taker_volume",
        "aggressive_sell_volume",
    ),
    "buy_volume_col": ("buy_volume", "bid_volume"),
    "sell_volume_col": ("sell_volume", "ask_volume"),
    "side_col": ("side", "taker_side", "aggressor_side"),
    "size_col": ("size", "qty", "quantity", "volume"),
    "signed_volume_col": ("signed_volume", "delta_volume", "volume_delta"),
}


def infer_column_mapping_from_columns(
    columns: Iterable[str], base: ColumnMapping | None = None
) -> ColumnMapping:
    mapping = base or ColumnMapping()
    available = set(columns)

    values = asdict(mapping)
    for field_name, candidates in _FLOW_CANDIDATES.items():
        if values[field_name] is not None:
            continue
        values[field_name] = _first_available(available, candidates)
    return ColumnMapping(**values)


def detected_column_mapping_report(mapping: ColumnMapping) -> dict[str, str | None]:
    return {
        "taker_buy_col": mapping.taker_buy_col,
        "taker_sell_col": mapping.taker_sell_col,
        "buy_volume_col": mapping.buy_volume_col,
        "sell_volume_col": mapping.sell_volume_col,
        "side_col": mapping.side_col,
        "size_col": mapping.size_col,
        "signed_volume_col": mapping.signed_volume_col,
    }


def _first_available(columns: set[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None
