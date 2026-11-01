# Grocery Price Tracker — Engineering Decisions

Status: Initial decisions approved; update deliberately if evidence changes. Updated 2026-10-28.

| Decision | Rationale |
| --- | --- |
| Historical *observed* prices rather than live prices or deal ratings | Keeps claims faithful to crowdsourced source data and avoids unsupported inference. |
| Open Prices daily Parquet export | Provides repeatable structured external input for a genuine ETL pipeline. |
| Nancy, France and ~15–20 curated packaged barcodes | Feasibility sample indicated sufficient observations; scope is manageable. |
| Match by barcode and physical location ID | Avoids ambiguous product matching and conflating different stores in the same chain. |
| Schedule one batch ingestion per day with EventBridge -> Lambda | Demonstrates cloud-triggered, event-driven batch processing without Kafka or queues. |
| Separate Products and PriceObservations DynamoDB tables | Simple mental model: tiny curated catalog plus potentially growing observations. |
| Observation source ID as main primary key | Enables idempotent imports and source corrections. |
| ProductStoreHistoryIndex GSI | Supports efficient store/product history queries and latest observation retrieval. |
| Store original observed date and source update timestamp separately | Avoids confusing a dated observation with when it was edited or imported. |
| Decimal-safe prices and arithmetic mean per observed record | Prevents float errors and mislabelled time-weighted averages. |
| Three public read-only REST endpoints with one API Lambda | Delivers needed behaviors without extra Lambda fragmentation. |
| React + TanStack Query | Familiar client UI and practical server-state caching. |
| Private S3 + CloudFront | Demonstrates static asset delivery and basic cloud distribution securely. |
| Focused tests, feature branches, GitHub documentation | Preserves fundamental software engineering quality for a portfolio. |
| Manual AWS deployment for MVP; defer SAM and GitHub Actions | Prioritize core AWS concepts within 2–3 weeks. Document setup for reproducibility. |
| No automatic source-deletion reconciliation initially | Avoid dangerous deletes/complex sync; disclose limitation. |
| No accounts, alerts, WebSockets, Kafka, or complex analytics | These are outside the approved MVP and better suited to later projects. |
| Fixed Nancy catalogue for the MVP | A version-controlled set of 17 recognizable packaged products and 5 physical store IDs keeps the first ingestion and user experience focused and reproducible. |
| Uneven store coverage is retained | Open Prices observations are concentrated in a few Nancy locations and dates; we preserve source store IDs rather than merging suspected duplicate OSM locations or inventing coverage. |
| 90-day history is the default chart window | Analysis showed useful recent coverage for many candidates while still requiring honest empty or sparse states; `1y` and `all` remain available for older observations. |

## Catalogue and observation caveats

The curated catalogue is intentionally fixed in
[`backend/ingestion/curated_catalog.json`](../backend/ingestion/curated_catalog.json)
and uses source physical store IDs as strings. Suspected duplicate locations remain
separate until there is evidence and an explicit identity-mapping decision.

Barcode-based `PRODUCT` observations may have a null `price_per`. A missing value is
reported as source data and must not, by itself, cause an observation to be rejected.
The catalogue does not assume that a missing `price_per` means `UNIT`; that validation
decision belongs to a later ingestion implementation.

## Pending implementation choices
- Specific source column mapping and final catalog/location identifiers.
- Exact requirements/package versions and Lambda packaging method.
- Simple chart library and visual UI specifics.
- AWS deployment configuration and practical cost limits.

## Working strategy
- Maintain approved MVP scope; streamline implementation when schedule pressure occurs rather than automatically dropping features.
- Essential understanding during implementation; defer deeper conceptual exploration to a post-project interview review.
- Project planning, task specification, code review, and acceptance discussions happen in ChatGPT. GitHub Copilot Agent in VS Code writes scoped code.
