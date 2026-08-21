"""Data-quality, conduct, model and operating controls."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .constants import DERIVED_ANALYTICS, PRODUCTS


def data_quality_controls(
    data: dict[str, pd.DataFrame],
    customer_360: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate source-to-feature integrity before decisioning."""
    checks = [
        _check(
            "DQ01",
            "Customer identifiers are unique",
            data["customers"]["customer_id"].is_unique,
            "Data Office",
        ),
        _check(
            "DQ02",
            "Relationship-manager identifiers are unique",
            data["relationship_managers"]["rm_id"].is_unique,
            "Sales Operations",
        ),
        _check(
            "DQ03",
            "Every customer has an assigned relationship manager",
            data["customers"]["rm_id"].isin(data["relationship_managers"]["rm_id"]).all(),
            "Sales Operations",
        ),
        _check(
            "DQ04",
            "Every risk profile resolves to one customer",
            set(data["risk_profile"]["customer_id"]) == set(data["customers"]["customer_id"]),
            "Credit Risk",
        ),
        _check(
            "DQ05",
            "Monthly-flow amounts are non-negative",
            (data["monthly_flows"].select_dtypes("number") >= 0).all().all(),
            "Data Office",
        ),
        _check(
            "DQ06",
            "Every holding uses a governed product code",
            data["product_holdings"]["product_code"].isin(PRODUCTS).all(),
            "Product Governance",
        ),
        _check(
            "DQ07",
            "Historical campaign labels are binary",
            data["campaign_history"]["activated_flag"].isin([0, 1]).all(),
            "Model Development",
        ),
        _check(
            "DQ08",
            "Historical treatment assignment is binary",
            data["campaign_history"]["treatment_flag"].isin([0, 1]).all(),
            "Model Development",
        ),
        _check(
            "DQ09",
            "Customer 360 has exactly one row per customer",
            len(customer_360) == customer_360["customer_id"].nunique() == len(data["customers"]),
            "Data Office",
        ),
        _check(
            "DQ10",
            "Candidate identifiers are unique",
            candidates["candidate_id"].is_unique,
            "Analytics",
        ),
        _check(
            "DQ11",
            "Candidate need signals are bounded",
            candidates["need_signal"].between(0, 1).all(),
            "Analytics",
        ),
        _check(
            "DQ12",
            "No existing product is proposed as a candidate",
            _no_held_product_candidate(data["product_holdings"], candidates),
            "Product Governance",
        ),
        _check(
            "DQ13",
            "PD values are bounded",
            customer_360["pd_12m"].between(0, 1).all(),
            "Credit Risk",
        ),
        _check(
            "DQ14",
            "Six-month flow coverage is complete",
            customer_360[["inflow_6m_try", "outflow_6m_try"]].notna().all().all(),
            "Data Office",
        ),
    ]
    frame = pd.DataFrame(checks)
    frame["data_class"] = DERIVED_ANALYTICS
    return frame


def conduct_monitoring(
    opportunities: pd.DataFrame,
    next_best: pd.DataFrame,
) -> pd.DataFrame:
    """Measure selection allocation across operational customer segments."""
    selected = set(next_best.loc[next_best["capacity_allocated_flag"], "candidate_id"])
    frames = []
    for dimension in ["size_band", "region"]:
        working = opportunities.copy()
        working["selected_flag"] = working["candidate_id"].isin(selected)
        summary = working.groupby(dimension, as_index=False).agg(
            candidates=("candidate_id", "count"),
            eligible_candidates=("eligible_flag", "sum"),
            selected_candidates=("selected_flag", "sum"),
            average_score=("opportunity_score", "mean"),
            average_expected_profit_try=("expected_incremental_profit_try", "mean"),
        )
        summary["selection_rate"] = summary["selected_candidates"] / summary["candidates"]
        summary.insert(0, "dimension", dimension)
        summary = summary.rename(columns={dimension: "segment"})
        frames.append(summary)
    result = pd.concat(frames, ignore_index=True)
    result["data_class"] = DERIVED_ANALYTICS
    return result


