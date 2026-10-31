"""Explore Nancy, France Open Prices observations from a local Parquet file."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import pyarrow as pa
import pyarrow.parquet as pq


FIELD_ALIASES = {
    "country_code": ("location_osm_address_country_code", "country_code"),
    "city": ("location_osm_address_city", "city"),
    "type": ("type",),
    "currency": ("currency",),
    "barcode": ("product_code", "barcode"),
    "store_id": ("location_id", "physical_location_id"),
    "store_name": (
        "location_osm_display_name",
        "location_name",
        "physical_location_name",
    ),
    "price": ("price",),
    "price_per": ("price_per",),
    "observation_date": ("date", "observation_date"),
    "product_name": ("product_name",),
}


@dataclass
class ProductSummary:
    observations: int = 0
    dates: set[date] = field(default_factory=set)
    stores: dict[str, "StoreSummary"] = field(default_factory=dict)
    names: set[str] = field(default_factory=set)


@dataclass
class StoreSummary:
    observations: int = 0
    dates: set[date] = field(default_factory=set)
    display_names: set[str] = field(default_factory=set)


@dataclass
class AnalysisResult:
    observations: int
    products: dict[str, ProductSummary]
    stores: dict[str, set[str]]
    missing_product_names: int
    missing_price_per: int
    earliest_date: date | None
    latest_date: date | None

    @property
    def candidate_products(self) -> dict[str, ProductSummary]:
        return {
            barcode: summary
            for barcode, summary in self.products.items()
            if len(summary.stores) >= 2
        }

    @property
    def suitable_products(self) -> dict[str, ProductSummary]:
        return {
            barcode: summary
            for barcode, summary in self.candidate_products.items()
            if any(len(store.dates) >= 3 for store in summary.stores.values())
        }


def _column_map(schema: pa.Schema) -> dict[str, str]:
    available = set(schema.names)
    selected: dict[str, str] = {}
    for logical_name, aliases in FIELD_ALIASES.items():
        match = next((alias for alias in aliases if alias in available), None)
        if match is not None:
            selected[logical_name] = match
    required = (
        "country_code",
        "city",
        "type",
        "currency",
        "barcode",
        "store_id",
        "price",
        "observation_date",
    )
    missing = [name for name in required if name not in selected]
    if missing:
        raise ValueError(f"Parquet file is missing required columns: {', '.join(missing)}")
    return selected


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _valid_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _positive_price(value: Any) -> bool:
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def analyze_nancy(path: Path, batch_size: int = 65_536) -> AnalysisResult:
    """Analyze eligible Nancy observations without eagerly loading the dataset."""
    parquet_file = pq.ParquetFile(path)
    columns = _column_map(parquet_file.schema_arrow)
    selected_columns = list(columns.values())
    products: dict[str, ProductSummary] = {}
    stores: dict[str, set[str]] = defaultdict(set)
    missing_product_names = 0
    missing_price_per = 0
    earliest_date: date | None = None
    latest_date: date | None = None

    for batch in parquet_file.iter_batches(
        batch_size=batch_size, columns=selected_columns
    ):
        for row in batch.to_pylist():
            get = lambda logical: row.get(columns[logical])
            if _text(get("country_code")).upper() != "FR":
                continue
            if _text(get("city")).casefold() != "nancy":
                continue
            if _text(get("type")).upper() != "PRODUCT":
                continue
            if _text(get("currency")).upper() != "EUR":
                continue
            barcode = _text(get("barcode"))
            store_id = _text(get("store_id"))
            observed_date = _valid_date(get("observation_date"))
            if not barcode or not store_id or observed_date is None:
                continue
            if not _positive_price(get("price")):
                continue

            summary = products.setdefault(barcode, ProductSummary())
            summary.observations += 1
            summary.dates.add(observed_date)
            store_summary = summary.stores.setdefault(store_id, StoreSummary())
            store_summary.observations += 1
            store_summary.dates.add(observed_date)
            product_name = _text(get("product_name")) if "product_name" in columns else ""
            if product_name:
                summary.names.add(product_name)
            store_name = _text(get("store_name")) if "store_name" in columns else ""
            stores[store_id]
            if store_name:
                stores[store_id].add(store_name)
            if earliest_date is None or observed_date < earliest_date:
                earliest_date = observed_date
            if latest_date is None or observed_date > latest_date:
                latest_date = observed_date
            if not product_name:
                missing_product_names += 1
            if "price_per" not in columns or get("price_per") is None or not _text(get("price_per")):
                missing_price_per += 1

    return AnalysisResult(
        observations=sum(summary.observations for summary in products.values()),
        products=products,
        stores=dict(stores),
        missing_product_names=missing_product_names,
        missing_price_per=missing_price_per,
        earliest_date=earliest_date,
        latest_date=latest_date,
    )


def _format_date(value: date | None) -> str:
    return value.isoformat() if value else "none"


def _shortlist(result: AnalysisResult) -> Iterable[tuple[str, ProductSummary]]:
    reference = result.latest_date or date.min
    return sorted(
        result.suitable_products.items(),
        key=lambda item: (
            -max(len(store.dates) for store in item[1].stores.values()),
            -sum(len(store.dates) for store in item[1].stores.values()),
            -len(item[1].stores),
            -item[1].observations,
            (reference - max(item[1].dates)).days if item[1].dates else 10**9,
            item[0],
        ),
    )[:20]


def print_report(result: AnalysisResult) -> None:
    print(f"Matching observations: {result.observations}")
    print(f"Distinct products: {len(result.products)}")
    print(f"Distinct physical stores: {len(result.stores)}")
    print("Stores:")
    for store_id in sorted(result.stores):
        names = ", ".join(sorted(result.stores[store_id])) or "(name unavailable)"
        print(f"  {store_id}: {names}")
    print(f"Earliest observation date: {_format_date(result.earliest_date)}")
    print(f"Latest observation date: {_format_date(result.latest_date)}")
    print(f"Missing product names: {result.missing_product_names}")
    print(
        f"Missing price_per values: {result.missing_price_per} "
        f"of {result.observations} matching observations"
    )
    print(f"Shortlist recency reference date: {_format_date(result.latest_date)}")
    print(
        f"Products with at least two stores and three dates at one store: "
        f"{len(result.suitable_products)}"
    )
    print("Suitable candidate barcodes:")
    for barcode, summary in _shortlist(result):
        names = ", ".join(sorted(summary.names)) or "(name unavailable)"
        store_counts = ", ".join(
            f"{store_id}={store.observations} observations/"
            f"{len(store.dates)} dates"
            for store_id, store in sorted(summary.stores.items())
        )
        earliest = min(
            date_value for store in summary.stores.values() for date_value in store.dates
        )
        latest = max(
            date_value for store in summary.stores.values() for date_value in store.dates
        )
        print(
            f"  {barcode}: observations={summary.observations}, "
            f"dates={len(summary.dates)}, stores={len(summary.stores)}, "
            f"earliest={earliest.isoformat()}, latest={latest.isoformat()} "
            f"({store_counts}), names={names}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Nancy, France Open Prices observations in a local Parquet file."
    )
    parser.add_argument("path", type=Path, help="path to a local Parquet file")
    args = parser.parse_args(argv)
    try:
        print_report(analyze_nancy(args.path))
    except FileNotFoundError:
        print(f"Error: Parquet file not found: {args.path}", file=sys.stderr)
        return 1
    except (OSError, pa.ArrowException, ValueError) as error:
        print(f"Error: unable to analyze Parquet file '{args.path}': {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
