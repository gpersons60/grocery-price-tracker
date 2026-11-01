from __future__ import annotations

import json
import base64
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from backend.api.lambda_handler import handler
from backend.api.data_access import HISTORY_INDEX_NAME
from backend.api.service import (
    ApiService,
    ApiValidationError,
    NotFoundError,
)
from backend.ingestion.curated_catalog import load_curated_catalog


class FakeTable:
    def __init__(
        self,
        *,
        scan_pages: list[dict[str, Any]] | None = None,
        query_pages: list[dict[str, Any]] | None = None,
    ) -> None:
        self.scan_pages = iter(scan_pages or [{"Items": []}])
        self.query_pages = iter(query_pages or [{"Items": []}])
        self.scan_calls: list[dict[str, Any]] = []
        self.query_calls: list[dict[str, Any]] = []

    def scan(self, **kwargs: Any) -> dict[str, Any]:
        self.scan_calls.append(kwargs)
        return next(self.scan_pages)

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_calls.append(kwargs)
        return next(self.query_pages)


def product() -> dict[str, str]:
    return {"barcode": "123", "name": "Test product"}


def observation(
    source_id: str, observed_date: str, price: str, store_id: str = "271"
) -> dict[str, Any]:
    return {
        "sourceObservationId": source_id,
        "observedDate": observed_date,
        "price": Decimal(price),
        "currency": "EUR",
        "sourceUpdatedAt": "2026-10-01T12:00:00Z",
        "productStoreKey": f"123#{store_id}",
        "observationSortKey": f"{observed_date}#{source_id}",
    }


def service(
    products: FakeTable, observations: FakeTable, *, today: date = date(2026, 10, 31)
) -> ApiService:
    return ApiService(
        products,
        observations,
        catalog=load_curated_catalog(),
        today=lambda: today,
    )


def test_products_scan_handles_pagination() -> None:
    table = FakeTable(
        scan_pages=[
            {"Items": [{"barcode": "123", "name": "Test product"}], "LastEvaluatedKey": {"barcode": "123"}},
            {"Items": [{"barcode": "456", "name": "Second"}]},
        ]
    )

    assert service(table, FakeTable()).products() == [
        {"barcode": "123", "name": "Test product"},
        {"barcode": "456", "name": "Second"},
    ]
    assert table.scan_calls[1]["ExclusiveStartKey"] == {"barcode": "123"}


def test_history_filters_dates_and_preserves_decimal_values() -> None:
    observations = FakeTable(
        query_pages=[
            {
                "Items": [observation("1", "2026-10-01", "1.230")],
                "LastEvaluatedKey": {
                    "sourceObservationId": "1",
                    "productStoreKey": "123#271",
                    "observationSortKey": "2026-10-01#1",
                },
            },
            {"Items": [observation("2", "2026-10-20", "2.50")]},
        ]
    )

    result = service(FakeTable(scan_pages=[{"Items": [product()]}]), observations).history(
        "123", "271", "30d"
    )

    assert [item["price"] for item in result["observations"]] == ["1.230"]
    assert result["statistics"] == {
        "latestPrice": "1.230",
        "minimumPrice": "1.230",
        "maximumPrice": "1.230",
        "meanPrice": "1.230",
        "observationCount": 1,
    }
    assert len(observations.query_calls) == 1
    assert observations.query_calls[0]["Limit"] == 100
    assert observations.query_calls[0]["IndexName"] == HISTORY_INDEX_NAME
    expression = observations.query_calls[0]["KeyConditionExpression"].get_expression()
    assert expression["operator"] == "AND"
    partition_expression = expression["values"][0]
    range_expression = expression["values"][1]
    assert partition_expression.get_expression()["operator"] == "="
    assert partition_expression._values[0].name == "productStoreKey"
    assert partition_expression._values[1] == "123#271"
    assert range_expression.get_expression()["operator"] == "BETWEEN"
    assert range_expression._values[0].name == "observationSortKey"
    assert range_expression._values[1:] == (
        "2026-10-01#",
        "2026-10-31#\uffff",
    )
    assert "continuationToken" in result

    next_result = service(
        FakeTable(scan_pages=[{"Items": [product()]}]), observations
    ).history("123", "271", "30d", continuation_token=result["continuationToken"])
    assert [item["price"] for item in next_result["observations"]] == ["2.50"]
    assert "continuationToken" not in next_result
    assert observations.query_calls[1]["ExclusiveStartKey"] == {
        "sourceObservationId": "1",
        "productStoreKey": "123#271",
        "observationSortKey": "2026-10-01#1",
    }


@pytest.mark.parametrize("page_size", ["0", "1001", "not-a-number"])
def test_history_rejects_invalid_page_size(page_size: str) -> None:
    with pytest.raises(ApiValidationError):
        service(
            FakeTable(scan_pages=[{"Items": [product()]}]), FakeTable()
        ).history("123", "271", page_size=page_size)