def management_controls(
    customer_360: pd.DataFrame,
    opportunities: pd.DataFrame,
    next_best: pd.DataFrame,
    rm_performance: pd.DataFrame,
    performance: pd.DataFrame,
    conduct: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Evaluate portfolio, model, conduct and capacity policy limits."""
    assumptions = config["assumptions"]
    model_controls = assumptions["model_controls"]
    champion = performance.loc[performance["selected_champion"]].iloc[0]
    segment_gaps = conduct.groupby("dimension")["selection_rate"].agg(
        lambda values: values.max() - values.min()
    )
    maximum_gap = float(segment_gaps.max())
    overdue_rate = float((customer_360["kyc_overdue_days"] > 0).mean())
    selected = next_best.loc[next_best["capacity_allocated_flag"]]
    rows = [
        _control(
            "CTL01",
            "Champion ROC AUC",
            champion.roc_auc,
            float(model_controls["minimum_auc"]),
            ">=",
            "Model Risk",
        ),
        _control(
            "CTL02",
            "Champion top-decile lift",
            champion.top_decile_lift,
            float(model_controls["minimum_top_decile_lift"]),
            ">=",
            "Model Risk",
        ),
        _control(
            "CTL03",
            "Champion Brier score",
            champion.brier_score,
            float(model_controls["maximum_brier"]),
            "<=",
            "Model Risk",
        ),
        _control(
            "CTL04",
            "Maximum operational-segment selection gap",
            maximum_gap,
            float(model_controls["maximum_segment_selection_gap"]),
            "<=",
            "Conduct Risk",
        ),
        _control("CTL05", "KYC overdue customer rate", overdue_rate, 0.30, "<=", "KYC Operations"),
        _control(
            "CTL06",
            "Suppressed candidates allocated to worklist",
            float((selected["eligible_flag"] == 0).sum()),
            0.0,
            "<=",
            "Product Governance",
        ),
        _control(
            "CTL07",
            "Automated sale decisions",
            float(selected["automated_sale_flag"].sum()),
            0.0,
            "<=",
            "Product Governance",
        ),
        _control(
            "CTL08",
            "Maximum RM capacity utilisation",
            float(rm_performance["capacity_utilisation"].max()),
            1.0,
            "<=",
            "Sales Operations",
        ),
        _control(
            "CTL09",
            "Selected conversations with negative expected profit",
            float((selected["expected_incremental_profit_try"] < 0).sum()),
            0.0,
            "<=",
            "Finance",
        ),
        _control(
            "CTL10",
            "Selected conversations without contact permission",
            float((selected["contact_permission"] == 0).sum()),
            0.0,
            "<=",
            "Privacy Office",
        ),
    ]
    frame = pd.DataFrame(rows)
    frame["data_class"] = DERIVED_ANALYTICS
    return frame


def _check(control_id: str, name: str, passed: bool, owner: str) -> dict[str, object]:
    return {
        "control_id": control_id,
        "control_name": name,
        "status": "PASS" if bool(passed) else "FAIL",
        "owner": owner,
        "remediation": "None" if bool(passed) else "Stop pipeline and remediate source or logic",
    }


def _control(
    control_id: str,
    name: str,
    actual: float,
    threshold: float,
    operator: str,
    owner: str,
) -> dict[str, object]:
    passed = actual >= threshold if operator == ">=" else actual <= threshold
    return {
        "control_id": control_id,
        "control_name": name,
        "actual_value": actual,
        "threshold": threshold,
        "operator": operator,
        "status": "PASS" if passed else "BREACH",
        "owner": owner,
        "management_action": "Monitor"
        if passed
        else "Escalate, investigate and approve remediation",
    }


def _no_held_product_candidate(holdings: pd.DataFrame, candidates: pd.DataFrame) -> bool:
    held = set(zip(holdings["customer_id"], holdings["product_code"], strict=True))
    proposed = set(zip(candidates["customer_id"], candidates["product_code"], strict=True))
    return not bool(held.intersection(proposed))
