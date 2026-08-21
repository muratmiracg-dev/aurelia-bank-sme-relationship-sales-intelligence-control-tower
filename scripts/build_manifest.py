"""Build a SHA-256 manifest for committed professional deliverables."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".venv", ".pytest_cache", ".ruff_cache", "__pycache__", "tmp", ".git"}
EXCLUDED_FILES = {
    "MANIFEST.sha256",
    ".coverage",
    "data/demo/monthly_flows.csv",
    "data/demo/campaign_history.csv",
    "artifacts/results/candidate_features.csv",
    "artifacts/results/product_opportunities.csv",
}


def included(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return (
        path.is_file()
        and not any(part in EXCLUDED_PARTS for part in path.parts)
        and relative not in EXCLUDED_FILES
        and not relative.endswith(".inspect.ndjson")
    )


rows = []
for path in sorted(ROOT.rglob("*")):
    if included(path):
        rows.append(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        )
(ROOT / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"WROTE {len(rows)} manifest entries")
