"""Customer 360, relationship-depth and product-need feature engineering."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .constants import DERIVED_ANALYTICS, PRODUCTS


def build_customer_360(
    data: dict[str, pd.DataFrame],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create one governed customer view and one eligible product-candidate view."""
    assumptions = config["assumptions"]
    as_of = pd.Timestamp(assumptions["as_of_date"])
    flows = data["monthly_flows"].copy()
    latest_6 = flows.sort_values("month_end").groupby("customer_id", as_index=False).tail(6)
    aggregates = latest_6.groupby("customer_id", as_index=False).agg(
        inflow_6m_try=("inflow_try", "sum"),
        outflow_6m_try=("outflow_try", "sum"),
        pos_volume_6m_try=("pos_volume_try", "sum"),
        payroll_6m_try=("payroll_estimate_try", "sum"),
        fx_inflow_6m_try=("fx_inflow_try", "sum"),
        fx_outflow_6m_try=("fx_outflow_try", "sum"),
        trade_flow_6m_try=("trade_flow_try", "sum"),
        average_deposit_balance_try=("average_deposit_balance_try", "mean"),
        average_loan_balance_try=("average_loan_balance_try", "mean"),
        digital_transaction_count_6m=("digital_transaction_count", "sum"),
    )
    holdings = data["product_holdings"]
    holding_summary = holdings.groupby("customer_id", as_index=False).agg(
        products_held=("product_code", "nunique"),
        bank_exposure_try=("exposure_try", "sum"),
        relationship_income_try=("annual_gross_income_try", "sum"),
    )
    holding_list = (
        holdings.sort_values(["customer_id", "product_code"])
        .groupby("customer_id")["product_code"]
        .agg("|".join)
        .rename("products_held_list")
        .reset_index()
    )
    interactions = (
        data["interactions"]
        .groupby("customer_id", as_index=False)
        .agg(
            last_interaction_date=("interaction_date", "max"),
            interactions_12m=("interaction_id", "count"),
        )
    )
    customer_360 = (
        data["customers"]
        .merge(
            data["risk_profile"], on="customer_id", validate="one_to_one", suffixes=("", "_risk")
        )
        .merge(aggregates, on="customer_id", validate="one_to_one")
        .merge(holding_summary, on="customer_id", how="left", validate="one_to_one")
        .merge(holding_list, on="customer_id", how="left", validate="one_to_one")
        .merge(interactions, on="customer_id", how="left", validate="one_to_one")
    )
    customer_360["products_held"] = customer_360["products_held"].fillna(0).astype(int)
    for column in ["bank_exposure_try", "relationship_income_try", "interactions_12m"]:
        customer_360[column] = customer_360[column].fillna(0)
    customer_360["products_held_list"] = customer_360["products_held_list"].fillna("")
    customer_360["days_since_interaction"] = (
        (as_of - pd.to_datetime(customer_360["last_interaction_date"]))
        .dt.days.fillna(999)
        .astype(int)
    )
    customer_360["relationship_depth_score"] = np.clip(
        100
        * (
            0.52 * customer_360["products_held"] / len(PRODUCTS)
            + 0.28
            * np.minimum(
                customer_360["bank_exposure_try"]
                / np.maximum(customer_360["annual_turnover_try"], 1),
                1,
            )
            + 0.20 * np.minimum(customer_360["relationship_tenure_months"] / 84, 1)
        ),
        0,
        100,
    ).round(2)
    customer_360["wallet_share_proxy"] = np.clip(
        customer_360["bank_exposure_try"]
        / np.maximum(customer_360["annual_turnover_try"] * 0.35, 1),
        0,
        1,
    ).round(6)
    customer_360["kyc_overdue_days"] = np.maximum(
        (as_of - pd.to_datetime(customer_360["kyc_review_due_date"])).dt.days,
        0,
    )
    customer_360["data_class"] = DERIVED_ANALYTICS
    candidates = _build_candidates(customer_360, holdings)
    return customer_360, candidates


