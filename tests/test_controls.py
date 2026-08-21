from __future__ import annotations

from aurelia_sme_sales.controls import (
    _control,
    conduct_monitoring,
    data_quality_controls,
)


def test_data_quality_controls_pass(small_data, feature_pack):
    customer_360, candidates = feature_pack
    controls = data_quality_controls(small_data, customer_360, candidates)
    assert len(controls) == 14
    assert (controls["status"] == "PASS").all()


def test_data_quality_detects_duplicate_customer(small_data, feature_pack):
    customer_360, candidates = feature_pack
    altered = dict(small_data)
    altered["customers"] = small_data["customers"].copy()
    altered["customers"].loc[1, "customer_id"] = altered["customers"].loc[0, "customer_id"]
    controls = data_quality_controls(altered, customer_360, candidates)
    assert controls.loc[controls["control_id"] == "DQ01", "status"].item() == "FAIL"


def test_conduct_monitoring_has_two_dimensions(decision_pack):
    _, decisions = decision_pack
    conduct = conduct_monitoring(
        decisions["product_opportunities"], decisions["next_best_conversations"]
    )
    assert set(conduct["dimension"]) == {"size_band", "region"}
    assert conduct["selection_rate"].between(0, 1).all()


def test_control_operators():
    assert _control("A", "above", 2, 1, ">=", "Owner")["status"] == "PASS"
    assert _control("B", "below", 2, 1, "<=", "Owner")["status"] == "BREACH"
