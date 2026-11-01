"""Load the version-controlled catalogue used to scope future ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).with_name("curated_catalog.json")


@dataclass(frozen=True)
class CuratedCatalog:
    market: dict[str, str]
    products: tuple[dict[str, str], ...]
    stores: tuple[dict[str, str], ...]


def load_curated_catalog(path: Path = CATALOG_PATH) -> CuratedCatalog:
    """Load and return the curated market, products, and physical stores."""
    with path.open(encoding="utf-8") as catalog_file:
        data: Any = json.load(catalog_file)

    return CuratedCatalog(
        market=data["market"],
        products=tuple(data["products"]),
        stores=tuple(data["stores"]),
    )
