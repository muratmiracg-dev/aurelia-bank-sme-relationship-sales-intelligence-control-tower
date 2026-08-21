"""Illustrative risk-adjusted product economics and profitability bridge."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .constants import CREDIT_PRODUCTS, DERIVED_ANALYTICS


def calculate_product_economics(
    scored_candidates: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Calculate transparent first-year economics for every product candidate."""
    frame = scored_candidates.copy()
    assumptions = config["assumptions"]
    economics = assumptions["economics"]
    frame["estimated_product_notional_try"] = [_notional(row) for row in frame.itertuples()]
    product_parameters = economics["product_parameters"]
    gross_income = []
    funding_cost = []
    expected_loss = []
    allocated_capital = []
    for row in frame.itertuples():
        parameters = product_parameters[row.product_code]
        notional = float(row.estimated_product_notional_try)
        utilization = float(parameters["utilization"])
        active_exposure = notional * utilization
        gross = active_exposure * float(parameters["annual_revenue_rate"]) + notional * float(
            parameters["fee_rate"]
        )
        if row.product_code == "TERM_DEPOSIT":
            funding = -notional * 0.022
        elif row.product_code in CREDIT_PRODUCTS:
            funding = active_exposure * 0.046
        else:
            funding = active_exposure * 0.003
        loss = (
            active_exposure * float(row.pd_12m) * float(economics["lgd_credit"])
            if row.product_code in CREDIT_PRODUCTS
            else 0.0
        )
        capital = (
            active_exposure
            * float(parameters["capital_factor"])
            * float(economics["capital_ratio_credit"])
        )
        gross_income.append(gross)
        funding_cost.append(funding)
        expected_loss.append(loss)
        allocated_capital.append(capital)
    frame["gross_income_if_activated_try"] = np.round(gross_income, 2)
    frame["funding_cost_if_activated_try"] = np.round(funding_cost, 2)
    frame["expected_loss_if_activated_try"] = np.round(expected_loss, 2)
    frame["allocated_capital_try"] = np.round(allocated_capital, 2)
    frame["capital_charge_if_activated_try"] = np.round(
        frame["allocated_capital_try"] * float(economics["cost_of_capital"]), 2
    )
    frame["servicing_cost_if_activated_try"] = np.round(
        900 + np.minimum(frame["estimated_product_notional_try"] * 0.00015, 85_000), 2
    )
    frame["risk_adjusted_profit_if_activated_try"] = np.round(
        frame["gross_income_if_activated_try"]
        - frame["funding_cost_if_activated_try"]
        - frame["expected_loss_if_activated_try"]
        - frame["capital_charge_if_activated_try"]
        - frame["servicing_cost_if_activated_try"],
        2,
    )
    frame["raroc_if_activated"] = np.where(
        frame["allocated_capital_try"] > 0,
        frame["risk_adjusted_profit_if_activated_try"] / frame["allocated_capital_try"],
        np.nan,
    )
    frame["expected_incremental_profit_try"] = np.round(
        np.maximum(frame["predicted_contact_uplift"], 0)
        * frame["risk_adjusted_profit_if_activated_try"]
        - float(economics["operating_cost_per_contact_try"]),
        2,
    )
    frame["profitability_percentile"] = frame["expected_incremental_profit_try"].rank(
        pct=True, method="average"
    )
    frame["data_class"] = DERIVED_ANALYTICS
    return frame


def _notional(row: object) -> float:
    turnover = float(row.annual_turnover_try)
    product = str(row.product_code)
    mapping = {
        "WORKING_CAPITAL_LOAN": turnover * 0.12,
        "POS_MERCHANT_ACQUIRING": float(row.pos_volume_6m_try) * 2,
        "BUSINESS_CREDIT_CARD": turnover * 0.018,
        "PAYROLL_SERVICES": float(row.payroll_6m_try) * 2,
        "CASH_MANAGEMENT": float(row.outflow_6m_try) * 2,
        "TRADE_FINANCE": float(row.trade_flow_6m_try) * 2,
        "TERM_DEPOSIT": float(row.average_deposit_balance_try) * 0.65,
        "FX_RISK_MANAGEMENT": (float(row.fx_inflow_6m_try) + float(row.fx_outflow_6m_try)) * 2,
    }
    return float(np.clip(mapping[product], 50_000, 250_000_000))
