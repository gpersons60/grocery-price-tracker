"""Manually import the curated catalogue and normalized observations."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import boto3
from botocore.exceptions import ClientError

from backend.ingestion.curated_catalog import CuratedCatalog, load_curated_catalog
from backend.ingestion.price_storage import StorageCounts, save_observations
from backend.ingestion.process_prices import (
    NormalizedObservation,
    iter_normalized_observations,
)


@dataclass(frozen=True)
class ProductCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def save_products(table: Any, products: Iterable[dict[str, str]]) -> ProductCounts:
    """Insert catalogue products without overwriting existing records."""
    inserted = skipped = 0
    for product in products:
        try:
            table.put_item(
                Item={"barcode": product["barcode"], "name": product["name"]},
                ConditionExpression="attribute_not_exists(barcode)",
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != (
                "ConditionalCheckFailedException"
            ):
                raise
            skipped += 1
        else:
            inserted += 1
    return ProductCounts(inserted=inserted, skipped=skipped)


def import_data(
    parquet_path: Path,
    *,
    profile: str | None,
    region: str,
    products_table_name: str,
    observations_table_name: str,
    apply: bool,
    catalog: CuratedCatalog | None = None,
) -> tuple[ProductCounts, StorageCounts] | None:
    """Run a dry run or apply the import to DynamoDB."""
    catalog = catalog or load_curated_catalog()
    observations = iter_normalized_observations(parquet_path, catalog)

    if not apply:
        observation_count = sum(1 for _ in observations)
        print(
            f"Dry run: {len(catalog.products)} products and "
            f"{observation_count} price observations would be imported."
        )
        return None

    session = boto3.Session(profile_name=profile, region_name=region)
    resource = session.resource("dynamodb")
    product_counts = save_products(
        resource.Table(products_table_name),
        catalog.products,
    )
    observation_counts = save_observations(
        resource.Table(observations_table_name),
        observations,
    )
    print(
        "Products: "
        f"inserted={product_counts.inserted}, "
        f"updated={product_counts.updated}, "
        f"skipped={product_counts.skipped}"
    )
    print(
        "Price observations: "
        f"inserted={observation_counts.inserted}, "
        f"updated={observation_counts.updated}, "
        f"skipped={observation_counts.skipped}"
    )
    return product_counts, observation_counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import curated products and normalized price observations."
    )
    parser.add_argument("parquet_path", type=Path, help="path to the source Parquet file")
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="AWS profile (default: AWS_PROFILE or SDK default)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-2"),
        help="AWS region (default: AWS_REGION or us-east-2)",
    )
    parser.add_argument(
        "--products-table",
        default=os.environ.get("PRODUCTS_TABLE", "Products"),
        help="Products table name (default: PRODUCTS_TABLE or Products)",
    )
    parser.add_argument(
        "--observations-table",
        default=os.environ.get("DYNAMODB_TABLE", "PriceObservations"),
        help=(
            "PriceObservations table name "
            "(default: DYNAMODB_TABLE or PriceObservations)"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the import to DynamoDB; otherwise only count records",
    )
    args = parser.parse_args(argv)

    import_data(
        args.parquet_path,
        profile=args.profile,
        region=args.region,
        products_table_name=args.products_table,
        observations_table_name=args.observations_table,
        apply=args.apply,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
