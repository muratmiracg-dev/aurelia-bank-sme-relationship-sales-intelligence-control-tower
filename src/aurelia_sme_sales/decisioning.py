"""Governed next-best-conversation and relationship-manager work allocation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .constants import CREDIT_PRODUCTS, DERIVED_ANALYTICS


def build_opportunities(
    economics: pd.DataFrame,
    relationship_managers: pd.DataFrame,
    products: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    """Apply conduct gates, rank opportunities and allocate finite RM capacity."""
    assumptions = config["assumptions"]
    policy = assumptions["decision_policy"]
    weights = assumptions["score_weights"]
    frame = economics.copy()
    suppressions = [_suppression_reasons(row, policy) for row in frame.itertuples()]
    frame["suppression_reason"] = ["|".join(items) for items in suppressions]
    frame["eligible_flag"] = frame["suppression_reason"] == ""
    uplift_component = np.clip(frame["predicted_contact_uplift"] / 0.20, 0, 1)
    frame["opportunity_score"] = np.round(
        100
        * (
            float(weights["propensity"]) * frame["propensity_probability"]
            + float(weights["uplift"]) * uplift_component
            + float(weights["need"]) * frame["need_signal"]
            + float(weights["profitability"]) * frame["profitability_percentile"]
            + float(weights["relationship_gap"]) * frame["relationship_gap"]
        ),
        2,
    )
    frame["policy_threshold_pass"] = (
        (frame["propensity_probability"] >= float(policy["minimum_propensity"]))
        & (frame["predicted_contact_uplift"] >= float(policy["minimum_uplift"]))
        & (frame["expected_incremental_profit_try"] >= float(policy["minimum_expected_profit_try"]))
        & (frame["opportunity_score"] >= float(policy["minimum_priority_score"]))
    )
    frame["recommendation_status"] = np.select(
        [
            ~frame["eligible_flag"],
            ~frame["policy_threshold_pass"],
            frame["opportunity_score"] >= float(policy["high_priority_score"]),
        ],
        ["SUPPRESSED", "MONITOR", "HIGH_PRIORITY"],
        default="MEDIUM_PRIORITY",
    )
    frame["human_review_required"] = [
        bool(products[row.product_code]["human_review"]) for row in frame.itertuples()
    ]
    frame["conversation_prompt"] = [
        str(products[row.product_code]["conversation"]) for row in frame.itertuples()
    ]
    frame["product_label"] = [
        str(products[row.product_code]["label"]) for row in frame.itertuples()
    ]
    frame["data_class"] = DERIVED_ANALYTICS

    ranked = frame.loc[frame["eligible_flag"] & frame["policy_threshold_pass"]].sort_values(
        ["customer_id", "opportunity_score"], ascending=[True, False]
    )
    next_best = ranked.groupby("customer_id", as_index=False).head(1).copy()
    next_best["customer_rank_within_rm"] = next_best.groupby("rm_id")["opportunity_score"].rank(
        method="first", ascending=False
    )
    managers_with_capacity = relationship_managers.copy()
    managers_with_capacity["policy_max_open_tasks"] = int(policy["max_open_tasks_per_rm"])
    managers_with_capacity["effective_contact_capacity"] = managers_with_capacity[
        ["monthly_contact_capacity", "policy_max_open_tasks"]
    ].min(axis=1)
    capacity = managers_with_capacity[
        [
            "rm_id",
            "monthly_contact_capacity",
            "policy_max_open_tasks",
            "effective_contact_capacity",
        ]
    ]
    next_best = next_best.merge(capacity, on="rm_id", validate="many_to_one")
    next_best["capacity_allocated_flag"] = (
        next_best["customer_rank_within_rm"] <= next_best["effective_contact_capacity"]
    )
    next_best["work_status"] = np.where(
        next_best["capacity_allocated_flag"], "CONTACT_DUE", "CAPACITY_WAITLIST"
    )
    next_best["task_id"] = [f"TASK{i:06d}" for i in range(1, len(next_best) + 1)]
    next_best["task_sla_days"] = int(policy["task_sla_days"])
    next_best["final_decision_owner"] = "AUTHORISED_RELATIONSHIP_MANAGER"
    next_best["automated_sale_flag"] = False

    rm_worklist = next_best.loc[next_best["capacity_allocated_flag"]].copy()
    rm_worklist = rm_worklist.sort_values(["rm_id", "opportunity_score"], ascending=[True, False])
    rm_performance = _rm_performance(frame, rm_worklist, managers_with_capacity)
    funnel = _sales_funnel(next_best)
    return {
        "product_opportunities": frame,
        "next_best_conversations": next_best,
        "rm_worklist": rm_worklist,
        "rm_performance": rm_performance,
        "sales_funnel": funnel,
    }


def _suppression_reasons(row: object, policy: dict[str, Any]) -> list[str]:
    reasons = []
    if not bool(row.contact_permission):
        reasons.append("NO_CONTACT_PERMISSION")
    if not bool(row.beneficial_owner_complete):
        reasons.append("BENEFICIAL_OWNER_INCOMPLETE")
    if float(row.kyc_overdue_days) > float(policy["kyc_overdue_days_block"]):
        reasons.append("KYC_MATERIALLY_OVERDUE")
    if bool(policy["aml_high_priority_block"]) and row.aml_alert_priority == "HIGH":
        reasons.append("HIGH_PRIORITY_AML_REVIEW")
    if row.product_code in CREDIT_PRODUCTS:
        if float(row.pd_12m) > float(policy["high_pd_block"]):
            reasons.append("CREDIT_RISK_OUTSIDE_SALES_POLICY")
        if int(row.days_past_due) >= int(policy["arrears_days_block"]):
            reasons.append("MATERIAL_ARREARS")
        if not bool(row.financials_fresh_flag):
            reasons.append("FINANCIALS_REFRESH_REQUIRED")
    if row.product_code == "FX_RISK_MANAGEMENT" and float(row.need_signal) < 0.20:
        reasons.append("NO_DOCUMENTED_FX_NEED")
    return reasons


def _rm_performance(
    opportunities: pd.DataFrame,
    worklist: pd.DataFrame,
    rms: pd.DataFrame,
) -> pd.DataFrame:
    portfolio = opportunities.groupby("rm_id", as_index=False).agg(
        candidate_opportunities=("candidate_id", "count"),
        eligible_opportunities=("eligible_flag", "sum"),
    )
    allocated = worklist.groupby("rm_id", as_index=False).agg(
        allocated_tasks=("task_id", "count"),
        high_priority_tasks=(
            "recommendation_status",
            lambda values: int((values == "HIGH_PRIORITY").sum()),
        ),
        expected_incremental_profit_try=("expected_incremental_profit_try", "sum"),
        average_opportunity_score=("opportunity_score", "mean"),
    )
    result = rms.merge(portfolio, on="rm_id", how="left").merge(allocated, on="rm_id", how="left")
    numeric = [
        "candidate_opportunities",
        "eligible_opportunities",
        "allocated_tasks",
        "high_priority_tasks",
        "expected_incremental_profit_try",
        "average_opportunity_score",
    ]
    result[numeric] = result[numeric].fillna(0)
    result["capacity_utilisation"] = (
        result["allocated_tasks"] / result["effective_contact_capacity"]
    )
    result["expected_target_coverage"] = (
        result["expected_incremental_profit_try"] / result["annual_target_try"]
    )
    result["data_class"] = DERIVED_ANALYTICS
    return result


def _sales_funnel(next_best: pd.DataFrame) -> pd.DataFrame:
    allocated = next_best.loc[next_best["capacity_allocated_flag"]].copy()
    proposals = int(round(len(allocated) * 0.39))
    expected_activation_rate = (
        float(allocated["propensity_probability"].mean()) if len(allocated) else 0.0
    )
    stages = [
        ("Prioritised conversations", len(allocated)),
        ("Expected contacts", int(round(len(allocated) * 0.86))),
        ("Expected qualified needs", int(round(len(allocated) * 0.58))),
        ("Expected proposals", proposals),
        ("Expected activations", int(round(proposals * expected_activation_rate))),
    ]
    frame = pd.DataFrame(stages, columns=["funnel_stage", "expected_count"])
    frame["stage_order"] = np.arange(1, len(frame) + 1)
    frame["conversion_from_prior"] = frame["expected_count"] / frame["expected_count"].shift(1)
    frame.loc[0, "conversion_from_prior"] = 1.0
    frame["data_class"] = DERIVED_ANALYTICS
    return frame
