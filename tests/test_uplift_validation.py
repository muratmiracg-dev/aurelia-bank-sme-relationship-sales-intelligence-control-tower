"""Qini ranking test and calibration check for the contact-uplift models."""

from __future__ import annotations

import numpy as np
import pytest

from aurelia_sme_sales.propensity import fit_propensity_models, qini_area, uplift_ranking_test


def _randomized_trial(size: int = 4000, seed: int = 3):
    rng = np.random.default_rng(seed)
    true_uplift = rng.uniform(-0.05, 0.35, size)
    treatment = (rng.random(size) < 0.5).astype(int)
    outcome = (rng.random(size) < 0.2 + treatment * true_uplift).astype(int)
    return true_uplift, treatment, outcome


def test_qini_area_hand_example():
    # Ranked: T1 Y1, C Y0, T1 Y0, C Y1.
    # Curve: 1, 1-0*1/1=1, 1-0*2/1=1, 1-1*2/2=0; random line: 0, 0, 0, 0 -> mean 0.75 / 4.
    predicted = np.array([0.4, 0.3, 0.2, 0.1])
    treatment = np.array([1, 0, 1, 0])
    outcome = np.array([1, 0, 0, 1])
    assert qini_area(predicted, treatment, outcome) == pytest.approx(0.75 / 4)


def test_true_uplift_ranks_above_random_and_reverse_below():
    true_uplift, treatment, outcome = _randomized_trial()
    assert qini_area(true_uplift, treatment, outcome) > 0.01
    assert qini_area(-true_uplift, treatment, outcome) < -0.01


def test_informative_ranking_is_significant_and_noise_is_not():
    true_uplift, treatment, outcome = _randomized_trial()
    informative = uplift_ranking_test(true_uplift, treatment, outcome, seed=1, permutations=199)
    assert informative.loc[0, "qini_permutation_p_value"] == pytest.approx(1 / 200)
    noise = np.random.default_rng(9).normal(size=len(true_uplift))
    uninformative = uplift_ranking_test(noise, treatment, outcome, seed=1, permutations=199)
    assert uninformative.loc[0, "qini_permutation_p_value"] > 0.05


def test_calibration_compares_mean_prediction_with_randomized_effect():
    true_uplift, treatment, outcome = _randomized_trial()
    result = uplift_ranking_test(true_uplift * 0.5, treatment, outcome, seed=1, permutations=9)
    row = result.loc[0]
    expected_effect = outcome[treatment == 1].mean() - outcome[treatment == 0].mean()
    assert row["observed_average_uplift"] == pytest.approx(expected_effect)
    assert row["mean_predicted_uplift"] == pytest.approx((true_uplift * 0.5).mean())
    assert row["uplift_calibration_ratio"] == pytest.approx(
        row["mean_predicted_uplift"] / expected_effect
    )
    assert row["treated_observations"] + row["control_observations"] == len(outcome)


@pytest.mark.parametrize(
    ("predicted", "treatment", "outcome", "permutations", "message"),
    [
        ([0.1, 0.2], [1, 0, 1], [1, 0], 9, "aligned"),
        ([0.1, np.nan], [1, 0], [1, 0], 9, "finite"),
        ([0.1, 0.2], [1, 1], [1, 0], 9, "treated and control"),
        ([0.1, 0.2], [1, 0], [2, 0], 9, "binary outcomes"),
        ([0.1, 0.2], [1, 0], [1, 0], 0, "positive integer"),
        ([0.1, 0.2], [1, 0], [1, 0], True, "positive integer"),
    ],
)
def test_uplift_ranking_test_rejects_invalid_inputs(
    predicted, treatment, outcome, permutations, message
):
    with pytest.raises(ValueError, match=message):
        uplift_ranking_test(
            np.array(predicted), np.array(treatment), np.array(outcome), 1, permutations
        )


def test_bundle_reports_uplift_validation(small_data):
    bundle = fit_propensity_models(small_data["campaign_history"], seed=7)
    row = bundle.uplift_validation.iloc[0]
    assert 0 < row["qini_permutation_p_value"] <= 1
    assert row["observations"] == bundle.uplift_deciles["observations"].sum()
    assert row["validation_start"] == bundle.split_date
