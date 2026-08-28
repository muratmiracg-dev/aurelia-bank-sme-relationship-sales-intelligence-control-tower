from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aurelia_sme_sales.config import load_project_config
from aurelia_sme_sales.decisioning import build_opportunities
from aurelia_sme_sales.economics import calculate_product_economics
from aurelia_sme_sales.features import build_customer_360
from aurelia_sme_sales.generator import build_demo_data
from aurelia_sme_sales.propensity import fit_propensity_models, score_candidates


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def base_config(project_root: Path) -> dict:
    return load_project_config(project_root)


@pytest.fixture(scope="session")
def small_config(base_config: dict) -> dict:
    config = copy.deepcopy(base_config)
    config["assumptions"]["observation_months"] = 8
    config["assumptions"]["synthetic_population"] = {
        "customers": 260,
        "relationship_managers": 12,
        "historical_campaigns": 3600,
    }
    return config


@pytest.fixture(scope="session")
def small_data(small_config: dict) -> dict:
    return build_demo_data(small_config, seed=20260821)


@pytest.fixture(scope="session")
def feature_pack(small_data: dict, small_config: dict):
    return build_customer_360(small_data, small_config)


@pytest.fixture(scope="session")
def decision_pack(small_data: dict, small_config: dict, feature_pack):
    _, candidates = feature_pack
    bundle = fit_propensity_models(small_data["campaign_history"], seed=12)
    scored = score_candidates(candidates, bundle)
    economics = calculate_product_economics(scored, small_config)
    decisions = build_opportunities(
        economics,
        small_data["relationship_managers"],
        small_config["products"],
        small_config,
    )
    return economics, decisions


@pytest.fixture(scope="session")
def economics_decision_inputs(small_data: dict, small_config: dict, feature_pack):
    _, candidates = feature_pack
    bundle = fit_propensity_models(small_data["campaign_history"], seed=12)
    scored = score_candidates(candidates, bundle)
    economics = calculate_product_economics(scored, small_config)
    return economics, small_data["relationship_managers"], small_config["products"], small_config
