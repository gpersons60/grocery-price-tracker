from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from backend.ingestion.import_data import (
    ProductCounts,
    import_data,
    save_products,
)
from backend.ingestion.price_storage import StorageCounts
from backend.ingestion.process_prices import NormalizedObservation


class FakeProductTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, str]] = {}
        self.calls: list[dict[str, Any]] = []

    def put_item(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)
        item = kwargs["Item"]
        if item["barcode"] in self.items:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException"}},
                "PutItem",
            )
        self.items[item["barcode"]] = item


def test_save_products_is_idempotent_and_preserves_existing_values() -> None:
    table = FakeProductTable()
    products = [{"barcode": "123", "name": "Original"}]

    assert save_products(table, products) == ProductCounts(inserted=1)
    assert save_products(table, [{"barcode": "123", "name": "Changed"}]) == (
        ProductCounts(skipped=1)
    )
    assert table.items["123"]["name"] == "Original"
    assert table.calls[0]["ConditionExpression"] == "attribute_not_exists(barcode)"


def test_save_products_propagates_unexpected_dynamodb_errors() -> None:
    class FailingTable:
        def put_item(self, **kwargs: Any) -> None:
            raise ClientError(
                {"Error": {"Code": "InternalServerError"}},
                "PutItem",
            )

    with pytest.raises(ClientError, match="InternalServerError"):
        save_products(FailingTable(), [{"barcode": "123", "name": "Product"}])


def test_dry_run_does_not_create_session_or_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = type(
        "Catalog",
        (),
        {
            "products": ({"barcode": "123", "name": "Product"},),
            "stores": (),
            "market": {},
        },
    )()
    observations = (
        NormalizedObservation(
            sourceObservationId="1",
            barcode="123",
            storeId="1",
            observedDate="2026-01-01",
            price=Decimal("1.25"),
            currency="EUR",
            sourceUpdated=None,
        ),
    )

    def fail_session(**kwargs: Any) -> None:
        raise AssertionError("dry run must not create a Boto3 session")

    monkeypatch.setattr("backend.ingestion.import_data.boto3.Session", fail_session)
    monkeypatch.setattr(
        "backend.ingestion.import_data.iter_normalized_observations",
        lambda path, supplied_catalog: iter(observations),
    )

    assert (
        import_data(
            Path("unused.parquet"),
            profile="grocery-tracker",
            region="us-east-2",
            products_table_name="Products",
            observations_table_name="PriceObservations",
            apply=False,
            catalog=catalog,
        )
        is None
    )
    assert "1 products and 1 price observations" in capsys.readouterr().out


def test_apply_uses_catalogue_and_persistence_counts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    product_table = FakeProductTable()
    observation_table = object()

    class FakeResource:
        def Table(self, name: str) -> Any:
            return {"Products": product_table, "PriceObservations": observation_table}[name]

    class FakeSession:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs == {"profile_name": "grocery-tracker", "region_name": "us-east-2"}

        def resource(self, name: str) -> FakeResource:
            assert name == "dynamodb"
            return FakeResource()

    catalog = type(
        "Catalog",
        (),
        {
            "products": ({"barcode": "123", "name": "Product"},),
            "stores": (),
            "market": {},
        },
    )()
    monkeypatch.setattr("backend.ingestion.import_data.boto3.Session", FakeSession)
    monkeypatch.setattr(
        "backend.ingestion.import_data.iter_normalized_observations",
        lambda path, supplied_catalog: iter(()),
    )
    monkeypatch.setattr(
        "backend.ingestion.import_data.save_observations",
        lambda table, observations: StorageCounts(skipped=2),
    )

    result = import_data(
        Path("unused.parquet"),
        profile="grocery-tracker",
        region="us-east-2",
        products_table_name="Products",
        observations_table_name="PriceObservations",
        apply=True,
        catalog=catalog,
    )

    assert result == (ProductCounts(inserted=1), StorageCounts(skipped=2))
    output = capsys.readouterr().out
    assert "Products: inserted=1, updated=0, skipped=0" in output
    assert "Price observations: inserted=0, updated=0, skipped=2" in output
