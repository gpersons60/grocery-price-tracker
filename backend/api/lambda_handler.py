"""AWS API Gateway HTTP API (payload format 2.0) Lambda handler."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .data_access import get_table
from .service import ApiService, ApiValidationError, NotFoundError

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    try:
        path = event.get("rawPath", "")
        method = event.get("requestContext", {}).get("http", {}).get("method")
        parameters = event.get("pathParameters") or {}
        query = event.get("queryStringParameters") or {}

        route = None
        if method == "GET" and path == "/products":
            route = "products"
        elif method == "GET" and path == "/stores":
            route = "stores"
        elif (
            method == "GET"
            and parameters.get("barcode")
            and path == f"/products/{parameters['barcode']}/history"
        ):
            route = "history"
        elif (
            method == "GET"
            and parameters.get("barcode")
            and path == f"/products/{parameters['barcode']}/comparison"
        ):
            route = "comparison"
        else:
            return _response(404, {"error": {"code": "NOT_FOUND", "message": "route not found"}})

        service = ApiService(
            get_table(os.environ["PRODUCTS_TABLE"], os.environ.get("AWS_REGION")),
            get_table(os.environ["DYNAMODB_TABLE"], os.environ.get("AWS_REGION")),
        )
        if route == "products":
            result = service.products()
        elif route == "stores":
            result = service.stores()
        elif route == "history":
            result = service.history(
                parameters.get("barcode", ""),
                query.get("storeId"),
                query.get("period", "90d"),
                query.get("pageSize"),
                query.get("continuationToken"),
            )
        else:
            result = service.comparison(parameters.get("barcode", ""))
        return _response(200, {"data": result})
    except ApiValidationError as error:
        return _response(400, {"error": {"code": "INVALID_REQUEST", "message": str(error)}})
    except NotFoundError as error:
        return _response(404, {"error": {"code": "NOT_FOUND", "message": str(error)}})
    except Exception:
        LOGGER.exception("API request failed")
        return _response(500, {"error": {"code": "INTERNAL_ERROR", "message": "internal server error"}})


lambda_handler = handler
