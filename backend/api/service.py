"""Application services for the public read-only API."""

from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable

from backend.ingestion.curated_catalog import CuratedCatalog, load_curated_catalog

from . import data_access

PERIOD_DAYS = {"30d": 30, "90d": 90, "1y": 365, "all": None}
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
MAX_CONTINUATION_TOKEN_LENGTH = 4096
_SORT_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}#.+$")


class ApiValidationError(ValueError):
    """An invalid public API parameter."""


class NotFoundError(LookupError):
    """A valid resource that is not in the curated catalogue."""


def _price(value: Any) -> str:
    """Serialize DynamoDB Decimal values without converting through float."""
    return str(value if isinstance(value, Decimal) else Decimal(str(value)))


class ApiService:
    def __init__(
        self,
        products_table: data_access.Table,
        observations_table: data_access.Table,
        *,
        catalog: CuratedCatalog | None = None,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.products_table = products_table
        self.observations_table = observations_table
        self.catalog = catalog or load_curated_catalog()
        self.today = today

    def products(self) -> list[dict[str, str]]:
        records = data_access.scan_all(self.products_table)
        return sorted(
            [
                {"barcode": str(item["barcode"]), "name": str(item["name"])}
                for item in records
                if item.get("barcode") and item.get("name")
            ],
            key=lambda item: item["barcode"],
        )

    def stores(self) -> list[dict[str, str]]:
        return [dict(store) for store in self.catalog.stores]

    def history(
        self,
        barcode: str,
        store_id: str | None,
        period: str = "90d",
        page_size: str | None = None,
        continuation_token: str | None = None,
    ) -> dict[str, Any]:
        self._require_product(barcode)
        store = self._require_store(store_id)
        if period not in PERIOD_DAYS:
            raise ApiValidationError("period must be one of 30d, 90d, 1y, all")
        requested_page_size = self._page_size(page_size)

        start_key = end_key = None
        if PERIOD_DAYS[period] is not None:
            start = self.today() - timedelta(days=PERIOD_DAYS[period])
            end = self.today()
            start_key = f"{start.isoformat()}#"
            end_key = f"{end.isoformat()}#\uffff"

        context = {
            "barcode": barcode,
            "storeId": store["id"],
            "period": period,
            "startSortKey": start_key,
            "endSortKey": end_key,
            "pageSize": requested_page_size,
        }
        exclusive_start_key = self._decode_token(continuation_token, context)
        records, last_evaluated_key = data_access.query_history(
            self.observations_table,
            product_store_key=f"{barcode}#{store['id']}",
            start_sort_key=start_key,
            end_sort_key=end_key,
            page_size=requested_page_size,
            exclusive_start_key=exclusive_start_key,
        )
        observations = [self._observation(record, store) for record in records]
        prices = [Decimal(item["price"]) for item in observations]
        stats = {
            "latestPrice": observations[-1]["price"] if observations else None,
            "minimumPrice": _price(min(prices)) if prices else None,
            "maximumPrice": _price(max(prices)) if prices else None,
            "meanPrice": _price(sum(prices, Decimal("0")) / len(prices))
            if prices
            else None,
            "observationCount": len(observations),
        }
        response: dict[str, Any] = {
            "barcode": barcode,
            "store": store,
            "period": period,
            "observations": observations,
            "statistics": stats,
        }
        if last_evaluated_key:
            response["continuationToken"] = self._encode_token(
                context, last_evaluated_key
            )
        return response

    def comparison(self, barcode: str) -> dict[str, Any]:
        product = self._require_product(barcode)
        stores: list[dict[str, Any]] = []
        for store in self.catalog.stores:
            record = data_access.query_latest(
                self.observations_table,
                product_store_key=f"{barcode}#{store['id']}",
            )
            if record:
                stores.append(self._observation(record, store))
        return {
            "barcode": barcode,
            "productName": product["name"],
            "stores": stores,
        }

    def _require_product(self, barcode: str) -> dict[str, str]:
        if not barcode or not barcode.isdigit():
            raise ApiValidationError("barcode must contain only digits")
        for product in self.products():
            if product["barcode"] == barcode:
                return product
        raise NotFoundError("product not found")

    def _require_store(self, store_id: str | None) -> dict[str, str]:
        if not store_id:
            raise ApiValidationError("storeId query parameter is required")
        if not store_id.isdigit():
            raise ApiValidationError("storeId must contain only digits")
        for store in self.catalog.stores:
            if store["id"] == store_id:
                return dict(store)
        raise ApiValidationError("storeId is not supported")

    @staticmethod
    def _observation(
        record: dict[str, Any], store: dict[str, str]
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "store": store,
            "sourceObservationId": str(record["sourceObservationId"]),
            "observedDate": str(record["observedDate"]),
            "price": _price(record["price"]),
            "currency": str(record.get("currency", "EUR")),
        }
        if record.get("sourceUpdatedAt") is not None:
            result["sourceUpdatedAt"] = str(record["sourceUpdatedAt"])
        return result

    @staticmethod
    def _page_size(value: str | None) -> int:
        if value is None:
            return DEFAULT_PAGE_SIZE
        try:
            page_size = int(value)
        except ValueError as error:
            raise ApiValidationError("pageSize must be an integer") from error
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise ApiValidationError(
                f"pageSize must be between 1 and {MAX_PAGE_SIZE}"
            )
        return page_size

    @staticmethod
    def _encode_token(
        context: dict[str, Any], last_evaluated_key: dict[str, Any]
    ) -> str:
        payload = {"context": context, "lastEvaluatedKey": last_evaluated_key}
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(encoded).decode().rstrip("=")

    @staticmethod
    def _decode_token(
        token: str | None, expected_context: dict[str, Any]
    ) -> dict[str, Any] | None:
        if token is None:
            return None
        if (
            not token
            or len(token) > MAX_CONTINUATION_TOKEN_LENGTH
            or not re.fullmatch(r"[A-Za-z0-9_-]+", token)
        ):
            raise ApiValidationError("continuationToken is malformed")
        try:
            padded = token + "=" * (-len(token) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded).decode())
            if (
                not isinstance(payload, dict)
                or payload.get("context") != expected_context
            ):
                raise ApiValidationError(
                    "continuationToken does not match the requested history"
                )
            key = payload.get("lastEvaluatedKey")
            if not isinstance(key, dict):
                raise ValueError
            if set(key) != {
                "sourceObservationId",
                "productStoreKey",
                "observationSortKey",
            }:
                raise ValueError
            if not all(isinstance(value, str) for value in key.values()):
                raise ValueError
            if (
                not key["sourceObservationId"]
                or key["productStoreKey"] != (
                    f"{expected_context['barcode']}#{expected_context['storeId']}"
                )
                or not _SORT_KEY_PATTERN.fullmatch(key["observationSortKey"])
                or not key["observationSortKey"].endswith(
                    f"#{key['sourceObservationId']}"
                )
            ):
                raise ValueError
            return key
        except (
            ValueError,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            binascii.Error,
        ) as error:
            if isinstance(error, ApiValidationError):
                raise
            raise ApiValidationError("continuationToken is malformed") from error
