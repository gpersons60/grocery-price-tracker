from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from backend.ingestion.inspect_parquet import main


def write_parquet(path: Path, row_count: int = 4) -> None:
    table = pa.table(
        {
            "barcode": [f"000{i}" for i in range(row_count)],
            "price": [f"{i + 1}.25" for i in range(row_count)],
        }
    )
    pq.write_table(table, path)


def test_inspection_prints_metadata_schema_and_at_most_three_records(
    tmp_path: Path, capsys
) -> None:
    parquet_path = tmp_path / "prices.parquet"
    write_parquet(parquet_path)

    assert main([str(parquet_path)]) == 0

    output = capsys.readouterr().out
    assert "Rows: 4" in output
    assert "barcode: string" in output
    assert "price: string" in output
    assert output.count("'barcode':") == 3


def test_inspection_handles_missing_file(tmp_path: Path, capsys) -> None:
    missing_path = tmp_path / "missing.parquet"

    assert main([str(missing_path)]) != 0

    assert f"Error: Parquet file not found: {missing_path}" in capsys.readouterr().err


def test_inspection_handles_invalid_file(tmp_path: Path, capsys) -> None:
    invalid_path = tmp_path / "invalid.parquet"
    invalid_path.write_text("not parquet", encoding="utf-8")

    assert main([str(invalid_path)]) != 0

    assert "Error: unable to read Parquet file" in capsys.readouterr().err


def test_inspection_prints_timezone_aware_timestamp(tmp_path: Path, capsys) -> None:
    parquet_path = tmp_path / "timestamps.parquet"
    table = pa.table(
        {
            "observed_at": pa.array(
                [datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)],
                type=pa.timestamp("us", tz="UTC"),
            )
        }
    )
    pq.write_table(table, parquet_path)

    assert main([str(parquet_path)]) == 0

    output = capsys.readouterr().out
    assert "observed_at: timestamp[us, tz=UTC]" in output
    assert "datetime.datetime(2026, 10, 28, 12, 0" in output
    assert "zoneinfo.ZoneInfo(key='UTC')" in output
