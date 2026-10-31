from __future__ import annotations

from backend.ingestion.curated_catalog import load_curated_catalog


def test_curated_catalog_has_expected_market_and_sizes() -> None:
    catalog = load_curated_catalog()

    assert catalog.market == {
        "city": "Nancy",
        "country_code": "FR",
        "currency": "EUR",
    }
    assert len(catalog.products) == 17
    assert len(catalog.stores) == 5


def test_curated_catalog_has_unique_string_identifiers() -> None:
    catalog = load_curated_catalog()

    barcodes = [product["barcode"] for product in catalog.products]
    store_ids = [store["id"] for store in catalog.stores]

    assert all(isinstance(barcode, str) for barcode in barcodes)
    assert all(isinstance(store_id, str) for store_id in store_ids)
    assert len(barcodes) == len(set(barcodes))
    assert len(store_ids) == len(set(store_ids))
