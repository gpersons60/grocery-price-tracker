"""AWS Lambda entry point for the daily Open Prices import."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import boto3

from backend.ingestion.curated_catalog import load_curated_catalog
from backend.ingestion.import_data import save_products
from backend.ingestion.price_storage import save_observations
from backend.ingestion.process_prices import iter_normalized_observations


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
SOURCE_URL = (
    "https://huggingface.co/datasets/openfoodfacts/open-prices/"
    "resolve/main/prices.parquet"
)
DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def _download_source(destination: Path) -> None:
    """Stream the source Parquet file into *destination*."""
    with urlopen(SOURCE_URL, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        with destination.open("wb") as output:
            while chunk := response.read(DOWNLOAD_CHUNK_SIZE):
                output.write(chunk)


def handler(event: Any, context: Any) -> dict[str, Any]:
    """Download, normalize, and persist the current curated observations."""
    del event, context
    products_table_name = os.environ["PRODUCTS_TABLE"]
    observations_table_name = os.environ["DYNAMODB_TABLE"]
    region = os.environ["AWS_REGION"]
    catalog = load_curated_catalog()
    session = boto3.Session(region_name=region)
    resource = session.resource("dynamodb")
    products_table = resource.Table(products_table_name)
    observations_table = resource.Table(observations_table_name)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            dir="/tmp",
            prefix="open-prices-",
            suffix=".parquet",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        _download_source(temporary_path)

        product_counts = save_products(products_table, catalog.products)
        observation_counts = save_observations(
            observations_table,
            iter_normalized_observations(temporary_path, catalog),
        )
        summary = {
            "products": {
                "inserted": product_counts.inserted,
                "updated": product_counts.updated,
                "skipped": product_counts.skipped,
            },
            "priceObservations": {
                "inserted": observation_counts.inserted,
                "updated": observation_counts.updated,
                "skipped": observation_counts.skipped,
            },
        }
        LOGGER.info("Open Prices import completed: %s", json.dumps(summary))
        return summary
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


lambda_handler = handler
