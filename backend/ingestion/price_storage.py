"""DynamoDB persistence for normalized price observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Protocol

from botocore.exceptions import ClientError

from backend.ingestion.process_prices import NormalizedObservation


class DynamoTable(Protocol):
    """Minimal DynamoDB Table interface used by the persistence layer."""

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class StorageCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def get_price_observations_table(
    table_name: str,
    region_name: str | None = None,
) -> DynamoTable:
    """Create a boto3 DynamoDB Table resource without requiring it in unit tests."""
    import boto3

    resource = boto3.resource("dynamodb", region_name=region_name)
    return resource.Table(table_name)


def _source_version(observation: NormalizedObservation) -> int | None:
    if observation.sourceUpdated is None:
        return None
    timestamp = datetime.fromisoformat(observation.sourceUpdated.replace("Z", "+00:00"))
    delta = timestamp - datetime(1970, 1, 1, tzinfo=timestamp.tzinfo)
    return (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )


def _item(observation: NormalizedObservation) -> dict[str, Any]:
    item: dict[str, Any] = {
        "barcode": observation.barcode,
        "storeId": observation.storeId,
        "price": observation.price,
        "currency": observation.currency,
        "observedDate": observation.observedDate,
        "productStoreKey": f"{observation.barcode}#{observation.storeId}",
        "observationSortKey": (
            f"{observation.observedDate}#{observation.sourceObservationId}"
        ),
    }
    version = _source_version(observation)
    if version is not None:
        item["sourceUpdatedAt"] = observation.sourceUpdated
        item["sourceVersion"] = version
    return item


def save_observation(
    table: DynamoTable,
    observation: NormalizedObservation,
) -> str:
    """Conditionally persist one observation and return inserted, updated, or skipped."""
    item = _item(observation)
    version = _source_version(observation)
    expression_values: dict[str, Any] = {}
    if version is not None:
        condition = (
            "attribute_not_exists(sourceObservationId) OR "
            "(attribute_not_exists(sourceVersion) OR sourceVersion < :sourceVersion)"
        )
        expression_values[":sourceVersion"] = version
    else:
        condition = "attribute_not_exists(sourceObservationId)"

    names = {f"#{key}": key for key in item}
    values = {f":{key}": value for key, value in item.items()}
    values.update(expression_values)
    update_expression = "SET " + ", ".join(
        f"#{key} = :{key}" for key in item
    )
    try:
        response = table.update_item(
            Key={"sourceObservationId": observation.sourceObservationId},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ConditionExpression=condition,
            ReturnValues="ALL_OLD",
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            return "skipped"
        raise
    return "updated" if response.get("Attributes") else "inserted"


def save_observations(
    table: DynamoTable,
    observations: Iterable[NormalizedObservation],
) -> StorageCounts:
    """Persist observations one at a time and return accurate outcome counts."""
    inserted = updated = skipped = 0
    for observation in observations:
        result = save_observation(table, observation)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        else:
            skipped += 1
    return StorageCounts(inserted=inserted, updated=updated, skipped=skipped)
