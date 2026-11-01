from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from botocore.exceptions import ClientError

from backend.ingestion.process_prices import NormalizedObservation
from backend.ingestion.price_storage import save_observation, save_observations


def observation(
    *,
    updated: str | None = "2026-10-31T12:00:00.123456Z",
    date: str = "2026-10-20",
    store: str = "271",
    price: Decimal = Decimal("1.230"),
) -> NormalizedObservation:
    return NormalizedObservation(
        sourceObservationId="123",
        barcode="3256540000346",
        storeId=store,
        observedDate=date,
        price=price,
        currency="EUR",
        sourceUpdated=updated,
    )


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self.calls: list[dict[str, Any]] = []

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        key = kwargs["Key"]["sourceObservationId"]
        names = kwargs["ExpressionAttributeNames"]
        if "sourceObservationId" in names.values():
            raise AssertionError("partition key must not be updated")
        existing = self.items.get(key)
        values = kwargs["ExpressionAttributeValues"]
        incoming_version = values.get(":sourceVersion")
        if existing is not None:
            existing_version = existing.get("sourceVersion")
            allowed = (
                incoming_version is not None
                and (
                    existing_version is None
                    or existing_version < incoming_version
                )
            )
            if not allowed:
                raise ClientError(
                    {"Error": {"Code": "ConditionalCheckFailedException"}},
                    "UpdateItem",
                )

        old = existing.copy() if existing is not None else None
        self.items[key] = {
            names[name]: values[name.replace("#", ":")]
            for name in names
        }
        self.items[key]["sourceObservationId"] = key
        return {"Attributes": old} if old is not None else {}


def test_request_excludes_partition_key_and_uses_atomic_condition() -> None:
    table = FakeTable()

    assert save_observation(table, observation()) == "inserted"

    request = table.calls[-1]
    assert request["Key"] == {"sourceObservationId": "123"}
    assert request["ConditionExpression"] == (
        "attribute_not_exists(sourceObservationId) OR "
        "(attribute_not_exists(sourceVersion) OR sourceVersion < :sourceVersion)"
    )
    assert request["ReturnValues"] == "ALL_OLD"
    assert "sourceObservationId" not in request["ExpressionAttributeNames"].values()
    assert ":sourceObservationId" not in request["ExpressionAttributeValues"]
    assert "#barcode = :barcode" in request["UpdateExpression"]
    assert "#productStoreKey = :productStoreKey" in request["UpdateExpression"]
    assert "#observationSortKey = :observationSortKey" in request["UpdateExpression"]


def test_insert_repeat_and_correction_counts_are_distinct() -> None:
    table = FakeTable()
    newer = observation(updated="2026-10-31T12:00:00.223456Z", price=Decimal("2.50"))

    counts = save_observations(table, [observation(), observation(), newer])

    assert counts.inserted == 1
    assert counts.updated == 1
    assert counts.skipped == 1
    assert table.items["123"]["price"] == Decimal("2.50")


def test_older_and_equal_fractional_timestamp_corrections_are_skipped() -> None:
    table = FakeTable()
    assert save_observation(table, observation()) == "inserted"

    assert (
        save_observation(
            table,
            observation(updated="2026-10-31T12:00:00.123455Z"),
        )
        == "skipped"
    )
    assert (
        save_observation(
            table,
            observation(updated="2026-10-31T12:00:00.123456Z"),
        )
        == "skipped"
    )


def test_unversioned_record_can_insert_but_never_overwrite() -> None:
    table = FakeTable()

    assert save_observation(table, observation(updated=None)) == "inserted"
    assert save_observation(table, observation(updated=None, price=Decimal("9.99"))) == "skipped"
    assert table.items["123"]["price"] == Decimal("1.230")


def test_timestamped_correction_can_follow_unversioned_insert() -> None:
    table = FakeTable()

    assert save_observation(table, observation(updated=None)) == "inserted"
    assert (
        save_observation(
            table,
            observation(
                updated="2026-10-31T12:00:00.123457Z",
                price=Decimal("2.50"),
            ),
        )
        == "updated"
    )
    assert save_observation(table, observation(updated=None, price=Decimal("9.99"))) == "skipped"
    assert table.items["123"]["price"] == Decimal("2.50")


def test_correction_replaces_indexed_attributes_and_preserves_decimal() -> None:
    table = FakeTable()
    save_observation(table, observation())

    result = save_observation(
        table,
        observation(
            updated="2026-10-31T13:00:00.000001Z",
            date="2026-10-21",
            store="3241",
            price=Decimal("1.234567"),
        ),
    )

    assert result == "updated"
    item = table.items["123"]
    assert item["price"] == Decimal("1.234567")
    assert item["productStoreKey"] == "3256540000346#3241"
    assert item["observationSortKey"] == "2026-10-21#123"


def test_unexpected_dynamodb_errors_propagate() -> None:
    class FailingTable(FakeTable):
        def update_item(self, **kwargs: Any) -> dict[str, Any]:
            raise ClientError(
                {"Error": {"Code": "ProvisionedThroughputExceededException"}},
                "UpdateItem",
            )

    with pytest.raises(ClientError, match="ProvisionedThroughputExceededException"):
        save_observation(FailingTable(), observation())
