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
