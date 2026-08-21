"""Repository-level deterministic demo entry point."""

from pathlib import Path

from aurelia_sme_sales.pipeline import run_pipeline

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    summary = run_pipeline(root)
    print(
        "Generated "
        f"{summary['prioritised_conversations']:,} conversations and "
        f"TRY {summary['expected_incremental_profit_try']:,.0f} expected incremental profit."
    )
