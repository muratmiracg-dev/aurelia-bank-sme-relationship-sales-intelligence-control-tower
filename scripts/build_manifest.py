"""Build a SHA-256 manifest for committed professional deliverables."""

from __future__ import annotations

import hashlib
import subprocess
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


def candidate_paths() -> list[Path]:
    """Prefer git-tracked files so local build output (egg-info, caches) never enters the
    manifest; a fresh CI checkout would otherwise report those entries as missing."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z"],  # noqa: S607 - fixed command, no user input
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        return sorted(ROOT.rglob("*"))
    return sorted(ROOT / name for name in listed.split("\0") if name)


rows = []
for path in candidate_paths():
    if included(path):
        rows.append(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        )
(ROOT / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"WROTE {len(rows)} manifest entries")
