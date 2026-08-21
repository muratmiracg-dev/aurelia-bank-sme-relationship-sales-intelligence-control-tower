"""End-to-end governed SME relationship-sales analytical pipeline."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_project_config
from .controls import conduct_monitoring, data_quality_controls, management_controls
from .decisioning import build_opportunities
from .economics import calculate_product_economics
from .exceptions import DataQualityError
from .features import build_customer_360
from .generator import build_demo_data
from .propensity import fit_propensity_models, score_candidates
from .reporting import create_figures


def run_pipeline(root: str | Path, seed: int = 20260821) -> dict[str, Any]:
    """Generate sources, analytics, governed decisions and reproducibility evidence."""
    root = Path(root).resolve()
    config = load_project_config(root)
    data = build_demo_data(config, seed=seed)
    _write_frames(data, root / "data" / "demo")
    customer_360, candidates = build_customer_360(data, config)
    dq_controls = data_quality_controls(data, customer_360, candidates)
    if not (dq_controls["status"] == "PASS").all():
        raise DataQualityError("One or more pre-decision data-quality controls failed")
    bundle = fit_propensity_models(data["campaign_history"], seed)
    scored = score_candidates(candidates, bundle)
    economics = calculate_product_economics(scored, config)
    decisions = build_opportunities(
        economics,
        data["relationship_managers"],
        config["products"],
        config,
    )
    conduct = conduct_monitoring(
        decisions["product_opportunities"], decisions["next_best_conversations"]
    )
    management = management_controls(
        customer_360,
        decisions["product_opportunities"],
        decisions["next_best_conversations"],
        decisions["rm_performance"],
        bundle.performance,
        conduct,
        config,
    )
    results = {
        "customer_360": customer_360,
        "candidate_features": candidates,
        "propensity_scores": scored[
            [
                "candidate_id",
                "customer_id",
                "rm_id",
                "product_code",
                "propensity_probability",
                "predicted_contact_uplift",
                "reason_1",
                "reason_2",
                "reason_3",
                "data_class",
            ]
        ],
        "model_performance": bundle.performance,
        "uplift_deciles": bundle.uplift_deciles,
        "model_coefficients": bundle.coefficients,
        **decisions,
        "conduct_monitoring": conduct,
        "data_quality_controls": dq_controls,
        "management_controls": management,
    }
    _write_frames(results, root / "artifacts" / "results")
    figures = create_figures(results, root / "artifacts" / "figures")
    summary = _executive_summary(data, results, config, seed)
    summary_path = root / "artifacts" / "results" / "executive_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_sqlite(
        root / "artifacts" / "aurelia_sme_sales_demo.sqlite",
        {
            "relationship_managers": data["relationship_managers"],
            "customer_360": customer_360,
            "next_best_conversations": decisions["next_best_conversations"],
            "rm_worklist": decisions["rm_worklist"],
            "rm_performance": decisions["rm_performance"],
            "sales_funnel": decisions["sales_funnel"],
            "model_performance": bundle.performance,
            "uplift_deciles": bundle.uplift_deciles,
            "conduct_monitoring": conduct,
            "data_quality_controls": dq_controls,
            "management_controls": management,
        },
    )
    summary["figure_count"] = len(figures)
    return summary


def _write_frames(frames: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, float_format="%.6f")


def _write_sqlite(path: Path, frames: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as connection:
        for name, frame in frames.items():
            safe = frame.copy()
            for column in safe.select_dtypes(include=["datetime64[ns]"]).columns:
                safe[column] = safe[column].dt.strftime("%Y-%m-%d")
            safe.to_sql(name, connection, index=False, if_exists="replace")
        connection.execute("CREATE INDEX idx_customer_360_customer ON customer_360(customer_id)")
        connection.execute(
            "CREATE INDEX idx_next_best_customer ON next_best_conversations(customer_id)"
        )
        connection.execute("CREATE INDEX idx_worklist_rm ON rm_worklist(rm_id)")


def _executive_summary(
    data: dict[str, pd.DataFrame],
    results: dict[str, pd.DataFrame],
    config: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    customers = results["customer_360"]
    opportunities = results["product_opportunities"]
    next_best = results["next_best_conversations"]
    selected = next_best.loc[next_best["capacity_allocated_flag"]]
    champion = (
        results["model_performance"].loc[results["model_performance"]["selected_champion"]].iloc[0]
    )
    controls = results["management_controls"]
    product_mix = (
        selected.groupby("product_label")
        .agg(
            conversations=("candidate_id", "count"),
            expected_profit_try=("expected_incremental_profit_try", "sum"),
        )
        .sort_values("expected_profit_try", ascending=False)
        .round(2)
        .to_dict(orient="index")
    )
    digest_frames = [
        customers[["customer_id", "relationship_depth_score", "wallet_share_proxy"]],
        selected[["candidate_id", "opportunity_score", "expected_incremental_profit_try"]],
        controls[["control_id", "status", "actual_value"]],
    ]
    digest = hashlib.sha256()
    for frame in digest_frames:
        digest.update(frame.to_csv(index=False, float_format="%.6f").encode("utf-8"))
    return {
        "project": "Aurelia Bank SME Relationship & Sales Intelligence Control Tower",
        "as_of_date": config["assumptions"]["as_of_date"],
        "seed": seed,
        "synthetic_customers": len(customers),
        "relationship_managers": len(data["relationship_managers"]),
        "product_holdings": len(data["product_holdings"]),
        "historical_campaigns": len(data["campaign_history"]),
        "candidate_opportunities": len(opportunities),
        "eligible_candidates": int(opportunities["eligible_flag"].sum()),
        "policy_qualified_candidates": int(opportunities["policy_threshold_pass"].sum()),
        "prioritised_conversations": len(selected),
        "high_priority_conversations": int(
            (selected["recommendation_status"] == "HIGH_PRIORITY").sum()
        ),
        "capacity_waitlist": int((next_best["work_status"] == "CAPACITY_WAITLIST").sum()),
        "expected_incremental_profit_try": round(
            float(selected["expected_incremental_profit_try"].sum()), 2
        ),
        "weighted_activation_probability": round(
            float(selected["propensity_probability"].mean()), 6
        ),
        "kyc_overdue_rate": round(float((customers["kyc_overdue_days"] > 0).mean()), 6),
        "champion_model": str(champion["model"]),
        "champion_roc_auc": round(float(champion["roc_auc"]), 6),
        "champion_pr_auc": round(float(champion["pr_auc"]), 6),
        "champion_brier_score": round(float(champion["brier_score"]), 6),
        "champion_top_decile_lift": round(float(champion["top_decile_lift"]), 6),
        "data_quality_passed": int((results["data_quality_controls"]["status"] == "PASS").sum()),
        "data_quality_total": len(results["data_quality_controls"]),
        "management_control_breaches": int((controls["status"] == "BREACH").sum()),
        "management_controls_total": len(controls),
        "product_mix": product_mix,
        "canonical_result_sha256": digest.hexdigest(),
        "decision_boundary": (
            "Human-led decision support only. No automated sale, credit approval, "
            "customer restriction "
            "or binding product recommendation."
        ),
    }
