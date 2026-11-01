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
