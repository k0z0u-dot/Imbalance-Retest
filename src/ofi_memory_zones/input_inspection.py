from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ofi_memory_zones.column_detection import detected_column_mapping_report, infer_column_mapping_from_columns
from ofi_memory_zones.schema import ColumnMapping

READY = "READY"
USABLE_WITH_WARNINGS = "USABLE_WITH_WARNINGS"
NOT_READY = "NOT_READY"


def inspect_input_csv(input_path: str | Path, columns: ColumnMapping | None = None) -> dict[str, object]:
    cols = columns or ColumnMapping()
    raw = pd.read_csv(input_path)
    cols = infer_column_mapping_from_columns(raw.columns, cols)
    rows = len(raw)

    timestamp_series = _parsed_timestamps(raw, cols.timestamp_col)
    timestamp_parseable = bool(timestamp_series is not None and timestamp_series.notna().all())
    monotonic = bool(timestamp_parseable and timestamp_series.is_monotonic_increasing)
    duplicate_count = int(timestamp_series.duplicated().sum()) if timestamp_parseable else 0

    interval_seconds = _inferred_interval_seconds(timestamp_series) if timestamp_parseable else None
    duration_seconds = _duration_seconds(timestamp_series) if timestamp_parseable else None

    price_cols = [c for c in [cols.price_col, cols.open_col, cols.high_col, cols.low_col, cols.close_col] if c in raw.columns]
    detected_ohlc = [c for c in [cols.open_col, cols.high_col, cols.low_col, cols.close_col] if c and c in raw.columns]
    high_low_available = bool((cols.high_col in raw.columns) and (cols.low_col in raw.columns))
    volume_available = bool(cols.volume_col and cols.volume_col in raw.columns)

    flow_source, proxy_used = _detect_flow_source(raw, cols)

    result: dict[str, object] = {
        "rows": int(rows),
        "columns": sorted(raw.columns.tolist()),
        "start_timestamp": _ts_to_str(timestamp_series.min()) if timestamp_parseable and rows else None,
        "end_timestamp": _ts_to_str(timestamp_series.max()) if timestamp_parseable and rows else None,
        "timestamp_parseable": timestamp_parseable,
        "timestamp_monotonic": monotonic,
        "duplicate_timestamp_count": duplicate_count,
        "inferred_bar_interval_seconds": interval_seconds,
        "duration_seconds": duration_seconds,
        "detected_price_columns": sorted(set(price_cols)),
        "detected_ohlc_columns": detected_ohlc,
        "high_low_available": high_low_available,
        "volume_available": volume_available,
        "detected_flow_source": flow_source,
        "proxy_used": proxy_used,
        "taker_buy_volume_coverage": _coverage(raw, cols.taker_buy_col),
        "taker_sell_volume_coverage": _coverage(raw, cols.taker_sell_col),
        "buy_volume_coverage": _coverage(raw, cols.buy_volume_col),
        "sell_volume_coverage": _coverage(raw, cols.sell_volume_col),
        "signed_volume_coverage": _coverage(raw, cols.signed_volume_col),
        "total_flow_zero_rate": _flow_zero_rate(raw, cols, flow_source),
        "null_rate_by_relevant_column": _null_rates(raw, cols),
        "detected_column_mapping": detected_column_mapping_report(cols),
        "warnings": [],
        "readiness_verdict": NOT_READY,
    }

    warnings = _build_warnings(result)
    result["warnings"] = warnings
    result["readiness_verdict"] = _readiness_verdict(result, warnings)
    return result


def write_input_diagnostics_reports(diagnostics: dict[str, object], input_path: str, output_dir: str | Path) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "input_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "input_diagnostics.md").write_text(_build_markdown(diagnostics, input_path), encoding="utf-8")


def _build_markdown(d: dict[str, object], input_path: str) -> str:
    warnings = d.get("warnings", [])
    warning_lines = "\n".join(f"- {w}" for w in warnings) if warnings else "- None"
    missing = _missing_readiness_columns(d)
    if d["readiness_verdict"] in {READY, USABLE_WITH_WARNINGS}:
        next_cmd = (
            f"python -m scripts.run_ofi_zone_study --input {input_path} --output output/ofi_real_smoke "
            "--config-json configs/ofi_loose.json"
        )
    else:
        next_cmd = f"不足列/品質問題を解消してください。Missing flow requirements: {', '.join(missing) if missing else 'N/A'}"

    return f"""# Input Diagnostics

## Basic Info
- rows: {d['rows']}
- columns: {len(d['columns'])}
- start_timestamp: {d['start_timestamp']}
- end_timestamp: {d['end_timestamp']}
- inferred_bar_interval_seconds: {d['inferred_bar_interval_seconds']}
- duration_seconds: {d['duration_seconds']}

## Timestamp Quality
- timestamp_parseable: {d['timestamp_parseable']}
- timestamp_monotonic: {d['timestamp_monotonic']}
- duplicate_timestamp_count: {d['duplicate_timestamp_count']}

## Price/OHLC Columns
- detected_price_columns: {d['detected_price_columns']}
- detected_ohlc_columns: {d['detected_ohlc_columns']}
- high_low_available: {d['high_low_available']}
- volume_available: {d['volume_available']}

## Flow Source Detection
- detected_flow_source: {d['detected_flow_source']}
- proxy_used: {d['proxy_used']}
- detected_column_mapping:
  - taker_buy_col: {d['detected_column_mapping'].get('taker_buy_col')}
  - taker_sell_col: {d['detected_column_mapping'].get('taker_sell_col')}
  - buy_volume_col: {d['detected_column_mapping'].get('buy_volume_col')}
  - sell_volume_col: {d['detected_column_mapping'].get('sell_volume_col')}
  - side_col: {d['detected_column_mapping'].get('side_col')}
  - size_col: {d['detected_column_mapping'].get('size_col')}
  - signed_volume_col: {d['detected_column_mapping'].get('signed_volume_col')}

## Coverage / Null Rates
- taker_buy_volume_coverage: {d['taker_buy_volume_coverage']}
- taker_sell_volume_coverage: {d['taker_sell_volume_coverage']}
- buy_volume_coverage: {d['buy_volume_coverage']}
- sell_volume_coverage: {d['sell_volume_coverage']}
- signed_volume_coverage: {d['signed_volume_coverage']}
- total_flow_zero_rate: {d['total_flow_zero_rate']}
- null_rate_by_relevant_column: {d['null_rate_by_relevant_column']}

## Warnings
{warning_lines}

## Readiness Verdict
- {d['readiness_verdict']}

## Recommended Next Command
```bash
{next_cmd}
```
"""


