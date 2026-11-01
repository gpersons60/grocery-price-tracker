# grocery-price-tracker
Serverless grocery price comparison and historical price tracking application

## Manual initial data import

The importer defaults to a dry run. Review its counts first, then add `--apply`
to write the curated products and normalized observations to DynamoDB:

```powershell
.venv\Scripts\python.exe -m backend.ingestion.import_data data\raw\prices.parquet `
  --profile grocery-tracker --region us-east-2 `
  --products-table Products --observations-table PriceObservations --apply
```

The import is safe to rerun: existing products are skipped and observations use
the persistence layer's idempotent correction rules. The command does not delete
records or create tables.

## Lambda container image

The ingestion Lambda downloads the latest Open Prices Parquet export and reads
these required environment variables: `PRODUCTS_TABLE`, `DYNAMODB_TABLE`, and
`AWS_REGION`. Build the image for Lambda's x86_64 runtime from the repository
root:

```powershell
docker buildx build --platform linux/amd64 --provenance=false --load `
  -t grocery-ingestion .
```

Run the handler locally with Docker's Lambda runtime interface after supplying
the table and region environment variables:

```powershell
docker run --rm -p 9000:8080 `
  -e PRODUCTS_TABLE=Products -e DYNAMODB_TABLE=PriceObservations `
  -e AWS_REGION=us-east-2 grocery-ingestion
```

The local container invocation requires AWS credentials with permission to write
the configured tables; it is not a dry run.

## Read-only API

The API Lambda uses API Gateway HTTP API payload format 2.0 and reads the
`PRODUCTS_TABLE` and `DYNAMODB_TABLE` environment variables. It uses the
standard Boto3 credential chain and does not create or modify AWS resources.

All successful responses have the shape `{"data": ...}`. Errors have the shape
`{"error": {"code": "...", "message": "..."}}`.

| Method and path | Response |
| --- | --- |
| `GET /products` | Curated products with `barcode` and `name`. |
| `GET /stores` | Curated physical stores with `id`, `name`, and `address`. |
| `GET /products/{barcode}/history?storeId={id}&period=90d&pageSize=100&continuationToken=...` | Ordered observations and page-scoped statistics. `period` is `30d`, `90d`, `1y`, or `all`; `90d` is the default. `storeId` is required. `pageSize` defaults to 100 and is limited to 1000. |
| `GET /products/{barcode}/comparison` | The newest indexed observation for each curated store with data. |

Prices and statistics are JSON strings (for example `"1.230"`) so decimal
values are not converted through binary floating point. Each observation
includes its observed date, source observation ID, and source update timestamp
when available. These are historical observations, not live shelf prices.
Empty history returns HTTP 200 with an empty array and null statistics; invalid
parameters return 400 and an unknown barcode returns 404. Product catalogue
scans and history queries handle DynamoDB pagination. History returns at most one
page per request; when more observations exist, repeat the request with the
opaque `continuationToken`. The token is bound to the barcode, store, period,
date bounds, and page size, and malformed or mismatched tokens return 400.
History statistics (`latestPrice`, minimum, maximum, mean, and count) describe
only the observations in the returned page, not the entire requested period.
History and comparison
reads use the `ProductStoreHistoryIndex` GSI, whose reads are eventually
consistent, so a newly ingested observation may be briefly absent. Retained
observations may also outlive upstream deletions because deletion reconciliation
is intentionally deferred.
