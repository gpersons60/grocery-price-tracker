"""Opt-in live DynamoDB smoke test for the observation persistence layer."""

from __future__ import annotations

import argparse
import os
from decimal import Decimal
from typing import Any
from uuid import uuid4

import boto3

from backend.ingestion.process_prices import NormalizedObservation
from backend.ingestion.price_storage import save_observation


def _observation(
    source_id: str,
    *,
    updated: str,
    date: str,
    store: str,
    price: str,
) -> NormalizedObservation:
    return NormalizedObservation(
        sourceObservationId=source_id,
        barcode="3256540000346",
        storeId=store,
        observedDate=date,
        price=Decimal(price),
        currency="EUR",
        sourceUpdated=updated,
    )


def _stored_item(table: Any, source_id: str) -> dict[str, Any] | None:
    response = table.get_item(
        Key={"sourceObservationId": source_id},
        ConsistentRead=True,
    )
    return response.get("Item")


def _matches_observation(item: dict[str, Any], observation: NormalizedObservation) -> bool:
    return all(
        item.get(key) == value
        for key, value in {
            "barcode": observation.barcode,
            "storeId": observation.storeId,
            "price": observation.price,
            "currency": observation.currency,
            "observedDate": observation.observedDate,
            "productStoreKey": f"{observation.barcode}#{observation.storeId}",
            "observationSortKey": (
                f"{observation.observedDate}#{observation.sourceObservationId}"
            ),
            "sourceUpdatedAt": observation.sourceUpdated,
        }.items()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="AWS CLI profile (default: AWS_PROFILE or SDK default)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-2"),
        help="AWS region (default: AWS_REGION or us-east-2)",
    )
    parser.add_argument(
        "--table",
        default=os.environ.get("DYNAMODB_TABLE", "PriceObservations"),
        help="DynamoDB table name (default: DYNAMODB_TABLE or PriceObservations)",
    )
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    table = session.resource("dynamodb").Table(args.table)
    source_id = f"smoke-{uuid4()}"
    initial = _observation(
        source_id,
        updated="2026-10-31T12:00:00.123456Z",
        date="2026-10-20",
        store="271",
        price="1.230",
    )
    older = _observation(
        source_id,
        updated="2026-10-31T11:00:00.123456Z",
        date="2026-10-19",
        store="999",
        price="9.990",
    )
    newer = _observation(
        source_id,
        updated="2026-10-31T13:00:00.123456Z",
        date="2026-10-21",
        store="3241",
        price="2.500",
    )
    if _stored_item(table, source_id) is not None:
        raise AssertionError(f"Generated observation ID already exists: {source_id}")

    inserted = False
    try:
        assert save_observation(table, initial) == "inserted"
        inserted = True
        assert save_observation(table, initial) == "skipped"
        assert save_observation(table, older) == "skipped"

        assert save_observation(table, newer) == "updated"
        item = _stored_item(table, source_id)
        if item is None:
            raise AssertionError(f"Temporary observation {source_id} was not stored")
        assert item["price"] == Decimal("2.500")
        assert item["observedDate"] == "2026-10-21"
        assert item["storeId"] == "3241"
        assert item["productStoreKey"] == "3256540000346#3241"
        assert item["observationSortKey"] == f"2026-10-21#{source_id}"
        print("DynamoDB smoke test passed")
    finally:
        if inserted:
            item = _stored_item(table, source_id)
            if item is not None and (
                _matches_observation(item, initial)
                or _matches_observation(item, newer)
            ):
                table.delete_item(Key={"sourceObservationId": source_id})


if __name__ == "__main__":
    main()
