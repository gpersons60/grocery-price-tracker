"""Filter and normalize Open Prices observations for the curated catalogue."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from backend.ingestion.curated_catalog import CuratedCatalog, load_curated_catalog


FIELD_ALIASES = {
    "source_observation_id": ("id", "source_observation_id", "sourceObservationId"),
    "country_code": ("location_osm_address_country_code", "country_code"),
    "city": ("location_osm_address_city", "city"),
    "type": ("type",),
    "currency": ("currency",),
    "barcode": ("product_code", "barcode"),
    "store_id": ("location_id", "physical_location_id", "store_id"),
    "price": ("price",),
    "observation_date": ("date", "observation_date", "observed_date"),
    "source_updated": ("updated", "source_updated", "sourceUpdated"),
}


@dataclass(frozen=True)
class NormalizedObservation:
    """A validated observation ready for a later persistence stage."""

    sourceObservationId: str
    barcode: str
    storeId: str
    observedDate: str
    price: Decimal
    currency: str
    sourceUpdated: str | None


@dataclass(frozen=True)
class IngestionSummary:
    """Counts from one bounded-memory Parquet transformation."""

    examined: int
    accepted: int
    rejected: int
    rejection_reasons: dict[str, int]


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
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _positive_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not decimal_value.is_finite() or decimal_value <= 0:
        return None
    return decimal_value


def _utc_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        timestamp = value
    else:
        text = _text(value)
        if not text:
            return None
        try:
            timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _catalog_sets(catalog: CuratedCatalog) -> tuple[set[str], set[str]]:
    return (
        {product["barcode"] for product in catalog.products},
        {store["id"] for store in catalog.stores},
    )


def _source_observation_id(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value) if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        return text if text.isdigit() and int(text) > 0 else None
    return None


def validate_and_normalize(
    row: Mapping[str, Any],
    catalog: CuratedCatalog | None = None,
    catalog_sets: tuple[set[str], set[str]] | None = None,
) -> tuple[NormalizedObservation | None, str | None]:
    """Validate one source row and return its normalized form or a reason."""
    catalog = catalog or load_curated_catalog()
    product_barcodes, store_ids = catalog_sets or _catalog_sets(catalog)
    values = {
        logical: next(
            (row[source] for source in (logical, *aliases) if source in row),
            None,
        )
        for logical, aliases in FIELD_ALIASES.items()
    }

    if _text(values.get("country_code")).upper() != catalog.market["country_code"].upper():
        return None, "country"
    if _text(values.get("city")).casefold() != catalog.market["city"].casefold():
        return None, "city"
    if _text(values.get("currency")).upper() != catalog.market["currency"].upper():
        return None, "currency"
    if _text(values.get("type")).upper() != "PRODUCT":
        return None, "type"

    source_id = _source_observation_id(values.get("source_observation_id"))
    if not source_id:
        return None, "source_observation_id"
    barcode = _text(values.get("barcode"))
    if not barcode:
        return None, "barcode"
    if barcode not in product_barcodes:
        return None, "product"
    store_id = _text(values.get("store_id"))
    if not store_id:
        return None, "store_id"
    if store_id not in store_ids:
        return None, "store"

    price = _positive_decimal(values.get("price"))
    if price is None:
        return None, "price"
    observed_date = _valid_date(values.get("observation_date"))
    if observed_date is None:
        return None, "observation_date"

    return (
        NormalizedObservation(
            sourceObservationId=source_id,
            barcode=barcode,
            storeId=store_id,
            observedDate=observed_date.isoformat(),
            price=price,
            currency=catalog.market["currency"].upper(),
            sourceUpdated=_utc_timestamp(values.get("source_updated")),
        ),
        None,
    )


def _column_map(schema: pa.Schema) -> dict[str, str]:
    available = set(schema.names)
    selected: dict[str, str] = {}
    for logical_name, aliases in FIELD_ALIASES.items():
        match = next((alias for alias in aliases if alias in available), None)
        if match is not None:
            selected[logical_name] = match
    required = (
        "source_observation_id",
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


def iter_normalized_observations(
    path: Path,
    catalog: CuratedCatalog | None = None,
    batch_size: int = 65_536,
) -> Iterator[NormalizedObservation]:
    """Yield accepted rows from *path* while reading at most one batch at a time."""
    catalog = catalog or load_curated_catalog()
    parquet_file = pq.ParquetFile(path)
    columns = _column_map(parquet_file.schema_arrow)
    catalog_sets = _catalog_sets(catalog)
    selected_columns = list(columns.values())
    for batch in parquet_file.iter_batches(batch_size=batch_size, columns=selected_columns):
        for row in batch.to_pylist():
            source_row = {logical: row.get(source) for logical, source in columns.items()}
            observation, _ = validate_and_normalize(source_row, catalog, catalog_sets)
            if observation is not None:
                yield observation


def summarize_parquet(
    path: Path,
    catalog: CuratedCatalog | None = None,
    batch_size: int = 65_536,
) -> IngestionSummary:
    """Transform a Parquet file and report counts without retaining observations."""
    catalog = catalog or load_curated_catalog()
    parquet_file = pq.ParquetFile(path)
    columns = _column_map(parquet_file.schema_arrow)
    catalog_sets = _catalog_sets(catalog)
    rejection_reasons: Counter[str] = Counter()
    examined = accepted = 0
    for batch in parquet_file.iter_batches(batch_size=batch_size, columns=list(columns.values())):
        for row in batch.to_pylist():
            examined += 1
            source_row = {logical: row.get(source) for logical, source in columns.items()}
            observation, reason = validate_and_normalize(source_row, catalog, catalog_sets)
            if observation is None:
                rejection_reasons[reason or "invalid"] += 1
            else:
                accepted += 1
    return IngestionSummary(
        examined=examined,
        accepted=accepted,
        rejected=examined - accepted,
        rejection_reasons=dict(rejection_reasons),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local transformation summary command."""
    parser = argparse.ArgumentParser(
        description="Filter and normalize Open Prices observations from Parquet."
    )
    parser.add_argument("path", type=Path, help="path to a local Parquet file")
    parser.add_argument("--batch-size", type=int, default=65_536)
    args = parser.parse_args(argv)
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    try:
        summary = summarize_parquet(args.path, batch_size=args.batch_size)
    except FileNotFoundError:
        print(f"Error: Parquet file not found: {args.path}", file=sys.stderr)
        return 1
    except (OSError, pa.ArrowException, ValueError) as error:
        print(f"Error: unable to process Parquet file '{args.path}': {error}", file=sys.stderr)
        return 1

    print(f"Examined: {summary.examined}")
    print(f"Accepted: {summary.accepted}")
    print(f"Rejected: {summary.rejected}")
    if summary.rejection_reasons:
        reasons = ", ".join(
            f"{reason}={count}" for reason, count in sorted(summary.rejection_reasons.items())
        )
        print(f"Rejection reasons: {reasons}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
