# Grocery Price Tracker — Coding Agent Instructions

This repository is an internship portfolio project. We plan and approve requirements and architecture in ChatGPT; GitHub Copilot Agent in VS Code performs scoped implementation tasks. Read `docs/requirements.md`, `docs/architecture.md`, `docs/decisions.md`, and `docs/roadmap.md` before implementing features or changing architecture.

## Work boundaries
- Implement only the specific, approved task. Do not expand the MVP or add unrelated features.
- Follow the documented design. Discuss material changes to architecture, cloud services, data contracts, and dependencies before making them.
- Prefer the simplest correct, readable, maintainable implementation. Reuse established conventions; avoid speculative abstractions and unrelated refactoring.
- Keep ingestion/data normalization, persistence, API handling, and frontend concerns appropriately separated.
- Where requirements are ambiguous, state assumptions or ask rather than inventing product behavior.

## Data correctness
- Treat Open Prices records as dated observations, **not** live/current store prices or confirmed sales.
- Use string barcodes and stable physical store IDs (not merely retail-chain names).
- Preserve original source observation ID, observation date, and source update timestamp.
- Make repeated ingestion idempotent; apply a correction only when its source update timestamp is newer.
- Validate price, currency, product/store membership, and supported observation types; do not invent or interpolate missing observations.
- Do not silently delete observations absent from an import. Source deletion reconciliation is deferred and documented.
- Store monetary data with decimal-safe representations rather than binary floating-point amounts.

## Quality, testing, and security
- Add or update focused tests with meaningful behavior changes; run relevant checks where possible.
- Report tests actually run, their outcomes, and anything not tested; never claim unrun tests passed.
- Do not commit credentials, secrets, `.env` files, virtual environments, or downloaded source datasets.
- Do not create/deploy AWS resources or make potentially billable cloud changes without explicit approval.
- Do not add AWS SAM, GitHub Actions, Kafka, WebSockets, Redis, authentication, or other deferred features unless approved.

## Git and handoff
- Work on the user's current feature branch; keep `main` stable.
- Do not commit, push, merge, reset, or open PRs unless explicitly asked.
- After each task, summarize changed files, important choices, exact test results, and unresolved issues.
- Update relevant documents when an approved decision changes; keep `docs/roadmap.md` accurate at meaningful milestones.
