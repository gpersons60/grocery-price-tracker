from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from backend.ingestion.curated_catalog import load_curated_catalog
from backend.ingestion.process_prices import (
    iter_normalized_observations,
    main,
    summarize_parquet,
    validate_and_normalize,
)


def row(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": 123,
        "location_osm_address_country_code": "FR",
        "location_osm_address_city": "Nancy",
        "type": "PRODUCT",
        "currency": "EUR",
        "product_code": "3256540000346",
        "location_id": 271,
        "price": Decimal("2.50"),
        "date": "2024-01-02",
        "updated": datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
        "product_name": None,
        "price_per": None,
    }
    value.update(overrides)
    return value


def test_valid_observation_is_normalized_precisely() -> None:
    observation, reason = validate_and_normalize(row())

    assert reason is None
    assert observation is not None
    assert observation.sourceObservationId == "123"
    assert observation.barcode == "3256540000346"
    assert observation.storeId == "271"
    assert observation.observedDate == "2024-01-02"
    assert observation.price == Decimal("2.50")
    assert observation.currency == "EUR"
    assert observation.sourceUpdated == "2026-10-31T12:00:00Z"


def test_catalogue_and_required_field_filtering() -> None:
    catalog = load_curated_catalog()
    for overrides, reason in (
        ({"product_code": "not-selected"}, "product"),
        ({"location_id": "not-selected"}, "store"),
        ({"id": None}, "source_observation_id"),
        ({"product_code": None}, "barcode"),
        ({"location_id": None}, "store_id"),
        ({"price": 0}, "price"),
        ({"price": "-1.0"}, "price"),
        ({"date": "not-a-date"}, "observation_date"),
    ):
        _, actual_reason = validate_and_normalize(row(**overrides), catalog)
        assert actual_reason == reason


def test_source_observation_id_must_be_a_positive_integer() -> None:
    for identifier in (None, 0, -1, True, 1.5, "1.5", "not-numeric", "0", "-1"):
        _, reason = validate_and_normalize(row(id=identifier))
        assert reason == "source_observation_id"

    observation, reason = validate_and_normalize(row(id=" 456 "))
    assert reason is None
    assert observation is not None
    assert observation.sourceObservationId == "456"


def test_date_strings_with_trailing_content_are_rejected() -> None:
    _, reason = validate_and_normalize(row(date="2026-10-27invalid"))

    assert reason == "observation_date"


def test_optional_fields_and_price_per_do_not_reject() -> None:
    observation, reason = validate_and_normalize(
        row(product_name=None, price_per=None, updated=None)
    )

    assert reason is None
    assert observation is not None
    assert observation.sourceUpdated is None


def test_timezone_aware_timestamp_string_is_normalized_as_utc() -> None:
    observation, reason = validate_and_normalize(
        row(updated="2026-10-31T14:00:00+02:00")
    )

    assert reason is None
    assert observation is not None
    assert observation.sourceUpdated == "2026-10-31T12:00:00Z"


def test_parquet_processing_reads_multiple_batches_and_reports_rejections(
    tmp_path: Path, capsys
) -> None:
    path = tmp_path / "prices.parquet"
    valid = row(id=1)
    rejected = row(id=2, product_code="not-selected")
    table = pa.Table.from_pylist([valid, rejected, row(id=3, price=Decimal("3.10"))])
    pq.write_table(table, path, row_group_size=1)

    observations = list(iter_normalized_observations(path, batch_size=1))
    assert [item.sourceObservationId for item in observations] == ["1", "3"]

    summary = summarize_parquet(path, batch_size=1)
    assert (summary.examined, summary.accepted, summary.rejected) == (3, 2, 1)
    assert summary.rejection_reasons == {"product": 1}

    assert main([str(path), "--batch-size", "1"]) == 0
    output = capsys.readouterr().out
    assert "Examined: 3" in output
    assert "Accepted: 2" in output
    assert "Rejected: 1" in output
