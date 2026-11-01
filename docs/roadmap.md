# Grocery Price Tracker — Roadmap and Progress

Status: Backend ingestion and read-only API complete; frontend next. Updated 2026-11-01.

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
- [ ] Copy and review repository foundation files from the prepared ZIP (this package).
- [ ] Review current `git status -sb` and plan a documentation/setup commit when ready.

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
- [ ] Build React catalog/comparison/history UI and dated-observation labeling.
- [ ] Add TanStack Query caching and time-filter behavior.
- [ ] Deploy frontend to private S3 behind CloudFront; connect public API.
- [ ] Verify complete live system; troubleshoot reliability, security, and reasonable AWS costs.
- [ ] Finish README with architecture, setup/deployment instructions, testing, limitations, data attribution/license, screenshots/demo.

## Upcoming milestone — React frontend
Build the React catalogue, comparison, and history views. Use TanStack Query for API requests and retrieve all pages of history for the selected product, store, and period before calculating complete-period statistics with decimal-safe arithmetic. Clearly label observations as historical and preserve honest empty or sparse-data states.

## Collaboration workflow
1. Plan and approve one task and its acceptance criteria in ChatGPT.
2. Give a narrow implementation prompt to Copilot Agent in VS Code; ask it not to run Git mutations or cloud operations without approval.
3. Inspect changed files/diff; run relevant tests and manually verify important behavior.
4. Fix issues; commit to the feature branch only after user approval. Merge reviewed, working changes to `main`.
5. Update this roadmap after meaningful milestones and record deferred learning topics here.

## Current blockers
None reported for the completed backend and API milestones. Frontend implementation remains the next planned work.

## Concepts to revisit later
AWS IAM permission details, DynamoDB conditional writes/GSI consistency and pagination, Lambda packaging/performance, serverless cost tradeoffs, REST error contracts, browser query caching, CDN caching, and deeper testing/CI/CD practices. Add specific gaps as they arise.
