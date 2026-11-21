# Changelog

## Unreleased

- Added a statistical check of the contact-uplift ranking. The validation report only said the
  top deciles were "reviewed"; no number tested whether the T-learner ranks incremental
  response better than random. `uplift_validation.csv` (also in SQLite and the executive
  summary) now reports the Qini area, a 999-permutation p-value and the randomized hold-out
  effect against the mean prediction. Result: Qini area 0.0035, p = 0.096 (not significant at
  5%), observed uplift 7.14% vs predicted 4.96%. README and validation report state the
  consequence for the expected-incremental-profit figure. Decisions are unchanged.
- Regenerated the committed results. They predated the RM task-policy cap (#8):
  `rm_performance.csv`, `rm_worklist.csv`, `next_best_conversations.csv` and the SQLite layer
  were missing `policy_max_open_tasks` and `effective_contact_capacity`. Sixteen RMs with a
  monthly capacity above the 60-task cap showed uncapped utilisation, so average RM
  utilisation is 25.1%, not 24.3%. Updated the executive report (it now computes the figure
  instead of hard-coding it), the deck's utilisation slide and the workbook's RM Performance
  utilisation column. The workbook does not show the two new columns.
- CI's reproducibility job only checked that the regenerated digest had 64 characters, so
  stale committed results passed. It now compares every regenerated CSV, JSON and SQLite table
  with the committed values (`scripts/compare_outputs.py`).
- CI test matrix adds Python 3.13.
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
