from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ColumnMapping:
    timestamp_col: str = "timestamp"
    price_col: str = "close"
    high_col: str | None = "high"
    low_col: str | None = "low"
    open_col: str | None = "open"
    close_col: str | None = "close"
    volume_col: str | None = "volume"
    taker_buy_col: str | None = None
    taker_sell_col: str | None = None
    buy_volume_col: str | None = None
    sell_volume_col: str | None = None
    signed_volume_col: str | None = None
    side_col: str | None = None
    size_col: str | None = None
