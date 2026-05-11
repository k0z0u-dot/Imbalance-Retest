from __future__ import annotations

import subprocess
import sys

import pandas as pd

from ofi_memory_zones.input_inspection import READY, NOT_READY, USABLE_WITH_WARNINGS, inspect_input_csv, write_input_diagnostics_reports
from ofi_memory_zones.schema import ColumnMapping


def test_taker_buy_sell_is_ready(tmp_path) -> None:
    path = tmp_path / "x.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=5, freq="min"),
            "high": [1, 2, 3, 4, 5],
            "low": [1, 2, 3, 4, 5],
            "close": [1, 2, 3, 4, 5],
            "taker_buy_volume": [1, 1, 1, 1, 1],
            "taker_sell_volume": [1, 2, 1, 2, 1],
        }
    ).to_csv(path, index=False)
    d = inspect_input_csv(path, ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"))
    assert d["detected_flow_source"] == "taker_buy_sell"
    assert d["readiness_verdict"] == READY


def test_signed_only_is_proxy_warning(tmp_path) -> None:
    path = tmp_path / "s.csv"
    pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=4, freq="min"), "signed_volume": [1, -1, 0.5, -0.5]}).to_csv(path, index=False)
    d = inspect_input_csv(path, ColumnMapping(signed_volume_col="signed_volume", high_col=None, low_col=None))
    assert d["proxy_used"] is True
    assert d["readiness_verdict"] == USABLE_WITH_WARNINGS


def test_no_flow_is_not_ready(tmp_path) -> None:
    path = tmp_path / "n.csv"
    pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=3, freq="min"), "close": [1, 2, 3]}).to_csv(path, index=False)
    d = inspect_input_csv(path, ColumnMapping(taker_buy_col=None, taker_sell_col=None, high_col=None, low_col=None))
    assert d["readiness_verdict"] == NOT_READY


def test_non_monotonic_warning(tmp_path) -> None:
    path = tmp_path / "m.csv"
    pd.DataFrame(
        {
            "timestamp": ["2026-01-01T00:01:00Z", "2026-01-01T00:00:00Z"],
            "taker_buy_volume": [1, 1],
            "taker_sell_volume": [1, 1],
        }
    ).to_csv(path, index=False)
    d = inspect_input_csv(path, ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"))
    assert "timestamp is not monotonic increasing" in d["warnings"]


def test_missing_high_low_warning(tmp_path) -> None:
    path = tmp_path / "hl.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="min"),
            "close": [1, 2],
            "taker_buy_volume": [1, 1],
            "taker_sell_volume": [1, 1],
        }
    ).to_csv(path, index=False)
    d = inspect_input_csv(path, ColumnMapping(taker_buy_col="taker_buy_volume", taker_sell_col="taker_sell_volume"))
    assert "high/low missing" in " ".join(d["warnings"])


def test_cli_writes_json_and_md(tmp_path) -> None:
    input_path = tmp_path / "c.csv"
    out = tmp_path / "out"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="min"),
            "close": [1, 2, 3, 4],
            "taker_buy_volume": [1, 1, 1, 1],
            "taker_sell_volume": [1, 1, 1, 1],
        }
    ).to_csv(input_path, index=False)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.inspect_ofi_input",
            "--input",
            str(input_path),
            "--output",
            str(out),
        ],
        check=True,
    )
    assert (out / "input_diagnostics.json").exists()
    assert (out / "input_diagnostics.md").exists()


def test_auto_detect_taker_columns_without_cli_mapping(tmp_path) -> None:
    path = tmp_path / "auto.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="min"),
            "close": [1, 2, 3, 4],
            "taker_buy_volume": [1, 1, 2, 2],
            "taker_sell_volume": [1, 1, 1, 1],
        }
    ).to_csv(path, index=False)
    d = inspect_input_csv(path, ColumnMapping(high_col=None, low_col=None))
    assert d["detected_flow_source"] == "taker_buy_sell"
    assert d["readiness_verdict"] == USABLE_WITH_WARNINGS
    assert d["detected_column_mapping"]["taker_buy_col"] == "taker_buy_volume"


def test_markdown_report_includes_detected_mapping(tmp_path) -> None:
    input_path = tmp_path / "m.csv"
    out = tmp_path / "out"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="min"),
            "close": [1, 2],
            "taker_buy_volume": [1, 1],
            "taker_sell_volume": [1, 1],
        }
    ).to_csv(input_path, index=False)
    d = inspect_input_csv(input_path, ColumnMapping(high_col=None, low_col=None))
    write_path = out
    write_input_diagnostics_reports(d, str(input_path), write_path)
    md = (write_path / "input_diagnostics.md").read_text(encoding="utf-8")
    assert "- detected_column_mapping:" in md
    assert "- taker_buy_col: taker_buy_volume" in md
    assert "- taker_sell_col: taker_sell_volume" in md
