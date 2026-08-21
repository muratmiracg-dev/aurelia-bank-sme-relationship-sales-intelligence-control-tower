from __future__ import annotations

import copy

import pandas as pd
import pytest
import yaml

from aurelia_sme_sales.config import load_project_config
from aurelia_sme_sales.constants import PRODUCTS
from aurelia_sme_sales.exceptions import ConfigurationError
from aurelia_sme_sales.generator import _product_exposure, build_demo_data


def test_configuration_loads(base_config):
    assert tuple(base_config["assumptions"]["product_codes"]) == PRODUCTS
    assert set(base_config["products"]) == set(PRODUCTS)


def test_missing_configuration_raises(tmp_path):
    with pytest.raises(ConfigurationError, match="Missing configuration"):
        load_project_config(tmp_path)


def test_bad_weight_sum_raises(tmp_path, base_config):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    assumptions = copy.deepcopy(base_config["assumptions"])
    assumptions["score_weights"]["propensity"] = 0.50
    (config_dir / "assumptions.yml").write_text(yaml.safe_dump(assumptions))
    (config_dir / "products.yml").write_text(yaml.safe_dump({"products": base_config["products"]}))
    with pytest.raises(ConfigurationError, match="sum to 1.0"):
        load_project_config(tmp_path)


def test_bad_product_order_raises(tmp_path, base_config):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    assumptions = copy.deepcopy(base_config["assumptions"])
    assumptions["product_codes"] = list(reversed(assumptions["product_codes"]))
    (config_dir / "assumptions.yml").write_text(yaml.safe_dump(assumptions))
    (config_dir / "products.yml").write_text(yaml.safe_dump({"products": base_config["products"]}))
    with pytest.raises(ConfigurationError, match="canonical order"):
        load_project_config(tmp_path)


def test_generator_is_deterministic(small_config):
    first = build_demo_data(small_config, seed=77)
    second = build_demo_data(small_config, seed=77)
    pd.testing.assert_frame_equal(first["customers"], second["customers"])
    pd.testing.assert_frame_equal(first["campaign_history"], second["campaign_history"])


def test_generator_referential_integrity(small_data):
    customers = set(small_data["customers"]["customer_id"])
    assert set(small_data["risk_profile"]["customer_id"]) == customers
    assert set(small_data["monthly_flows"]["customer_id"]) == customers
    assert set(small_data["product_holdings"]["customer_id"]).issubset(customers)
    assert small_data["product_holdings"]["product_code"].isin(PRODUCTS).all()


def test_generator_expected_shapes(small_data, small_config):
    population = small_config["assumptions"]["synthetic_population"]
    assert len(small_data["customers"]) == population["customers"]
    assert len(small_data["relationship_managers"]) == population["relationship_managers"]
    assert len(small_data["campaign_history"]) == population["historical_campaigns"]
    assert len(small_data["monthly_flows"]) == population["customers"] * 8


@pytest.mark.parametrize("product", PRODUCTS)
def test_product_exposure_is_positive(product):
    row = type(
        "Row",
        (),
        {
            "annual_turnover_try": 10_000_000,
            "pos_volume_try": 1_000_000,
            "payroll_estimate_try": 500_000,
            "outflow_try": 2_000_000,
            "trade_flow_try": 750_000,
            "average_deposit_balance_try": 900_000,
            "fx_inflow_try": 300_000,
            "fx_outflow_try": 200_000,
        },
    )()
    import numpy as np

    assert _product_exposure(product, row, np.random.default_rng(4)) > 0
