# Grocery Price Comparison & History Tracker — Requirements

Status: MVP concept approved; backend ingestion and read-only API implemented. Updated 2026-11-01.

## Goal and users
Build a small, deployed serverless application that helps users compare real **historical observed** grocery prices and demonstrates practical AWS, data-pipeline, NoSQL, REST API, frontend, caching, testing, and Git skills for software engineering internship applications.

## MVP scope
- **Geography:** Nancy, France only, initially. This is a data-coverage choice, not support for international comparison.
- **Catalog:** About 15–20 manually curated packaged grocery items, matched by barcode. Product names/package descriptions may be curated separately from raw observations.
- **Stores:** A limited curated set of **physical store locations**, each identified by its Open Prices location ID. Do not conflate store locations with retail banners/chains.
- **Product browse/search:** Small catalog listing; simple client-side search is sufficient.
- **Comparison:** For a selected product, show the latest **observed** price at each supported store, including the observation date and store identity. A stale observation must not be presented as today's price.
- **History:** Choose a product and a physical store; display a chart of recorded observations over `30d`, `90d` (default), `1y`, or `all`.
- **Statistics:** For the selected period show latest observed price, minimum, maximum, simple arithmetic mean of observed prices, and observation count. These are **record-based** statistics, not daily/weekly/time-weighted averages.
- **Missing data:** Show empty/insufficient-data states honestly; do not interpolate observations on missing days or invent prices.
- **Source credit:** Attribute Open Prices and link to its dataset and applicable ODbL license. Consider obligations when redistributing derived data.

## Explicit non-goals
Authentication, user accounts, alerts, promotions/sale detection, deal rankings, price predictions, seasonal analysis, multi-market support, loose product-name matching, variable-weight products, retailer scraping, image use, Kafka, WebSockets, Redis, SQL, complex backend caching, and additional infrastructure tooling. AWS SAM and GitHub Actions are deferred for this MVP.

## Source and import behavior
- Source: Open Prices daily Parquet data export; ingestion runs once per day.
- Process only curated barcodes and physical location IDs.
- Restrict to relevant positive `UNIT` product observations in EUR, with valid source IDs and observation dates. Validate actual source schema from a real export before finalizing mapping.
- Preserve `sourceObservationId`, `barcode`, `storeId`, `observedDate`, `sourceUpdatedAt`, and decimal-safe price.
- Re-importing the same unchanged source record must not duplicate it. A source record with a newer `updated` timestamp may correct an existing record; stale versions must not overwrite newer ones.
- Failed downloads and write failures must be surfaced as failures; a valid import with zero new observations is a successful no-op.
- Track processing counts (examined, eligible, inserted, updated, skipped, invalid) in logs.
- Automatic reconciliation of deleted/retracted upstream observations is deferred. Disclose that retained data may not perfectly mirror upstream deletions.
- Prices are crowdsourced historical observations; their collection date differs from ingestion and source-update dates.

## API behavior
- `GET /products` — curated catalog with product barcodes and names.
- `GET /stores` — curated physical store catalogue with IDs, names, and addresses.
- `GET /products/{barcode}/comparison` — the most recent available observation for each curated store with data.
- `GET /products/{barcode}/history?storeId=<id>&period=90d&pageSize=100&continuationToken=<token>` — ordered observation points and page-scoped record-based statistics; periods: `30d`, `90d`, `1y`, `all`.
- History requires `storeId`; `period` defaults to `90d`; `pageSize` defaults to 100 and is bounded by the API; `continuationToken` retrieves the next page when more observations exist.
- Successful empty history periods return `200` with an empty observations array and null/unavailable stats. Invalid query parameters return `400`; unknown barcodes `404`; unexpected server failures `500`.
- Backend history statistics currently describe only the observations in the returned page, not the complete requested period. The frontend must retrieve all available history pages for the selected product, store, and period before calculating complete-period statistics with decimal-safe arithmetic. Page statistics must not be treated as full-period statistics.
- These are public, read-only HTTP endpoints; ingestion is not a public API.

## Acceptance criteria
- The local Parquet reader can inspect a real file and process selected records without loading the entire dataset eagerly.
- Validation, filtering, transformations, idempotent ingest, and correction rules have focused automated tests.
- A cloud ingestion run populates DynamoDB with useful real observations and subsequent runs do not create duplicates.
- The four REST endpoints serve correct data, including history windows, timestamps, pagination, and empty/error states.
- The React site can compare products, view history and statistics, and clearly identifies observations as historical.
- The project is deployed, a reviewer can access a live demonstration, and the README explains setup, architecture, limitations, tests, and licensing attribution.
- Key tests run successfully and no credentials or downloaded datasets are committed.