def _build_warnings(d: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    if not d["timestamp_parseable"]:
        warnings.append("timestamp parse failed for at least one row")
    if not d["timestamp_monotonic"]:
        warnings.append("timestamp is not monotonic increasing")
    if d["duplicate_timestamp_count"]:
        warnings.append("duplicate timestamps found")
    if not d["high_low_available"]:
        warnings.append("high/low missing: first-touch outcome quality is weaker")
    if d["detected_flow_source"] == "none":
        warnings.append("no usable flow source detected")
    if d["proxy_used"]:
        warnings.append("proxy flow source used: conclusions are weaker")
    return warnings


def _readiness_verdict(d: dict[str, object], warnings: list[str]) -> str:
    if d["rows"] == 0 or d["detected_flow_source"] == "none" or not d["timestamp_parseable"]:
        return NOT_READY
    if warnings:
        return USABLE_WITH_WARNINGS
    return READY


def _parsed_timestamps(raw: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in raw.columns:
        return None
    return pd.to_datetime(raw[column], errors="coerce", utc=True)


def _inferred_interval_seconds(ts: pd.Series | None) -> int | None:
    if ts is None or len(ts) < 2:
        return None
    diffs = ts.sort_values().diff().dropna()
    if diffs.empty:
        return None
    return int(diffs.dt.total_seconds().median())


def _duration_seconds(ts: pd.Series | None) -> int | None:
    if ts is None or ts.dropna().empty:
        return None
    return int((ts.max() - ts.min()).total_seconds())


def _coverage(raw: pd.DataFrame, col: str | None) -> float:
    if not col or col not in raw.columns or len(raw) == 0:
        return 0.0
    return float(raw[col].notna().mean())


def _detect_flow_source(raw: pd.DataFrame, cols: ColumnMapping) -> tuple[str, bool]:
    if _has(raw, cols.taker_buy_col, cols.taker_sell_col):
        return "taker_buy_sell", False
    if _has(raw, cols.buy_volume_col, cols.sell_volume_col):
        return "buy_sell_proxy", True
    if _has(raw, cols.side_col, cols.size_col):
        return "side_size_proxy", True
    if _has(raw, cols.signed_volume_col):
        return "signed_proxy", True
    return "none", False


def _has(raw: pd.DataFrame, *cands: str | None) -> bool:
    return all(c and c in raw.columns for c in cands)


def _flow_zero_rate(raw: pd.DataFrame, cols: ColumnMapping, source: str) -> float | None:
    if len(raw) == 0:
        return None
    if source == "taker_buy_sell":
        total = pd.to_numeric(raw[cols.taker_buy_col], errors="coerce").fillna(0) + pd.to_numeric(raw[cols.taker_sell_col], errors="coerce").fillna(0)
    elif source == "buy_sell_proxy":
        total = pd.to_numeric(raw[cols.buy_volume_col], errors="coerce").fillna(0) + pd.to_numeric(raw[cols.sell_volume_col], errors="coerce").fillna(0)
    elif source == "side_size_proxy":
        total = pd.to_numeric(raw[cols.size_col], errors="coerce").fillna(0)
    elif source == "signed_proxy":
        total = pd.to_numeric(raw[cols.signed_volume_col], errors="coerce").abs().fillna(0)
    else:
        return None
    return float((total == 0).mean())


def _null_rates(raw: pd.DataFrame, cols: ColumnMapping) -> dict[str, float | None]:
    relevant = [
        cols.timestamp_col,
        cols.price_col,
        cols.open_col,
        cols.high_col,
        cols.low_col,
        cols.close_col,
        cols.volume_col,
        cols.taker_buy_col,
        cols.taker_sell_col,
        cols.buy_volume_col,
        cols.sell_volume_col,
        cols.signed_volume_col,
        cols.side_col,
        cols.size_col,
    ]
    out: dict[str, float | None] = {}
    for col in relevant:
        if not col:
            continue
        out[col] = float(raw[col].isna().mean()) if col in raw.columns and len(raw) else None
    return out


def _missing_readiness_columns(d: dict[str, object]) -> list[str]:
    if d["detected_flow_source"] != "none":
        return []
    return ["taker_buy+taker_sell or buy+sell or side+size or signed_volume"]


def _ts_to_str(ts: pd.Timestamp) -> str | None:
    if pd.isna(ts):
        return None
    return ts.isoformat()
