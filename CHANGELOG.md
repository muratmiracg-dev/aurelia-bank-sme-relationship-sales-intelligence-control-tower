# Changelog

## Unreleased

- Rebuilt `MANIFEST.sha256`. Eleven entries (config, decisioning, economics, features,
  propensity, three test modules and three docs) were stale, so `make verify` failed on `main`.
- CI now runs `scripts/verify_artifacts.py`, and `make ci` includes `verify`, so a stale manifest
  fails the pull request.
- `scripts/build_manifest.py` hashes only git-tracked files, so local build output such as
  `*.egg-info` cannot enter the manifest and break verification on a fresh checkout.

## 1.0.0 - 2026-08-21

- Added deterministic SME Customer 360, relationship and product-holding data.
- Added eight-product need, propensity and temporal validation framework.
- Added treatment/control T-learner uplift estimates and decile evidence.
- Added FTP, expected-loss, allocated-capital and RAROC-style economics.
- Added permission, KYC, AML, credit-risk and product-suitability gates.
- Added next-best-conversation, RM capacity, worklist and sales-funnel outputs.
- Added read-only FastAPI, CLI, PostgreSQL, SQLite and Power BI assets.
- Added Excel workbench, executive PowerPoint, PDF report and governance documentation.
- Added 90% coverage gate, Ruff, CI, CodeQL, Dependabot and SHA-256 verification.
