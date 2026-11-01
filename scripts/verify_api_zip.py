"""Verify required contents and imports for an API Lambda ZIP package."""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path


REQUIRED_FILES = {
    "backend/__init__.py",
    "backend/api/__init__.py",
    "backend/api/lambda_handler.py",
    "backend/ingestion/curated_catalog.json",
}
FORBIDDEN_FILES = {
    "backend/ingestion/process_prices.py",
    "backend/ingestion/import_data.py",
    "backend/tests/",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()

    with zipfile.ZipFile(args.package) as package:
        names = set(package.namelist())
        missing = REQUIRED_FILES - names
        if missing:
            raise SystemExit(f"Missing package files: {sorted(missing)}")
        if any(name.endswith(".parquet") for name in names):
            raise SystemExit("Package must not contain Parquet datasets")
        if any(
            name in FORBIDDEN_FILES
            or name.startswith("backend/tests/")
            or name.endswith((".pyc", ".pyo"))
            for name in names
        ):
            raise SystemExit("Package contains excluded development or ingestion files")
        with tempfile.TemporaryDirectory(prefix="grocery-api-verify-") as directory:
            package.extractall(directory)
            sys.path.insert(0, directory)
            from backend.api.lambda_handler import handler
            from backend.ingestion.curated_catalog import load_curated_catalog

            assert handler
            assert load_curated_catalog().products
    print(f"Verified {args.package} ({args.package.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
