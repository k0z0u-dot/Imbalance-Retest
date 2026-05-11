from __future__ import annotations

from ofi_memory_zones.column_detection import infer_column_mapping_from_columns
from ofi_memory_zones.schema import ColumnMapping


def test_infer_taker_buy_sell_from_standard_names() -> None:
    mapping = infer_column_mapping_from_columns(["timestamp", "close", "taker_buy_volume", "taker_sell_volume"])
    assert mapping.taker_buy_col == "taker_buy_volume"
    assert mapping.taker_sell_col == "taker_sell_volume"


def test_explicit_mapping_kept_over_auto_detection() -> None:
    mapping = infer_column_mapping_from_columns(
        ["buy_volume", "sell_volume", "taker_buy_volume", "taker_sell_volume"],
        ColumnMapping(taker_buy_col="buy_volume", taker_sell_col="sell_volume"),
    )
    assert mapping.taker_buy_col == "buy_volume"
    assert mapping.taker_sell_col == "sell_volume"
