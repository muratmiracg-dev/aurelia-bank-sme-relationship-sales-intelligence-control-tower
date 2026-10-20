from __future__ import annotations

import numpy as np
import pytest

from aurelia_sme_sales.features import build_customer_360
from aurelia_sme_sales.propensity import fit_propensity_models, score_candidates


def test_customer_360_is_one_row_per_customer(feature_pack, small_data):
    customer_360, _ = feature_pack
    assert len(customer_360) == len(small_data["customers"])
    assert customer_360["customer_id"].is_unique
    assert customer_360["relationship_depth_score"].between(0, 100).all()
    assert customer_360["wallet_share_proxy"].between(0, 1).all()


def test_candidates_exclude_existing_holdings(feature_pack, small_data):
    _, candidates = feature_pack
    held = set(
        zip(
            small_data["product_holdings"]["customer_id"],
            small_data["product_holdings"]["product_code"],
            strict=True,
        )
    )
    proposed = set(zip(candidates["customer_id"], candidates["product_code"], strict=True))
    assert not held.intersection(proposed)
    assert candidates["candidate_id"].is_unique
    assert candidates["need_signal"].between(0, 1).all()


@pytest.mark.parametrize("invalid_date", ["not-a-date", None, "2099-01-01"])
def test_customer_360_rejects_invalid_or_future_interactions(
    small_data, small_config, invalid_date
):
    invalid = {name: frame.copy() for name, frame in small_data.items()}
    invalid["interactions"]["interaction_date"] = invalid["interactions"][
        "interaction_date"
    ].astype(object)
    invalid["interactions"].loc[invalid["interactions"].index[0], "interaction_date"] = invalid_date
    with pytest.raises(ValueError, match="Interaction dates"):
        build_customer_360(invalid, small_config)


def test_temporal_models_produce_valid_metrics(small_data):
    bundle = fit_propensity_models(small_data["campaign_history"], seed=7)
    assert len(bundle.performance) == 2
    assert bundle.performance["roc_auc"].between(0, 1).all()
    assert bundle.performance["brier_score"].between(0, 1).all()
    assert bundle.performance["selected_champion"].sum() == 1
    assert len(bundle.uplift_deciles) == 10
    assert bundle.coefficients["absolute_coefficient"].is_monotonic_decreasing


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("treatment_flag", True, "binary integers"),
        ("activated_flag", "1", "binary integers"),
        ("campaign_date", None, "dates"),
    ],
)
def test_propensity_rejects_ambiguous_contract_values(small_data, column, value, message):
    invalid = small_data["campaign_history"].copy()
    invalid[column] = invalid[column].astype(object)
    invalid.loc[invalid.index[0], column] = value
    with pytest.raises(ValueError, match=message):
        fit_propensity_models(invalid, seed=7)


def test_propensity_requires_both_training_arms(small_data):
    invalid = small_data["campaign_history"].copy()
    ordered_index = invalid.sort_values("campaign_date").index
    cutoff = int(len(invalid) * 0.8)
    invalid.loc[ordered_index[:cutoff], "treatment_flag"] = 1
    with pytest.raises(ValueError, match="treated and control"):
        fit_propensity_models(invalid, seed=7)


def test_scoring_outputs_probability_uplift_and_reasons(feature_pack, small_data):
    _, candidates = feature_pack
    bundle = fit_propensity_models(small_data["campaign_history"], seed=8)
    scored = score_candidates(candidates.head(300), bundle)
    assert scored["propensity_probability"].between(0, 1).all()
    assert scored["predicted_contact_uplift"].between(-0.2, 0.5).all()
    assert scored[["reason_1", "reason_2", "reason_3"]].notna().all().all()
    assert np.isfinite(scored["propensity_probability"]).all()
