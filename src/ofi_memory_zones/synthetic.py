from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PATTERN_TYPES = [
    "initiative_support",
    "absorption_support",
    "initiative_resistance",
    "absorption_resistance",
]


def generate_synthetic_ofi_data(
    *,
    output_path: str | Path,
    rows: int = 560,
    start_timestamp: str = "2026-01-01 09:00:00",
    freq: str = "min",
    seed: int = 42,
    cycles: int = 1,
    start_price: float = 10000.0,
    cycle_price_offset_bps: float = 20.0,
    noise_scale: float = 0.002,
) -> pd.DataFrame:
    if rows < 520:
        raise ValueError("Synthetic OFI data requires at least 520 rows.")
    if cycles < 1:
        raise ValueError("Synthetic OFI data requires cycles >= 1.")
    if start_price <= 0:
        raise ValueError("Synthetic OFI data requires start_price > 0.")

    rng = np.random.default_rng(seed)
    total_rows = rows * cycles
    timestamps = pd.date_range(start_timestamp, periods=total_rows, freq=freq)
    close = np.empty(total_rows, dtype=float)
    open_ = np.empty(total_rows, dtype=float)
    high = np.empty(total_rows, dtype=float)
    low = np.empty(total_rows, dtype=float)
    buy = np.full(total_rows, 10.0)
    sell = np.full(total_rows, 10.0)
    labels = np.full(total_rows, "background", dtype=object)

    for cycle in range(cycles):
        start = cycle * rows
        end = start + rows
        cycle_base = start_price * (1.0 + cycle * cycle_price_offset_bps / 10000.0)
        close[start:end] = cycle_base + np.cumsum(rng.normal(0.0, noise_scale, rows))

    open_ = np.r_[close[0], close[:-1]]
    high[:] = np.maximum(open_, close) + _bps(close, 1.0)
    low[:] = np.minimum(open_, close) - _bps(close, 1.0)

    for cycle in range(cycles):
        start = cycle * rows
        cycle_base = start_price * (1.0 + cycle * cycle_price_offset_bps / 10000.0)
        specs = [
            ("initiative_support", start + 100, cycle_base * 1.0000, "buy", "up", 25),
            ("absorption_support", start + 220, cycle_base * 1.0100, "sell", "up_absorption", 25),
            ("initiative_resistance", start + 340, cycle_base * 1.0200, "sell", "down", 25),
            ("absorption_resistance", start + 460, cycle_base * 1.0150, "buy", "down_absorption", 25),
        ]

        for zone_type, event_index, center, flow_side, reaction, retest_offset in specs:
            _write_pattern(
                close=close,
                open_=open_,
                high=high,
                low=low,
                buy=buy,
                sell=sell,
                labels=labels,
                zone_type=zone_type,
                event_index=event_index,
                center=center,
                flow_side=flow_side,
                reaction=reaction,
                retest_offset=retest_offset,
            )

    data = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": buy + sell,
            "taker_buy_volume": buy,
            "taker_sell_volume": sell,
            "synthetic_label": labels,
        }
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False)
    return data


def _write_pattern(
    *,
    close: np.ndarray,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    buy: np.ndarray,
    sell: np.ndarray,
    labels: np.ndarray,
    zone_type: str,
    event_index: int,
    center: float,
    flow_side: str,
    reaction: str,
    retest_offset: int,
) -> None:
    for index in range(event_index - 5, event_index + 32):
        if index < 0 or index >= len(close):
            continue
        close[index] = center
        open_[index] = center
        high[index] = center + _bps(center, 1.0)
        low[index] = center - _bps(center, 1.0)

    labels[event_index] = zone_type
    close[event_index] = center
    open_[event_index] = center
    high[event_index] = center + _bps(center, 1.0)
    low[event_index] = center - _bps(center, 1.0)
    if flow_side == "buy":
        buy[event_index] = 150.0
        sell[event_index] = 1.0
    else:
        buy[event_index] = 1.0
        sell[event_index] = 150.0

    if reaction == "up":
        _set_bar(close, open_, high, low, event_index + 8, center + _bps(center, 10.0), center + _bps(center, 12.0), center + _bps(center, 6.0))
        _set_bar(close, open_, high, low, event_index + 12, center + _bps(center, 16.0), center + _bps(center, 18.0), center + _bps(center, 8.0))
    elif reaction == "up_absorption":
        _set_bar(close, open_, high, low, event_index + 3, center + _bps(center, 1.0), center + _bps(center, 2.0), center - _bps(center, 1.0))
        _set_bar(close, open_, high, low, event_index + 10, center + _bps(center, 12.0), center + _bps(center, 15.0), center + _bps(center, 5.0))
    elif reaction == "down":
        _set_bar(close, open_, high, low, event_index + 8, center - _bps(center, 10.0), center - _bps(center, 6.0), center - _bps(center, 12.0))
        _set_bar(close, open_, high, low, event_index + 12, center - _bps(center, 16.0), center - _bps(center, 8.0), center - _bps(center, 18.0))
    elif reaction == "down_absorption":
        _set_bar(close, open_, high, low, event_index + 3, center - _bps(center, 1.0), center + _bps(center, 1.0), center - _bps(center, 2.0))
        _set_bar(close, open_, high, low, event_index + 10, center - _bps(center, 12.0), center - _bps(center, 5.0), center - _bps(center, 15.0))

    retest_index = event_index + retest_offset
    labels[retest_index] = f"{zone_type}_retest"
    _set_bar(close, open_, high, low, retest_index, center, center + _bps(center, 2.0), center - _bps(center, 2.0))
    if "support" in zone_type:
        buy[retest_index] = 90.0
        sell[retest_index] = 5.0
        _set_bar(close, open_, high, low, retest_index + 1, center + _bps(center, 8.0), center + _bps(center, 10.0), center + _bps(center, 1.0))
    else:
        buy[retest_index] = 5.0
        sell[retest_index] = 90.0
        _set_bar(close, open_, high, low, retest_index + 1, center - _bps(center, 8.0), center - _bps(center, 1.0), center - _bps(center, 10.0))


def _set_bar(
    close: np.ndarray,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    index: int,
    close_value: float,
    high_value: float,
    low_value: float,
) -> None:
    if index < 0 or index >= len(close):
        return
    close[index] = close_value
    open_[index] = close_value
    high[index] = high_value
    low[index] = low_value


def _bps(price: float | np.ndarray, bps: float) -> float | np.ndarray:
    return price * bps / 10000.0