def test_history_rejects_malformed_and_mismatched_tokens() -> None:
    products = FakeTable(scan_pages=[{"Items": [product()]}])
    with pytest.raises(ApiValidationError):
        service(products, FakeTable()).history(
            "123", "271", continuation_token="not-a-token"
        )

    observations = FakeTable(
        query_pages=[
            {
                "Items": [observation("1", "2026-10-20", "1.20")],
                "LastEvaluatedKey": {"sourceObservationId": "1"},
            }
        ]
    )
    token = service(
        FakeTable(scan_pages=[{"Items": [product()]}]), observations
    ).history("123", "271", page_size="10")["continuationToken"]
    with pytest.raises(ApiValidationError):
        service(
            FakeTable(scan_pages=[{"Items": [product()]}]), FakeTable()
        ).history("123", "271", page_size="20", continuation_token=token)


@pytest.mark.parametrize(
    "key_update",
    [
        {"unexpected": "value"},
        {"productStoreKey": "999#271"},
        {"sourceObservationId": 123},
        {"observationSortKey": "not-a-sort-key"},
    ],
)
def test_history_rejects_tampered_token_keys(key_update: dict[str, Any]) -> None:
    observations = FakeTable(
        query_pages=[
            {
                "Items": [observation("1", "2026-10-20", "1.20")],
                "LastEvaluatedKey": {
                    "sourceObservationId": "1",
                    "productStoreKey": "123#271",
                    "observationSortKey": "2026-10-20#1",
                },
            }
        ]
    )
    service_instance = service(
        FakeTable(scan_pages=[{"Items": [product()]}]), observations
    )
    token = service_instance.history("123", "271", page_size="10")[
        "continuationToken"
    ]
    padded = token + "=" * (-len(token) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    payload["lastEvaluatedKey"].update(key_update)
    tampered = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    with pytest.raises(ApiValidationError):
        service(
            FakeTable(scan_pages=[{"Items": [product()]}]), FakeTable()
        ).history("123", "271", continuation_token=tampered)


def test_history_rejects_oversized_token() -> None:
    with pytest.raises(ApiValidationError):
        service(
            FakeTable(scan_pages=[{"Items": [product()]}]), FakeTable()
        ).history("123", "271", continuation_token="a" * 4097)


def test_empty_history_returns_null_statistics() -> None:
    result = service(
        FakeTable(scan_pages=[{"Items": [product()]}]), FakeTable()
    ).history("123", "271")

    assert result["observations"] == []
    assert result["statistics"]["latestPrice"] is None
    assert result["statistics"]["observationCount"] == 0


@pytest.mark.parametrize(
    ("barcode", "store_id", "period", "error"),
    [
        ("bad", "271", "90d", ApiValidationError),
        ("123", None, "90d", ApiValidationError),
        ("123", "999", "90d", ApiValidationError),
        ("123", "271", "7d", ApiValidationError),
        ("999", "271", "90d", NotFoundError),
    ],
)
def test_invalid_inputs_are_rejected(
    barcode: str, store_id: str | None, period: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        service(
            FakeTable(scan_pages=[{"Items": [product()]}]), FakeTable()
        ).history(barcode, store_id, period)


def test_comparison_queries_each_store_and_omits_missing_data() -> None:
    observations = FakeTable(
        query_pages=[
            {"Items": [observation("1", "2026-10-20", "1.20")]},
            {"Items": []},
            {"Items": [observation("3", "2026-10-18", "3.40", "5395")]},
            {"Items": []},
            {"Items": []},
        ]
    )

    result = service(
        FakeTable(scan_pages=[{"Items": [product()]}]), observations
    ).comparison("123")

    assert [item["price"] for item in result["stores"]] == ["1.20", "3.40"]
    assert len(observations.query_calls) == 5
    assert all(call["Limit"] == 1 for call in observations.query_calls)
    assert all(call["IndexName"] == HISTORY_INDEX_NAME for call in observations.query_calls)
    assert all(call["ScanIndexForward"] is False for call in observations.query_calls)
    assert [
        call["KeyConditionExpression"].get_expression()["values"][1]
        for call in observations.query_calls
    ] == [f"123#{store['id']}" for store in load_curated_catalog().stores]
    for call in observations.query_calls:
        condition = call["KeyConditionExpression"].get_expression()
        assert condition["operator"] == "="
        assert condition["values"][0].name == "productStoreKey"
        assert condition["values"][1].startswith("123#")


def test_handler_returns_consistent_validation_and_success_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    products = FakeTable(scan_pages=[{"Items": [product()]}])
    observations = FakeTable()
    monkeypatch.setenv("PRODUCTS_TABLE", "Products")
    monkeypatch.setenv("DYNAMODB_TABLE", "PriceObservations")
    monkeypatch.setattr(
        "backend.api.lambda_handler.get_table",
        lambda name, region: products if name == "Products" else observations,
    )

    event = {
        "rawPath": "/products/123/history",
        "requestContext": {"http": {"method": "GET"}},
        "pathParameters": {"barcode": "123"},
        "queryStringParameters": {"storeId": "271", "period": "7d"},
    }
    response = handler(event, None)
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "INVALID_REQUEST"


def test_handler_rejects_unrelated_suffix_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.api.lambda_handler.get_table",
        lambda name, region: FakeTable(),
    )
    response = handler(
        {
            "rawPath": "/unrelated/history",
            "requestContext": {"http": {"method": "GET"}},
            "pathParameters": {"barcode": "123"},
        },
        None,
    )
    assert response["statusCode"] == 404
