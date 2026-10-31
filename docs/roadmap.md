# Grocery Price Tracker — Roadmap and Progress

Status: Project foundation. Updated 2026-10-28.

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
- [ ] Inspect a real Open Prices Parquet export schema and sample records with a local Python utility.
- [ ] Choose/finalize small Nancy barcode/store list and source-field mapping.
- [ ] Implement local filtering, validation, normalization, and record-based idempotency/corrections with focused tests.
- [ ] Create/configure DynamoDB tables and GSI, respecting minimal AWS permissions.
- [ ] Integrate ingestion with Lambda and EventBridge Scheduler; verify initial import and safe repeated runs.

## Week 2 — Public read-only REST API
- [ ] Implement products endpoint and basic API Gateway/Lambda integration.
- [ ] Implement latest observed store price comparison endpoint.
- [ ] Implement store-scoped history endpoint and selected-period statistics.
- [ ] Test happy path, validation, empty data, and source corrections through API/data layers.

## Week 3 — Frontend, deployment, and portfolio polish
- [ ] Build React catalog/comparison/history UI and dated-observation labeling.
- [ ] Add TanStack Query caching and time-filter behavior.
- [ ] Deploy frontend to private S3 behind CloudFront; connect public API.
- [ ] Verify complete live system; troubleshoot reliability, security, and reasonable AWS costs.
- [ ] Finish README with architecture, setup/deployment instructions, testing, limitations, data attribution/license, screenshots/demo.

## Immediate next Copilot task (not started)
Create minimal Python backend scaffolding and a **local** Parquet inspection tool. Requirements: CLI accepts a file path; reports row count, schema, up to three sample rows; avoids loading full dataset into memory; handles missing/unreadable paths; includes focused pytest tests with tiny generated Parquet fixtures. Do not download data or call AWS in this task. Define final implementation prompt in ChatGPT before sending it to Copilot.

## Collaboration workflow
1. Plan and approve one task and its acceptance criteria in ChatGPT.
2. Give a narrow implementation prompt to Copilot Agent in VS Code; ask it not to run Git mutations or cloud operations without approval.
3. Inspect changed files/diff; run relevant tests and manually verify important behavior.
4. Fix issues; commit to the feature branch only after user approval. Merge reviewed, working changes to `main`.
5. Update this roadmap after meaningful milestones and record deferred learning topics here.

## Current blockers
None reported. Need to inspect actual Open Prices file/schema before mapping fields.

## Concepts to revisit later
AWS IAM permission details, DynamoDB conditional writes/GSI consistency and pagination, Lambda packaging/performance, serverless cost tradeoffs, REST error contracts, browser query caching, CDN caching, and deeper testing/CI/CD practices. Add specific gaps as they arise.
