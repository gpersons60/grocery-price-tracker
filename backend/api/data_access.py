"""DynamoDB access patterns used by the read-only API."""

from __future__ import annotations

from typing import Any, Protocol

from boto3.dynamodb.conditions import Key

HISTORY_INDEX_NAME = "ProductStoreHistoryIndex"


class Table(Protocol):
    def scan(self, **kwargs: Any) -> dict[str, Any]:
        ...

    def query(self, **kwargs: Any) -> dict[str, Any]:
        ...


def get_table(table_name: str, region_name: str | None = None) -> Table:
    """Create a DynamoDB Table using Boto3's default credential chain."""
    import boto3

    return boto3.resource("dynamodb", region_name=region_name).Table(table_name)


def scan_all(table: Table, *, page_size: int = 100) -> list[dict[str, Any]]:
    """Read every catalogue page without relying on a single Scan response."""
    items: list[dict[str, Any]] = []
    request: dict[str, Any] = {"Limit": page_size}
    while True:
        response = table.scan(**request)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        request["ExclusiveStartKey"] = last_key


def query_history(
    table: Table,
    *,
    product_store_key: str,
    start_sort_key: str | None = None,
    end_sort_key: str | None = None,
    page_size: int = 100,
    exclusive_start_key: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Query one bounded page for one product/store."""
    key_condition = Key("productStoreKey").eq(product_store_key)
    if start_sort_key is not None and end_sort_key is not None:
        key_condition = key_condition & Key("observationSortKey").between(
            start_sort_key, end_sort_key
        )

    items: list[dict[str, Any]] = []
    request: dict[str, Any] = {
        "IndexName": HISTORY_INDEX_NAME,
        "KeyConditionExpression": key_condition,
        "Limit": page_size,
        "ScanIndexForward": True,
    }
    if exclusive_start_key is not None:
        request["ExclusiveStartKey"] = exclusive_start_key
    response = table.query(**request)
    items.extend(response.get("Items", []))
    return items, response.get("LastEvaluatedKey")


def query_latest(
    table: Table, *, product_store_key: str
) -> dict[str, Any] | None:
    """Return the newest indexed observation for a product/store."""
    response = table.query(
        IndexName=HISTORY_INDEX_NAME,
        KeyConditionExpression=Key("productStoreKey").eq(product_store_key),
        Limit=1,
        ScanIndexForward=False,
    )
    items = response.get("Items", [])
    return items[0] if items else None
