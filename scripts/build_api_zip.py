"""Build the read-only API Lambda ZIP package on Windows or other hosts."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGE_NAME = "grocery-api-lambda.zip"


def main() -> int:
    package_path = DIST / PACKAGE_NAME
    with tempfile.TemporaryDirectory(prefix="grocery-api-build-") as directory:
        staging = Path(directory)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-compile",
                "--target",
                str(staging),
                "--requirement",
                str(ROOT / "backend" / "requirements.api.txt"),
            ],
            check=True,
            cwd=ROOT,
        )
        copy_files = [
            ROOT / "backend" / "__init__.py",
            ROOT / "backend" / "api" / "__init__.py",
            ROOT / "backend" / "api" / "data_access.py",
            ROOT / "backend" / "api" / "lambda_handler.py",
            ROOT / "backend" / "api" / "service.py",
            ROOT / "backend" / "ingestion" / "__init__.py",
            ROOT / "backend" / "ingestion" / "curated_catalog.py",
            ROOT / "backend" / "ingestion" / "curated_catalog.json",
        ]
        for source in copy_files:
            destination = staging / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        DIST.mkdir(exist_ok=True)
        if package_path.exists():
            package_path.unlink()
        shutil.make_archive(
            str(package_path.with_suffix("")),
            "zip",
            root_dir=staging,
        )
    print(f"Created {package_path} ({package_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
