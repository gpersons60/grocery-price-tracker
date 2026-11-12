# Grocery Price Tracker — Roadmap and Progress

Status: Backend ingestion, read-only API, frontend Milestone 4B, frontend deployment, and manual end-to-end verification complete. Portfolio documentation updated. Updated 2026-11-12.

## Timeline and working agreement
Target: 2–3 focused development weeks, with implementation, testing, review and deployment. Schedule is a target, not a guarantee. Preserve the agreed MVP; streamline implementation and defer deep theory before proposing scope changes. Continue LeetCode/interview preparation separately.

## Engineering Objectives and Skills
Build maintainable, scalable foundations while keeping the MVP intentionally small:

- Develop a Python backend for ETL, validation, and scheduled batch processing.
- Practice AWS serverless architecture, DynamoDB access-pattern design, REST APIs, and React frontend integration.
- Apply scalable ingestion concepts such as idempotency, source-data corrections, reliability, and honest handling of partial data.
- Strengthen automated testing, Git workflow, cloud deployment, and monitoring skills.
- Prefer simple, proportionate infrastructure over unnecessary services or premature optimization; AWS SAM and GitHub Actions remain deferred.

## Completed setup
- [x] MVP concept and architecture reviewed with friend.
- [x] Repository created and cloned: `gpersons60/grocery-price-tracker` (`main`).
- [x] Local branch created: `feat/ingestion-setup`.
- [x] Python 3.14.0 virtual environment created and activated as `.venv` in VS Code CMD.
- [x] Local `.gitignore` created; `git status -sb` showed only `.gitignore` as untracked.

## Week 1 — Data pipeline and DynamoDB
- [x] Inspect a real Open Prices Parquet export schema and sample records with a local Python utility.
- [x] Choose/finalize small Nancy barcode/store list and source-field mapping.
- [x] Implement local filtering, validation, and normalization with focused tests.
- [x] Create/configure DynamoDB tables and the `ProductStoreHistoryIndex` GSI, respecting minimal AWS permissions.
- [x] Integrate ingestion with Lambda and EventBridge Scheduler; deployment completed.

## Week 2 — Public read-only REST API
- [x] Implement products endpoint and basic API Gateway/Lambda integration.
- [x] Implement latest observed store price comparison endpoint.
- [x] Implement store-scoped history endpoint and selected-period statistics.
- [x] Test happy path, validation, empty data, pagination, and date filtering through API/data layers.
- [x] Deploy the read-only Lambda and API Gateway HTTP API with four routes.
- [x] Manually verify the four deployed endpoints on 2026-11-01. Local backend test suite: 50 tests passed. No untested operations are claimed as verified.

## Week 3 — Frontend, deployment, and portfolio polish
- [x] Build the first React frontend milestone: Vite/React scaffolding, `/products` API integration, and searchable catalogue with historical-observation labeling.
- [x] Build the React store comparison milestone with complete store coverage and historical observation labeling.
- [x] Build Milestone 3A: historical price API integration, complete pagination, and period selection.
- [x] Build Milestone 3B: interactive historical price charts.
- [x] Build Milestone 3C: complete-period historical price statistics.
- [x] Add TanStack Query caching and time-filter behavior.
- [x] Build Milestone 4A: lazy-load chart code and split Recharts from the initial bundle.
- [x] Build Milestone 4B: query caching and pre-deployment reliability review (selection isolation, pagination, states, responsiveness, and accessibility).
- [x] Deploy frontend to private S3 behind CloudFront with OAC and connect the public API.
- [x] Manually verify the deployed frontend and four API endpoints end to end.
- [x] Finish README and deployment documentation with architecture, setup, testing, limitations, screenshots, demo, and Open Prices attribution/licensing links.

## Milestone 6 — Deployment and portfolio documentation
Frontend catalogue, comparison, history, chart, statistics, chart-loading optimization, and Milestone 4B reliability review are complete. The frontend is deployed behind private S3 and CloudFront OAC, and the live frontend plus four API endpoints were manually verified. Documentation records the deployment procedure and remaining limitations without claiming automated production monitoring or additional unperformed tests.

## Collaboration workflow
1. Plan and approve one task and its acceptance criteria in ChatGPT.
2. Give a narrow implementation prompt to Copilot Agent in VS Code; ask it not to run Git mutations or cloud operations without approval.
3. Inspect changed files/diff; run relevant tests and manually verify important behavior.
4. Fix issues; commit to the feature branch only after user approval. Merge reviewed, working changes to `main`.
5. Update this roadmap after meaningful milestones and record deferred learning topics here.

## Current blockers
None reported for the completed MVP. AWS deployment automation, broader monitoring, source-deletion reconciliation, and a source-code license remain deferred or pending decisions.

## Concepts to revisit later
AWS IAM permission details, DynamoDB conditional writes/GSI consistency and pagination, Lambda packaging/performance, serverless cost tradeoffs, REST error contracts, browser query caching, CDN caching, and deeper testing/CI/CD practices. Add specific gaps as they arise.
