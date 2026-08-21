"""Remove only deterministic generated outputs, preserving source and documentation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "data/demo/monthly_flows.csv",
    ROOT / "data/demo/campaign_history.csv",
    ROOT / "artifacts/results/candidate_features.csv",
    ROOT / "artifacts/results/product_opportunities.csv",
]
for target in TARGETS:
    if target.exists():
        target.unlink()
        print(f"REMOVED {target.relative_to(ROOT)}")
