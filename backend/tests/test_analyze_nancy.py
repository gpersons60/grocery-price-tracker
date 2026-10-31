from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from backend.ingestion.analyze_nancy import analyze_nancy, main


def write_observations(path: Path) -> None:
    pq.write_table(
        pa.table(
            {
                "location_osm_address_country_code": ["FR", "fr", "FR", "FR", "FR", "DE", "FR", "FR", "FR", "FR"],
                "location_osm_address_city": ["Nancy", "NANCY", "Nancy", "Nancy", "Nancy", "Nancy", "Metz", "Nancy", "Nancy", "Nancy"],
                "type": ["PRODUCT", "product", "PRODUCT", "PRODUCT", "PRODUCT", "PRODUCT", "PRODUCT", "PRODUCT", "PRODUCT", "PRODUCT"],
                "currency": ["EUR", "eur", "EUR", "EUR", "EUR", "EUR", "EUR", "USD", "EUR", "EUR"],
                "product_code": ["0001", "0001", "0001", "0002", "0003", "0001", "0001", "0001", "0004", "0001"],
                "location_id": ["store-a", "store-b", "store-a", "store-a", "store-a", "store-c", "store-d", "store-a", "store-a", "store-a"],
                "location_osm_display_name": ["Real A", "Real B", "Real A", "Real A", "Real A", "Real C", "Real D", None, "Real A", "Real A"],
                "location_name": ["A", "B", "A", "A", "A", "C", "D", "A", "A", "A"],
                "price": [2.50, 2.75, 2.40, 0, 3.10, 2.50, 2.50, 2.50, 1.20, 2.30],
                "price_per": ["kg", None, "kg", "kg", None, "kg", "kg", "kg", "kg", "kg"],
                "date": ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-20", "2026-10-20", "2026-10-20", "2026-10-20", "2026-10-20", "invalid", "2026-10-23"],
                "product_name": ["Milk", "Milk", "Milk", "Bread", None, "Milk", "Milk", "Milk", "Juice", "Milk"],
                "unrelated_column": list(range(10)),
            }
        ),
        path,
    )


def test_analysis_filters_and_aggregates_without_optional_values(tmp_path: Path) -> None:
    parquet_path = tmp_path / "prices.parquet"
    write_observations(parquet_path)

    result = analyze_nancy(parquet_path)

    assert result.observations == 5
    assert set(result.products) == {"0001", "0003"}
    assert result.stores == {"store-a": {"Real A"}, "store-b": {"Real B"}}
    assert result.products["0001"].observations == 4
    assert result.products["0001"].dates == {
        date(2026, 10, 20),
        date(2026, 10, 21),
        date(2026, 10, 22),
        date(2026, 10, 23),
    }
    assert result.products["0001"].stores["store-a"].observations == 3
    assert len(result.products["0001"].stores["store-a"].dates) == 3
    assert result.products["0001"].stores["store-b"].observations == 1
    assert len(result.suitable_products) == 1
    assert result.missing_product_names == 1
    assert result.missing_price_per == 2
    assert result.earliest_date.isoformat() == "2026-10-20"
    assert result.latest_date.isoformat() == "2026-10-23"


def test_cli_reports_shortlist_and_missing_values(tmp_path: Path, capsys) -> None:
    parquet_path = tmp_path / "prices.parquet"
    write_observations(parquet_path)

    assert main([str(parquet_path)]) == 0

    output = capsys.readouterr().out
    assert "Matching observations: 5" in output
    assert "Shortlist recency reference date: 2026-10-23" in output
    assert "Products with at least two stores and three dates at one store: 1" in output
    assert "0001: observations=4, dates=4, stores=2" in output
    assert "earliest=2026-10-20, latest=2026-10-23" in output
    assert "store-a=3 observations/3 dates" in output
    assert "store-b=1 observations/1 dates" in output


def test_analysis_rejects_missing_required_columns(tmp_path: Path) -> None:
    parquet_path = tmp_path / "incomplete.parquet"
    pq.write_table(pa.table({"price": [1]}), parquet_path)

    assert main([str(parquet_path)]) == 1


def test_valid_observation_with_missing_store_name_is_counted_and_reported(
    tmp_path: Path, capsys
) -> None:
    parquet_path = tmp_path / "unnamed-store.parquet"
    pq.write_table(
        pa.table(
            {
                "location_osm_address_country_code": ["FR"],
                "location_osm_address_city": ["Nancy"],
                "type": ["PRODUCT"],
                "currency": ["EUR"],
                "product_code": ["0009"],
                "location_id": ["store-without-name"],
                "location_osm_display_name": [None],
                "price": [1.50],
                "date": ["2026-10-24"],
            }
        ),
        parquet_path,
    )

    result = analyze_nancy(parquet_path)
    assert result.stores == {"store-without-name": set()}

    assert main([str(parquet_path)]) == 0
    assert "store-without-name: (name unavailable)" in capsys.readouterr().out
