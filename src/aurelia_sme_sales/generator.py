"""Deterministic synthetic SME relationship-banking data.

No real customer, employee, bank relationship, credit decision or campaign record is used.
The generator intentionally creates realistic commercial signals and governance exceptions so
the analytical controls can be demonstrated without claiming production representativeness.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .constants import CONTROLLED_SYNTHETIC, PRODUCTS

SECTORS = (
    "Manufacturing",
    "Wholesale Trade",
    "Retail Trade",
    "Construction",
    "Transportation",
    "Professional Services",
    "Hospitality",
    "Technology",
    "Agriculture",
    "Healthcare",
)
REGIONS = ("Marmara", "Central Anatolia", "Aegean", "Mediterranean", "Black Sea", "Eastern")


def build_demo_data(config: dict[str, Any], seed: int = 20260821) -> dict[str, pd.DataFrame]:
    """Build all controlled synthetic source tables."""
    assumptions = config["assumptions"]
    population = assumptions["synthetic_population"]
    as_of = pd.Timestamp(assumptions["as_of_date"])
    rng = np.random.default_rng(seed)
    rms = _build_relationship_managers(int(population["relationship_managers"]), rng)
    customers = _build_customers(int(population["customers"]), rms, as_of, rng)
    risk = _build_risk_profile(customers, as_of, rng)
    flows = _build_monthly_flows(
        customers,
        int(assumptions["observation_months"]),
        as_of,
        rng,
    )
    holdings = _build_product_holdings(customers, risk, flows, as_of, rng)
    interactions = _build_interactions(customers, as_of, rng)
    campaigns = _build_campaign_history(
        customers,
        risk,
        flows,
        holdings,
        int(population["historical_campaigns"]),
        as_of,
        rng,
    )
    return {
        "relationship_managers": rms,
        "customers": customers,
        "risk_profile": risk,
        "monthly_flows": flows,
        "product_holdings": holdings,
        "interactions": interactions,
        "campaign_history": campaigns,
    }


def _build_relationship_managers(count: int, rng: np.random.Generator) -> pd.DataFrame:
    rm_ids = [f"RM{i:03d}" for i in range(1, count + 1)]
    regions = np.resize(np.array(REGIONS), count)
    rng.shuffle(regions)
    return pd.DataFrame(
        {
            "rm_id": rm_ids,
            "rm_label": [f"Relationship Manager {i:03d}" for i in range(1, count + 1)],
            "region": regions,
            "seniority": rng.choice(
                ["Associate", "Manager", "Senior Manager"], count, p=[0.34, 0.46, 0.20]
            ),
            "monthly_contact_capacity": rng.integers(46, 71, count),
            "annual_target_try": rng.integers(8_000_000, 15_000_001, count),
            "data_class": CONTROLLED_SYNTHETIC,
        }
    )


def _build_customers(
    count: int,
    rms: pd.DataFrame,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    customer_ids = [f"SME{i:06d}" for i in range(1, count + 1)]
    size_band = rng.choice(["MICRO", "SMALL", "MEDIUM"], count, p=[0.48, 0.38, 0.14])
    scale = np.select(
        [size_band == "MICRO", size_band == "SMALL"],
        [rng.lognormal(16.0, 0.65, count), rng.lognormal(17.2, 0.62, count)],
        default=rng.lognormal(18.5, 0.60, count),
    )
    annual_turnover = np.clip(scale, 1_000_000, 1_500_000_000)
    employee_base = np.select(
        [size_band == "MICRO", size_band == "SMALL"],
        [rng.integers(2, 10, count), rng.integers(10, 50, count)],
        default=rng.integers(50, 250, count),
    )
    sector = rng.choice(SECTORS, count)
    region = rng.choice(REGIONS, count, p=[0.34, 0.18, 0.16, 0.13, 0.11, 0.08])
    rm_by_region = {
        key: group["rm_id"].to_numpy() for key, group in rms.groupby("region", sort=False)
    }
    rm_id = [rng.choice(rm_by_region.get(item, rms["rm_id"].to_numpy())) for item in region]
    onboarding_days = rng.integers(120, 4200, count)
    return pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_label": [f"Synthetic SME {i:06d}" for i in range(1, count + 1)],
            "rm_id": rm_id,
            "region": region,
            "sector": sector,
            "size_band": size_band,
            "legal_form": rng.choice(
                ["LIMITED", "JOINT_STOCK", "SOLE_PROPRIETOR"], count, p=[0.58, 0.22, 0.20]
            ),
            "onboarding_date": as_of - pd.to_timedelta(onboarding_days, unit="D"),
            "relationship_tenure_months": np.floor(onboarding_days / 30.4375).astype(int),
            "annual_turnover_try": annual_turnover.round(2),
            "employees": employee_base,
            "exporter_flag": rng.random(count) < np.where(size_band == "MEDIUM", 0.48, 0.20),
            "importer_flag": rng.random(count) < np.where(size_band == "MEDIUM", 0.44, 0.18),
            "digital_engagement_score": np.clip(rng.beta(3.2, 2.0, count) * 100, 2, 100).round(2),
            "contact_permission": rng.random(count) > 0.055,
            "preferred_channel": rng.choice(
                ["RM_CALL", "VIDEO_MEETING", "BRANCH", "SECURE_MESSAGE"],
                count,
                p=[0.43, 0.20, 0.22, 0.15],
            ),
            "data_class": CONTROLLED_SYNTHETIC,
        }
    )


def _build_risk_profile(
    customers: pd.DataFrame,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    count = len(customers)
    size_adj = customers["size_band"].map({"MICRO": 0.018, "SMALL": 0.006, "MEDIUM": -0.004})
    sector_adj = (
        customers["sector"]
        .map({"Construction": 0.020, "Hospitality": 0.015, "Agriculture": 0.010})
        .fillna(0)
    )
    pd_12m = np.clip(rng.beta(1.7, 19.0, count) * 0.30 + size_adj + sector_adj, 0.002, 0.28)
    days_past_due = rng.choice(
        [0, 5, 15, 30, 60, 90], count, p=[0.81, 0.07, 0.05, 0.035, 0.02, 0.015]
    )
    aml_priority = rng.choice(
        ["NONE", "LOW", "MEDIUM", "HIGH"], count, p=[0.89, 0.06, 0.035, 0.015]
    )
    kyc_offset = rng.integers(-260, 420, count)
    rating_number = np.clip(np.ceil(pd_12m * 44).astype(int) + 1, 1, 10)
    return pd.DataFrame(
        {
            "customer_id": customers["customer_id"],
            "pd_12m": pd_12m.round(6),
            "internal_rating": [f"R{value:02d}" for value in rating_number],
            "days_past_due": days_past_due,
            "stage": np.where(days_past_due >= 90, 3, np.where(days_past_due >= 30, 2, 1)),
            "kyc_review_due_date": as_of + pd.to_timedelta(kyc_offset, unit="D"),
            "aml_alert_priority": aml_priority,
            "beneficial_owner_complete": rng.random(count) > 0.035,
            "financials_fresh_flag": rng.random(count) > 0.13,
            "data_class": CONTROLLED_SYNTHETIC,
        }
    )


def _build_monthly_flows(
    customers: pd.DataFrame,
    months: int,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    month_ends = pd.date_range(
        end=as_of.to_period("M").end_time.normalize(), periods=months, freq="ME"
    )
    frames: list[pd.DataFrame] = []
    sector_pos = customers["sector"].isin(["Retail Trade", "Hospitality", "Healthcare"]).to_numpy()
    exporter = customers["exporter_flag"].to_numpy()
    importer = customers["importer_flag"].to_numpy()
    employee = customers["employees"].to_numpy()
    base_monthly = customers["annual_turnover_try"].to_numpy() / 12
    for index, month in enumerate(month_ends):
        seasonality = 1.0 + 0.10 * np.sin((index + 1) * np.pi / 6)
        total_in = np.clip(
            base_monthly * seasonality * rng.lognormal(0, 0.18, len(customers)), 10_000, None
        )
        total_out = total_in * rng.uniform(0.72, 1.05, len(customers))
        pos_volume = total_in * np.where(
            sector_pos,
            rng.uniform(0.28, 0.72, len(customers)),
            rng.uniform(0.0, 0.10, len(customers)),
        )
        payroll = employee * rng.uniform(22_000, 48_000, len(customers))
        fx_in = total_in * exporter * rng.uniform(0.08, 0.46, len(customers))
        fx_out = total_out * importer * rng.uniform(0.08, 0.44, len(customers))
        trade = (fx_in + fx_out) * rng.uniform(0.30, 0.80, len(customers))
        frame = pd.DataFrame(
            {
                "month_end": month,
                "customer_id": customers["customer_id"],
                "inflow_try": total_in.round(2),
                "outflow_try": total_out.round(2),
                "pos_volume_try": pos_volume.round(2),
                "payroll_estimate_try": payroll.round(2),
                "fx_inflow_try": fx_in.round(2),
                "fx_outflow_try": fx_out.round(2),
                "trade_flow_try": trade.round(2),
                "average_deposit_balance_try": (
                    total_in * rng.uniform(0.08, 0.36, len(customers))
                ).round(2),
                "average_loan_balance_try": (
                    base_monthly * rng.uniform(0.10, 1.15, len(customers))
                ).round(2),
                "digital_transaction_count": np.maximum(
                    1,
                    (
                        customers["digital_engagement_score"].to_numpy()
                        * rng.uniform(0.8, 2.3, len(customers))
                    ).astype(int),
                ),
                "data_class": CONTROLLED_SYNTHETIC,
            }
        )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def _build_product_holdings(
    customers: pd.DataFrame,
    risk: pd.DataFrame,
    flows: pd.DataFrame,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    latest = flows.sort_values("month_end").groupby("customer_id", as_index=False).tail(3)
    recent = latest.groupby("customer_id", as_index=False).mean(numeric_only=True)
    base = customers.merge(risk[["customer_id", "pd_12m"]], on="customer_id").merge(
        recent, on="customer_id"
    )
    need = _need_matrix(base)
    rows: list[dict[str, object]] = []
    for product in PRODUCTS:
        probability = np.clip(
            0.10 + 0.48 * need[product] + rng.normal(0, 0.06, len(base)), 0.04, 0.78
        )
        held = rng.random(len(base)) < probability
        for row in base.loc[held].itertuples():
            exposure = _product_exposure(product, row, rng)
            rows.append(
                {
                    "holding_id": f"H{len(rows) + 1:07d}",
                    "customer_id": row.customer_id,
                    "product_code": product,
                    "opened_date": as_of - pd.to_timedelta(int(rng.integers(90, 2400)), unit="D"),
                    "exposure_try": round(exposure, 2),
                    "annual_gross_income_try": round(exposure * rng.uniform(0.004, 0.055), 2),
                    "active_flag": True,
                    "data_class": CONTROLLED_SYNTHETIC,
                }
            )
    return pd.DataFrame(rows)


def _build_interactions(
    customers: pd.DataFrame,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    counts = rng.integers(1, 7, len(customers))
    rows: list[dict[str, object]] = []
    for customer, rm_id, count in zip(
        customers["customer_id"], customers["rm_id"], counts, strict=True
    ):
        for _ in range(int(count)):
            days_ago = int(rng.integers(1, 365))
            rows.append(
                {
                    "interaction_id": f"I{len(rows) + 1:07d}",
                    "customer_id": customer,
                    "rm_id": rm_id,
                    "interaction_date": as_of - pd.to_timedelta(days_ago, unit="D"),
                    "channel": rng.choice(["CALL", "MEETING", "SECURE_MESSAGE", "BRANCH"]),
                    "outcome": rng.choice(
                        ["CONNECTED", "FOLLOW_UP", "NO_RESPONSE", "NEEDS_REVIEW"],
                        p=[0.43, 0.27, 0.20, 0.10],
                    ),
                    "data_class": CONTROLLED_SYNTHETIC,
                }
            )
    return pd.DataFrame(rows)


def _build_campaign_history(
    customers: pd.DataFrame,
    risk: pd.DataFrame,
    flows: pd.DataFrame,
    holdings: pd.DataFrame,
    count: int,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    recent = flows.sort_values("month_end").groupby("customer_id", as_index=False).tail(6)
    features = recent.groupby("customer_id", as_index=False).mean(numeric_only=True)
    base = customers.merge(risk, on="customer_id").merge(features, on="customer_id")
    held = set(zip(holdings["customer_id"], holdings["product_code"], strict=True))
    indices = rng.integers(0, len(base), count)
    products = rng.choice(PRODUCTS, count)
    sampled = base.iloc[indices].reset_index(drop=True)
    raw_need = _need_for_rows(sampled, products)
    treatment = rng.random(count) < 0.56
    relationship = np.clip(sampled["relationship_tenure_months"].to_numpy() / 72, 0, 1)
    digital = sampled["digital_engagement_score"].to_numpy() / 100
    risk_penalty = sampled["pd_12m"].to_numpy() * 4.5
    product_gap = np.array(
        [
            0 if (cid, product) in held else 1
            for cid, product in zip(sampled["customer_id"], products, strict=True)
        ]
    )
    heterogeneous_uplift = 0.24 * raw_need + 0.10 * digital + 0.05 * relationship
    logit = (
        -4.05
        + 3.65 * raw_need
        + 0.90 * digital
        + 0.62 * relationship
        - 1.15 * risk_penalty
        + 0.32 * product_gap
    )
    probability = 1 / (1 + np.exp(-(logit + treatment * heterogeneous_uplift)))
    activated = rng.random(count) < probability
    dates = as_of - pd.to_timedelta(rng.integers(15, 500, count), unit="D")
    order = np.argsort(dates.to_numpy())
    frame = pd.DataFrame(
        {
            "campaign_id": [f"CMP{i:07d}" for i in range(1, count + 1)],
            "campaign_date": dates,
            "customer_id": sampled["customer_id"],
            "product_code": products,
            "treatment_flag": treatment.astype(int),
            "activated_flag": activated.astype(int),
            "need_signal": raw_need.round(6),
            "digital_engagement_score": sampled["digital_engagement_score"].to_numpy(),
            "relationship_tenure_months": sampled["relationship_tenure_months"].to_numpy(),
            "annual_turnover_try": sampled["annual_turnover_try"].to_numpy(),
            "employees": sampled["employees"].to_numpy(),
            "pd_12m": sampled["pd_12m"].to_numpy(),
            "days_past_due": sampled["days_past_due"].to_numpy(),
            "exporter_flag": sampled["exporter_flag"].astype(int).to_numpy(),
            "importer_flag": sampled["importer_flag"].astype(int).to_numpy(),
            "size_band": sampled["size_band"].to_numpy(),
            "sector": sampled["sector"].to_numpy(),
            "region": sampled["region"].to_numpy(),
            "realized_first_year_margin_try": np.where(
                activated,
                np.maximum(
                    2500,
                    sampled["annual_turnover_try"].to_numpy() * rng.uniform(0.0003, 0.0025, count),
                ),
                0,
            ).round(2),
            "data_class": CONTROLLED_SYNTHETIC,
        }
    )
    return frame.iloc[order].reset_index(drop=True)


def _need_matrix(base: pd.DataFrame) -> dict[str, np.ndarray]:
    turnover = np.log1p(base["annual_turnover_try"].to_numpy())
    turnover = (turnover - turnover.min()) / max(turnover.max() - turnover.min(), 1e-9)
    pos_share = base["pos_volume_try"].to_numpy() / np.maximum(base["inflow_try"].to_numpy(), 1)
    payroll_share = base["payroll_estimate_try"].to_numpy() / np.maximum(
        base["outflow_try"].to_numpy(), 1
    )
    fx_share = (base["fx_inflow_try"].to_numpy() + base["fx_outflow_try"].to_numpy()) / np.maximum(
        base["inflow_try"].to_numpy() + base["outflow_try"].to_numpy(), 1
    )
    trade_share = base["trade_flow_try"].to_numpy() / np.maximum(base["inflow_try"].to_numpy(), 1)
    deposit_share = base["average_deposit_balance_try"].to_numpy() / np.maximum(
        base["inflow_try"].to_numpy(), 1
    )
    loan_share = base["average_loan_balance_try"].to_numpy() / np.maximum(
        base["inflow_try"].to_numpy(), 1
    )
    digital = base["digital_engagement_score"].to_numpy() / 100
    return {
        "WORKING_CAPITAL_LOAN": np.clip(
            0.55 * loan_share
            + 0.25 * turnover
            + 0.20 * (base["outflow_try"].to_numpy() > base["inflow_try"].to_numpy()),
            0,
            1,
        ),
        "POS_MERCHANT_ACQUIRING": np.clip(0.72 * pos_share + 0.28 * digital, 0, 1),
        "BUSINESS_CREDIT_CARD": np.clip(0.48 * digital + 0.32 * turnover + 0.20 * loan_share, 0, 1),
        "PAYROLL_SERVICES": np.clip(0.68 * payroll_share + 0.32 * turnover, 0, 1),
        "CASH_MANAGEMENT": np.clip(0.55 * digital + 0.45 * turnover, 0, 1),
        "TRADE_FINANCE": np.clip(0.60 * trade_share + 0.30 * fx_share + 0.10 * turnover, 0, 1),
        "TERM_DEPOSIT": np.clip(0.72 * deposit_share + 0.28 * turnover, 0, 1),
        "FX_RISK_MANAGEMENT": np.clip(0.82 * fx_share + 0.18 * turnover, 0, 1),
    }


def _need_for_rows(frame: pd.DataFrame, products: np.ndarray) -> np.ndarray:
    # Historical campaign rows contain the same direct drivers used by the current feature layer.
    turnover = np.clip((np.log1p(frame["annual_turnover_try"].to_numpy()) - 14) / 7, 0, 1)
    employee = np.clip(frame["employees"].to_numpy() / 200, 0, 1)
    exporter = frame["exporter_flag"].astype(float).to_numpy()
    importer = frame["importer_flag"].astype(float).to_numpy()
    digital = frame["digital_engagement_score"].to_numpy() / 100
    mapping = {
        "WORKING_CAPITAL_LOAN": 0.55 * turnover + 0.20 * employee + 0.25,
        "POS_MERCHANT_ACQUIRING": 0.45 * digital + 0.35 * turnover + 0.20,
        "BUSINESS_CREDIT_CARD": 0.55 * digital + 0.25 * turnover + 0.20,
        "PAYROLL_SERVICES": 0.60 * employee + 0.25 * turnover + 0.15,
        "CASH_MANAGEMENT": 0.58 * digital + 0.32 * turnover + 0.10,
        "TRADE_FINANCE": 0.45 * np.maximum(exporter, importer) + 0.35 * turnover + 0.20,
        "TERM_DEPOSIT": 0.55 * turnover + 0.20 * digital + 0.25,
        "FX_RISK_MANAGEMENT": 0.60 * np.maximum(exporter, importer) + 0.25 * turnover + 0.15,
    }
    return np.clip(np.array([mapping[item][index] for index, item in enumerate(products)]), 0, 1)


def _product_exposure(product: str, row: object, rng: np.random.Generator) -> float:
    turnover = float(row.annual_turnover_try)
    if product == "WORKING_CAPITAL_LOAN":
        return turnover * rng.uniform(0.05, 0.28)
    if product == "POS_MERCHANT_ACQUIRING":
        return float(row.pos_volume_try) * 12
    if product == "BUSINESS_CREDIT_CARD":
        return turnover * rng.uniform(0.005, 0.035)
    if product == "PAYROLL_SERVICES":
        return float(row.payroll_estimate_try) * 12
    if product == "CASH_MANAGEMENT":
        return float(row.outflow_try) * 12
    if product == "TRADE_FINANCE":
        return float(row.trade_flow_try) * 12
    if product == "TERM_DEPOSIT":
        return float(row.average_deposit_balance_try)
    return (float(row.fx_inflow_try) + float(row.fx_outflow_try)) * 12
