"""Verify required deliverables, controls and SHA-256 evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "artifacts/results/executive_summary.json",
    "artifacts/results/model_performance.csv",
    "artifacts/results/next_best_conversations.csv",
    "artifacts/results/management_controls.csv",
    "artifacts/aurelia_sme_sales_demo.sqlite",
    "artifacts/figures/executive-overview.png",
    "excel/Aurelia_Bank_SME_Relationship_Sales_Workbench.xlsx",
    "presentation/Aurelia_Bank_SME_Relationship_Sales_Executive_Deck_EN.pptx",
    "report/Aurelia_Bank_SME_Relationship_Sales_Executive_Report.pdf",
    "powerbi/SME_Relationship_Sales_Measures.dax",
    "sql/schema.sql",
]


def main() -> None:
    missing = [item for item in REQUIRED if not (ROOT / item).exists()]
    if missing:
        raise SystemExit(f"Missing required artifacts: {missing}")
    summary = json.loads((ROOT / "artifacts/results/executive_summary.json").read_text())
    if summary["prioritised_conversations"] <= 0:
        raise SystemExit("No prioritised conversations were generated")
    dq = pd.read_csv(ROOT / "artifacts/results/data_quality_controls.csv")
    if not (dq["status"] == "PASS").all():
        raise SystemExit("One or more data-quality controls failed")
    next_best = pd.read_csv(ROOT / "artifacts/results/next_best_conversations.csv")
    selected = next_best.loc[next_best["capacity_allocated_flag"].astype(str).str.lower() == "true"]
    if selected["automated_sale_flag"].astype(str).str.lower().eq("true").any():
        raise SystemExit("Automated sale flag must always be false")
    manifest = ROOT / "MANIFEST.sha256"
    if not manifest.exists():
        raise SystemExit("MANIFEST.sha256 is missing")
    verified = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Manifest mismatch: {relative}")
        verified += 1
    print(f"VERIFIED {len(REQUIRED)} required deliverables and {verified} manifest entries")


if __name__ == "__main__":
    main()
