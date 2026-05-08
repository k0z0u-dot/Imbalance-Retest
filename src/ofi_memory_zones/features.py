from __future__ import annotations

import numpy as np
import pandas as pd

from ofi_memory_zones.config import OFIMemoryZoneConfig
from ofi_memory_zones.schema import ColumnMapping


class OFIDataError(ValueError):
    """Raised when input data cannot support OFI feature construction."""


def build_ofi_features(
    data: pd.DataFrame,
    columns: ColumnMapping | None = None,
    config: OFIMemoryZoneConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Build bar-level order-flow imbalance features.

    The function never fabricates flow from price movement. It uses explicit taker
    volumes first, then documented proxies, and raises if no flow source exists.
    """

    columns = columns or ColumnMapping()
    config = config or OFIMemoryZoneConfig()
    _require_column(data, columns.timestamp_col, "timestamp")

    working = data.copy()
    working["source_row_index"] = np.arange(len(working), dtype=int)

    source, proxy_used = _resolve_flow_source(working, columns)
    if source == "raw_side_size":
        working = _aggregate_raw_trades(working, columns)
        source, proxy_used = "side_size", False

    parsed_timestamps = pd.to_datetime(working[columns.timestamp_col], errors="coerce")
    if parsed_timestamps.isna().any():
        raise OFIDataError(f"Column '{columns.timestamp_col}' contains unparseable timestamps.")
    working = (
        working.assign(_parsed_timestamp=parsed_timestamps)
        .sort_values("_parsed_timestamp")
        .reset_index(drop=True)
    )

    features = pd.DataFrame(index=working.index)
    features["timestamp"] = working["_parsed_timestamp"]

    price = _numeric_column(working, _price_column(columns), "price")
    features["price"] = price
    features["open"] = _optional_price(working, columns.open_col, price)
    features["high"] = _optional_price(working, columns.high_col, price)
    features["low"] = _optional_price(working, columns.low_col, price)
    features["close"] = _optional_price(working, columns.close_col, price)
    features["volume"] = _optional_numeric(working, columns.volume_col, np.nan)

    if source == "taker":
        buy = _numeric_column(working, columns.taker_buy_col, "taker buy volume")
        sell = _numeric_column(working, columns.taker_sell_col, "taker sell volume")
    elif source == "buy_sell_proxy":
        buy = _numeric_column(working, columns.buy_volume_col, "buy volume")
        sell = _numeric_column(working, columns.sell_volume_col, "sell volume")
    elif source == "signed_proxy":
        signed = _numeric_column(working, columns.signed_volume_col, "signed volume")
        buy = signed.clip(lower=0.0)
        sell = (-signed).clip(lower=0.0)
    elif source == "side_size":
        buy = _numeric_column(working, "taker_buy_volume", "taker buy volume")
        sell = _numeric_column(working, "taker_sell_volume", "taker sell volume")
    else:
        raise OFIDataError("Internal error: unresolved OFI flow source.")

    features["taker_buy_volume"] = buy.astype(float)
    features["taker_sell_volume"] = sell.astype(float)
    features["signed_volume"] = features["taker_buy_volume"] - features["taker_sell_volume"]
    features["total_flow_volume"] = features["taker_buy_volume"] + features["taker_sell_volume"]
    features["imbalance"] = features["signed_volume"] / np.maximum(
        features["total_flow_volume"], config.eps
    )
    features["proxy_used"] = bool(proxy_used)
    features["source_row_index"] = working["source_row_index"].astype(int).to_numpy()

    features["imbalance_z"] = _rolling_z(features["imbalance"], config.z_window, config.eps)
    features["robust_imbalance_z"] = _rolling_robust_z(
        features["imbalance"], config.z_window, config.eps
    )
    features["volume_z"] = _rolling_z(features["total_flow_volume"], config.z_window, config.eps)
    features["atr"] = _atr(features, config.atr_window, config.eps)

    features["bar_index"] = np.arange(len(features), dtype=int)

    metadata = {
        "flow_source": source,
        "proxy_used": bool(proxy_used),
        "rows": int(len(features)),
        "start_timestamp": _timestamp_or_none(features["timestamp"].iloc[0])
        if len(features)
        else None,
        "end_timestamp": _timestamp_or_none(features["timestamp"].iloc[-1])
        if len(features)
        else None,
    }
    return features, metadata


def _resolve_flow_source(data: pd.DataFrame, columns: ColumnMapping) -> tuple[str, bool]:
    if _has_columns(data, columns.taker_buy_col, columns.taker_sell_col):
        return "taker", False
    if _has_columns(data, columns.buy_volume_col, columns.sell_volume_col):
        return "buy_sell_proxy", True
    if _has_columns(data, columns.side_col, columns.size_col):
        return "raw_side_size", False
    if _has_columns(data, columns.signed_volume_col):
        return "signed_proxy", True
    raise OFIDataError(
        "No usable OFI flow columns found. Provide taker_buy/taker_sell, buy/sell volume, "
        "side+size raw trades, or signed_volume. OFI will not be inferred from price."
    )


def _aggregate_raw_trades(data: pd.DataFrame, columns: ColumnMapping) -> pd.DataFrame:
    side_col = _require_column(data, columns.side_col, "side")
    size_col = _require_column(data, columns.size_col, "size")
    timestamp_col = _require_column(data, columns.timestamp_col, "timestamp")
    price_col = _require_column(data, _price_column(columns), "price")

    working = data.copy()
    side = working[side_col].astype(str).str.lower().str.strip()
    size = pd.to_numeric(working[size_col], errors="coerce").fillna(0.0).astype(float)
    working["_buy_size"] = np.where(side.isin(["buy", "b", "bid"]), size, 0.0)
    working["_sell_size"] = np.where(side.isin(["sell", "s", "ask"]), size, 0.0)

    aggregations: dict[str, tuple[str, str]] = {
        "source_row_index": ("source_row_index", "first"),
        "price": (price_col, "last"),
        "open": (columns.open_col or price_col, "first"),
        "high": (columns.high_col or price_col, "max"),
        "low": (columns.low_col or price_col, "min"),
        "close": (columns.close_col or price_col, "last"),
        "volume": (size_col, "sum"),
        "taker_buy_volume": ("_buy_size", "sum"),
        "taker_sell_volume": ("_sell_size", "sum"),
    }
    grouped = working.groupby(timestamp_col, sort=True).agg(**aggregations).reset_index()
    output = pd.DataFrame(
        {
            timestamp_col: grouped[timestamp_col],
            "source_row_index": grouped["source_row_index"],
            "taker_buy_volume": grouped["taker_buy_volume"],
            "taker_sell_volume": grouped["taker_sell_volume"],
        }
    )
    output[_price_column(columns)] = grouped["price"]
    output[columns.open_col or "open"] = grouped["open"]
    output[columns.high_col or "high"] = grouped["high"]
    output[columns.low_col or "low"] = grouped["low"]
    output[columns.close_col or _price_column(columns)] = grouped["close"]
    output[columns.volume_col or "volume"] = grouped["volume"]
    return output


def _rolling_z(series: pd.Series, window: int, eps: float) -> pd.Series:
    rolling = series.rolling(window=window, min_periods=2)
    mean = rolling.mean().shift(1)
    std = rolling.std(ddof=0).shift(1)
    z = (series - mean) / np.maximum(std, eps)
    return _finite_or_nan(z)


def _rolling_robust_z(series: pd.Series, window: int, eps: float) -> pd.Series:
    rolling = series.rolling(window=window, min_periods=2)
    median = rolling.median().shift(1)
    mad = rolling.apply(lambda values: float(np.median(np.abs(values - np.median(values)))), raw=True)
    robust = (series - median) / np.maximum(mad.shift(1), eps)
    return _finite_or_nan(robust)


def _atr(features: pd.DataFrame, window: int, eps: float) -> pd.Series:
    high = features["high"].astype(float)
    low = features["low"].astype(float)
    close = features["close"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(window=window, min_periods=1).mean()
    return atr.clip(lower=eps)


def _finite_or_nan(series: pd.Series) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan)


def _optional_price(data: pd.DataFrame, column: str | None, fallback: pd.Series) -> pd.Series:
    if column and column in data.columns:
        return pd.to_numeric(data[column], errors="coerce").astype(float)
    return fallback.astype(float)


def _optional_numeric(data: pd.DataFrame, column: str | None, default: float) -> pd.Series:
    if column and column in data.columns:
        return pd.to_numeric(data[column], errors="coerce").astype(float)
    return pd.Series(default, index=data.index, dtype=float)


def _numeric_column(data: pd.DataFrame, column: str | None, label: str) -> pd.Series:
    resolved = _require_column(data, column, label)
    series = pd.to_numeric(data[resolved], errors="coerce")
    if series.isna().any():
        raise OFIDataError(f"Column '{resolved}' contains non-numeric values for {label}.")
    return series.astype(float)


def _require_column(data: pd.DataFrame, column: str | None, label: str) -> str:
    if not column:
        raise OFIDataError(f"Missing column mapping for {label}.")
    if column not in data.columns:
        raise OFIDataError(f"Required column '{column}' for {label} is not present.")
    return column


def _has_columns(data: pd.DataFrame, *columns: str | None) -> bool:
    return all(column is not None and column in data.columns for column in columns)


def _price_column(columns: ColumnMapping) -> str:
    return columns.price_col or columns.close_col or "close"


def _timestamp_or_none(value: pd.Timestamp) -> str | None:
    if pd.isna(value):
        return None
    return value.isoformat()
