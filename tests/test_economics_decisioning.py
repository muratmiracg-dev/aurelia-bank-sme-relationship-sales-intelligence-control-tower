from __future__ import annotations

import copy

import pytest

from aurelia_sme_sales.constants import PRODUCTS
from aurelia_sme_sales.decisioning import _suppression_reasons, build_opportunities
from aurelia_sme_sales.economics import _notional


def test_economics_bridge_ties(decision_pack):
    economics, _ = decision_pack
    calculated = (
        economics["gross_income_if_activated_try"]
        - economics["funding_cost_if_activated_try"]
        - economics["expected_loss_if_activated_try"]
        - economics["capital_charge_if_activated_try"]
        - economics["servicing_cost_if_activated_try"]
    )
    assert (
        calculated.round(2) == economics["risk_adjusted_profit_if_activated_try"].round(2)
    ).all()
    assert (economics["estimated_product_notional_try"] > 0).all()


@pytest.mark.parametrize("product", PRODUCTS)
def test_notional_branch_for_every_product(product):
    row = type(
        "Row",
        (),
        {
            "product_code": product,
            "annual_turnover_try": 25_000_000,
            "pos_volume_6m_try": 4_000_000,
            "payroll_6m_try": 3_000_000,
            "outflow_6m_try": 14_000_000,
            "trade_flow_6m_try": 6_000_000,
            "average_deposit_balance_try": 2_000_000,
            "fx_inflow_6m_try": 3_000_000,
            "fx_outflow_6m_try": 2_000_000,
        },
    )()
    assert 50_000 <= _notional(row) <= 250_000_000


def test_decisioning_never_automates_sale(decision_pack):
    _, decisions = decision_pack
    next_best = decisions["next_best_conversations"]
    assert not next_best["automated_sale_flag"].any()
    assert (next_best["final_decision_owner"] == "AUTHORISED_RELATIONSHIP_MANAGER").all()
    assert decisions["rm_performance"]["capacity_utilisation"].le(1).all()


def test_task_allocation_respects_policy_cap(economics_decision_inputs):
    economics, relationship_managers, products, config = economics_decision_inputs
    relationship_managers = relationship_managers.copy()
    relationship_managers["monthly_contact_capacity"] = 999
    config = copy.deepcopy(config)
    config["assumptions"]["decision_policy"]["max_open_tasks_per_rm"] = 1

    decisions = build_opportunities(economics, relationship_managers, products, config)
    next_best = decisions["next_best_conversations"]
    allocated = next_best.loc[next_best["capacity_allocated_flag"]]

    assert next_best["effective_contact_capacity"].eq(1).all()
    assert allocated.groupby("rm_id").size().le(1).all()
    assert decisions["rm_performance"]["capacity_utilisation"].le(1).all()


def test_sales_funnel_is_monotonic(decision_pack):
    _, decisions = decision_pack
    values = decisions["sales_funnel"].sort_values("stage_order")["expected_count"].to_list()
    assert values == sorted(values, reverse=True)


def test_suppression_reasons_cover_governance_gates(small_config):
    policy = small_config["assumptions"]["decision_policy"]
    row = type(
        "Row",
        (),
        {
            "contact_permission": False,
            "beneficial_owner_complete": False,
            "kyc_overdue_days": 999,
            "aml_alert_priority": "HIGH",
            "product_code": "WORKING_CAPITAL_LOAN",
            "pd_12m": 0.20,
            "days_past_due": 60,
            "financials_fresh_flag": False,
            "need_signal": 0.1,
        },
    )()
    reasons = _suppression_reasons(row, policy)
    assert len(reasons) == 7
    fx_row = copy.copy(row)
    fx_row.contact_permission = True
    fx_row.beneficial_owner_complete = True
    fx_row.kyc_overdue_days = 0
    fx_row.aml_alert_priority = "NONE"
    fx_row.product_code = "FX_RISK_MANAGEMENT"
    assert _suppression_reasons(fx_row, policy) == ["NO_DOCUMENTED_FX_NEED"]
