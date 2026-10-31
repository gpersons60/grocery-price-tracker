# Grocery Price Tracker — Architecture

Status: Approved high-level design, to be validated incrementally while building. Updated 2026-10-28.

## Technology stack
- Ingestion/REST backend: Python on AWS Lambda.
- Trigger: Amazon EventBridge Scheduler, once daily.
- Dataset: Open Prices Parquet export; initially filter to curated products and physical stores in Nancy, France.
- Database: Amazon DynamoDB (on-demand capacity), with two tables and a GSI.
- HTTP: Amazon API Gateway HTTP API invoking one read-only API Lambda (three routes).
- Frontend: React, with TanStack Query for client-side API caching and a history chart library chosen during implementation.
- Static hosting: Private S3 bucket through CloudFront (use Origin Access Control).
- Operations: CloudWatch logs/basic failure monitoring, least-privilege IAM, and a small AWS Budget alert (alert is NOT a spending cap).
- Version control and testing: Git/GitHub, scoped feature branches and local automated tests. Manual cloud configuration/documentation for MVP; no AWS SAM or GitHub Actions initially.

## Data flow

```text
Open Prices daily Parquet export
              |
EventBridge daily schedule
              v
      Python ingestion Lambda
   filter -> validate -> normalize
    -> idempotent upsert/correction
              |
              v
  DynamoDB PriceObservations
  DynamoDB Products (curated)
              ^
              |
        API Lambda (read-only)
              ^
              |
       API Gateway HTTP API
              ^
              |
React + TanStack Query in browser
              ^
              |
   CloudFront <- private S3 site assets
```

EventBridge emits a scheduled invocation event; this is batch processing, not streaming or an event queue. No SQS is required for the MVP.

## DynamoDB access patterns

### Table `Products`
- Partition key: `barcode` (String).
- Attributes: `name`, `packageSize`, `active`, and configured physical store IDs (with display names where useful).
- Tiny catalog (15–20 rows): a simple `Scan` for catalog browsing is acceptable.

### Table `PriceObservations`
- Partition key: `sourceObservationId` (String), e.g. `OPEN_PRICES#12345`.
- Attributes: `barcode` (String), `storeId` (String), `price` (decimal-safe DynamoDB Number), `currency`, `observedDate` (`YYYY-MM-DD`), `sourceUpdatedAt` (comparable ISO timestamp), `productStoreKey` (`barcode#storeId`), `observationSortKey` (`YYYY-MM-DD#sourceObservationId`). Store names may be supplied by curated catalog metadata rather than repeated in every row.
- GSI `ProductStoreDateIndex`: partition `productStoreKey`, sort `observationSortKey`, with projections sufficient for history responses.

Query one product and one physical store by GSI, with sort-key date ranges for historical windows. Retrieve the newest indexed observation per store for comparison. DynamoDB GSIs are eventually consistent; brief indexing delay is acceptable for historical data. Handle pagination if the query size requires it.

The persistence layer writes `sourceObservationId` as the table partition key and
uses `ProductStoreDateIndex` with `productStoreKey` (`barcode#storeId`) and
`observationSortKey` (`observedDate#sourceObservationId`). Source update timestamps
are compared as integer UTC epoch microseconds in `sourceVersion`, preserving
fractional-second ordering. Conditional updates insert new IDs, accept only newer
versions, and replace all indexed attributes when a correction moves an observation
to another date or store. Records without a source update timestamp may be inserted
but never overwrite an existing record. GSI reads are eventually consistent.
Automatic source-deletion reconciliation is deferred, and corrections that move
records outside the curated selection are not ingested by this stage.

The source observation ID is the primary identity for upsert. Use conditional writes or equivalent safe logic to prevent older source updates overwriting newer corrections. If a corrected record changes product/store/date, verify that the index attributes update consistently.

## Stats and correctness
- Compute period stats in the API from selected observed records (small MVP dataset), using decimal-safe arithmetic before JSON serialization.
- Mean is `sum(prices) / count(observations)`, not time-weighted. No filling missing days.
- Sort date-plus-ID consistently; separate observed date, source-updated timestamp, and ingestion time.
- Do not present unobserved prices as zero or imply latest observation is current shelf price.

## Operational behavior
- Daily ingestion: retrieve/stream or batch-read Parquet, filter cheaply, validate/normalize, then write eligible rows. Minimize memory usage; verify Lambda package compatibility, dependency size, duration, and memory using real data before deployment.
- Run failures: download/processing/write failures log and fail the run; normal no-op imports succeed.
- Source deletions: do not automatically delete a local record solely because it is absent from an import. Full reconciliation is deferred and must be described as a limitation.
- Credentials/config: use AWS IAM roles and environment configuration; no secrets in source control.
- Frontend/CDN: TanStack Query provides application-level caching. CloudFront delivers static assets; no separate API cache is required.

## Open questions to validate during implementation
- Exact Open Prices export columns, null behavior, file size, and location ID format.
- Final Nancy barcode/location shortlist from the feasibility sample.
- Parquet dependency packaging and Lambda resource needs.
- Exact decimal representation/precision and public API response JSON fields.
- AWS account region, deployment steps, and budget safeguards.