def _build_candidates(customer_360: pd.DataFrame, holdings: pd.DataFrame) -> pd.DataFrame:
    held = set(zip(holdings["customer_id"], holdings["product_code"], strict=True))
    rows: list[pd.DataFrame] = []
    for product in PRODUCTS:
        frame = customer_360.loc[
            ~customer_360["customer_id"].map(
                lambda customer, current_product=product: (customer, current_product) in held
            )
        ].copy()
        frame["product_code"] = product
        frame["need_signal"] = _need_signal(frame, product)
        frame["relationship_gap"] = np.clip(1 - frame["products_held"] / len(PRODUCTS), 0, 1)
        rows.append(frame)
    candidates = pd.concat(rows, ignore_index=True)
    candidates.insert(0, "candidate_id", [f"OPP{i:07d}" for i in range(1, len(candidates) + 1)])
    keep = [
        "candidate_id",
        "customer_id",
        "rm_id",
        "product_code",
        "need_signal",
        "relationship_gap",
        "wallet_share_proxy",
        "digital_engagement_score",
        "relationship_tenure_months",
        "annual_turnover_try",
        "employees",
        "pd_12m",
        "days_past_due",
        "kyc_overdue_days",
        "aml_alert_priority",
        "beneficial_owner_complete",
        "financials_fresh_flag",
        "contact_permission",
        "exporter_flag",
        "importer_flag",
        "size_band",
        "sector",
        "region",
        "inflow_6m_try",
        "outflow_6m_try",
        "pos_volume_6m_try",
        "payroll_6m_try",
        "fx_inflow_6m_try",
        "fx_outflow_6m_try",
        "trade_flow_6m_try",
        "average_deposit_balance_try",
        "average_loan_balance_try",
        "days_since_interaction",
    ]
    result = candidates[keep].copy()
    result["data_class"] = DERIVED_ANALYTICS
    return result


def _need_signal(frame: pd.DataFrame, product: str) -> np.ndarray:
    turnover = _scale_log(frame["annual_turnover_try"])
    digital = frame["digital_engagement_score"].to_numpy() / 100
    inflow = np.maximum(frame["inflow_6m_try"].to_numpy(), 1)
    outflow = np.maximum(frame["outflow_6m_try"].to_numpy(), 1)
    pos = np.clip(frame["pos_volume_6m_try"].to_numpy() / inflow, 0, 1)
    payroll = np.clip(frame["payroll_6m_try"].to_numpy() / outflow, 0, 1)
    trade = np.clip(frame["trade_flow_6m_try"].to_numpy() / inflow, 0, 1)
    fx = np.clip(
        (frame["fx_inflow_6m_try"].to_numpy() + frame["fx_outflow_6m_try"].to_numpy())
        / (inflow + outflow),
        0,
        1,
    )
    deposit = np.clip(frame["average_deposit_balance_try"].to_numpy() / (inflow / 6), 0, 1)
    loan = np.clip(frame["average_loan_balance_try"].to_numpy() / (outflow / 6), 0, 1)
    employee = np.clip(frame["employees"].to_numpy() / 200, 0, 1)
    liquidity_gap = np.clip((outflow - inflow) / np.maximum(outflow, 1), 0, 1)
    formulas = {
        "WORKING_CAPITAL_LOAN": 0.38 * liquidity_gap
        + 0.28 * loan
        + 0.22 * turnover
        + 0.12 * (1 - frame["pd_12m"].to_numpy()),
        "POS_MERCHANT_ACQUIRING": 0.66 * pos + 0.20 * digital + 0.14 * turnover,
        "BUSINESS_CREDIT_CARD": 0.42 * digital + 0.28 * turnover + 0.18 * employee + 0.12 * loan,
        "PAYROLL_SERVICES": 0.60 * payroll + 0.25 * employee + 0.15 * turnover,
        "CASH_MANAGEMENT": 0.46 * digital
        + 0.34 * turnover
        + 0.20 * np.minimum((inflow + outflow) / 2e8, 1),
        "TRADE_FINANCE": 0.45 * trade
        + 0.30 * fx
        + 0.15 * np.maximum(frame["exporter_flag"], frame["importer_flag"])
        + 0.10 * turnover,
        "TERM_DEPOSIT": 0.62 * deposit + 0.22 * turnover + 0.16 * (1 - liquidity_gap),
        "FX_RISK_MANAGEMENT": 0.68 * fx
        + 0.20 * np.maximum(frame["exporter_flag"], frame["importer_flag"])
        + 0.12 * turnover,
    }
    return np.clip(formulas[product], 0, 1).round(6)


def _scale_log(series: pd.Series) -> np.ndarray:
    values = np.log1p(series.to_numpy())
    low, high = np.quantile(values, [0.02, 0.98])
    return np.clip((values - low) / max(high - low, 1e-9), 0, 1)
