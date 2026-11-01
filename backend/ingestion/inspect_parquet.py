"""Inspect the metadata and a small sample from a local Parquet file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import pyarrow as pa
import pyarrow.parquet as pq


def inspect_parquet(path: Path) -> None:
    """Print row count, schema, and up to three records from *path*."""
    parquet_file = pq.ParquetFile(path)
    print(f"Rows: {parquet_file.metadata.num_rows}")
    print("Columns:")
    for field in parquet_file.schema_arrow:
        print(f"  {field.name}: {field.type}")

    print("Sample records:")
    batches = parquet_file.iter_batches(batch_size=3)
    try:
        sample = next(batches)
    except StopIteration:
        return

    for record in pa.Table.from_batches([sample]).to_pylist():
        print(f"  {record}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Parquet inspection command and return its exit status."""
    parser = argparse.ArgumentParser(
        description="Inspect a local Parquet file without reading the full dataset."
    )
    parser.add_argument("path", type=Path, help="path to a local Parquet file")
    args = parser.parse_args(argv)

    try:
        inspect_parquet(args.path)
    except FileNotFoundError:
        print(f"Error: Parquet file not found: {args.path}", file=sys.stderr)
        return 1
    except (OSError, pa.ArrowException) as error:
        print(f"Error: unable to read Parquet file '{args.path}': {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
