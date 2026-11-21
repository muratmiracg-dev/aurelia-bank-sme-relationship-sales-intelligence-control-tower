"""Temporal product-propensity and treatment-uplift modeling."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .constants import DERIVED_ANALYTICS

NUMERIC_FEATURES = [
    "need_signal",
    "digital_engagement_score",
    "relationship_tenure_months",
    "annual_turnover_try",
    "employees",
    "pd_12m",
    "days_past_due",
    "exporter_flag",
    "importer_flag",
]
CATEGORICAL_FEATURES = ["product_code", "size_band", "sector", "region"]


@dataclass
class PropensityBundle:
    """Fitted models and auditable validation outputs."""

    champion: Pipeline
    treated_model: Pipeline
    control_model: Pipeline
    performance: pd.DataFrame
    uplift_deciles: pd.DataFrame
    uplift_validation: pd.DataFrame
    coefficients: pd.DataFrame
    split_date: pd.Timestamp


def fit_propensity_models(
    campaign_history: pd.DataFrame,
    seed: int,
) -> PropensityBundle:
    """Fit an interpretable champion, nonlinear challenger and T-learner uplift pair."""
    required = {
        *NUMERIC_FEATURES,
        *CATEGORICAL_FEATURES,
        "campaign_date",
        "treatment_flag",
        "activated_flag",
    }
    if campaign_history.empty or not required <= set(campaign_history.columns):
        raise ValueError("Campaign history must contain all model fields and observations")
    if campaign_history["campaign_date"].isna().any():
        raise ValueError("Campaign dates must be complete")
    for column in ("treatment_flag", "activated_flag"):
        values = campaign_history[column]
        if (
            values.isna().any()
            or not values.map(
                lambda value: type(value) in (int, np.int64) and value in (0, 1)
            ).all()
        ):
            raise ValueError(f"{column} must contain explicit binary integers")
    ordered = campaign_history.sort_values("campaign_date").reset_index(drop=True)
    split_index = int(len(ordered) * 0.80)
    if split_index == 0 or split_index == len(ordered):
        raise ValueError("Campaign history must provide non-empty train and validation periods")
    train = ordered.iloc[:split_index].copy()
    test = ordered.iloc[split_index:].copy()
    if train["activated_flag"].nunique() < 2 or test["activated_flag"].nunique() < 2:
        raise ValueError("Train and validation periods must contain both activation classes")
    if set(train["treatment_flag"].unique()) != {0, 1}:
        raise ValueError("Training data must contain treated and control observations")
    split_date = pd.Timestamp(test["campaign_date"].min())
    champion_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["treatment_flag"]
    champion = _logistic_pipeline(include_treatment=True, seed=seed)
    champion.fit(train[champion_features], train["activated_flag"])
    challenger = _challenger_pipeline(seed)
    challenger.fit(train[champion_features], train["activated_flag"])
    models = {"LOGISTIC_CHAMPION": champion, "HIST_GRADIENT_CHALLENGER": challenger}
    performance_rows = []
    for name, model in models.items():
        probability = model.predict_proba(test[champion_features])[:, 1]
        performance_rows.append(
            _performance_row(name, test["activated_flag"].to_numpy(), probability)
        )
    performance = pd.DataFrame(performance_rows)
    performance["selected_champion"] = performance["model"] == "LOGISTIC_CHAMPION"
    performance["validation_start"] = split_date
    performance["validation_end"] = pd.Timestamp(test["campaign_date"].max())
    performance["data_class"] = DERIVED_ANALYTICS

    uplift_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    treated_train = train.loc[train["treatment_flag"] == 1]
    control_train = train.loc[train["treatment_flag"] == 0]
    treated_model = _logistic_pipeline(include_treatment=False, seed=seed + 11)
    control_model = _logistic_pipeline(include_treatment=False, seed=seed + 17)
    treated_model.fit(treated_train[uplift_features], treated_train["activated_flag"])
    control_model.fit(control_train[uplift_features], control_train["activated_flag"])
    treated_probability = treated_model.predict_proba(test[uplift_features])[:, 1]
    control_probability = control_model.predict_proba(test[uplift_features])[:, 1]
    predicted_uplift = treated_probability - control_probability
    uplift_deciles = _uplift_validation(test, predicted_uplift)
    uplift_validation = uplift_ranking_test(
        predicted_uplift,
        test["treatment_flag"].to_numpy(),
        test["activated_flag"].to_numpy(),
        seed=seed,
    )
    uplift_validation["validation_start"] = split_date
    uplift_validation["validation_end"] = pd.Timestamp(test["campaign_date"].max())
    coefficients = _coefficient_frame(champion)
    return PropensityBundle(
        champion=champion,
        treated_model=treated_model,
        control_model=control_model,
        performance=performance,
        uplift_deciles=uplift_deciles,
        uplift_validation=uplift_validation,
        coefficients=coefficients,
        split_date=split_date,
    )


def score_candidates(candidates: pd.DataFrame, bundle: PropensityBundle) -> pd.DataFrame:
    """Score current product candidates under contact and no-contact counterfactuals."""
    current = candidates.copy()
    current["treatment_flag"] = 1
    champion_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["treatment_flag"]
    uplift_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    current["propensity_probability"] = bundle.champion.predict_proba(current[champion_features])[
        :, 1
    ]
    treated = bundle.treated_model.predict_proba(current[uplift_features])[:, 1]
    control = bundle.control_model.predict_proba(current[uplift_features])[:, 1]
    current["predicted_contact_uplift"] = np.clip(treated - control, -0.20, 0.50)
    reason_codes = [_reason_codes(row) for row in current.itertuples()]
    current[["reason_1", "reason_2", "reason_3"]] = pd.DataFrame(reason_codes, index=current.index)
    current["data_class"] = DERIVED_ANALYTICS
    return current


def _preprocessor(include_treatment: bool) -> ColumnTransformer:
    numeric = NUMERIC_FEATURES + (["treatment_flag"] if include_treatment else [])
    return ColumnTransformer(
        [
            ("num", StandardScaler(), numeric),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _logistic_pipeline(include_treatment: bool, seed: int) -> Pipeline:
    return Pipeline(
        [
            ("preprocessor", _preprocessor(include_treatment)),
            (
                "classifier",
                LogisticRegression(max_iter=700, C=0.75, random_state=seed),
            ),
        ]
    )


def _challenger_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("preprocessor", _preprocessor(include_treatment=True)),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    learning_rate=0.08,
                    max_iter=180,
                    max_leaf_nodes=18,
                    l2_regularization=0.5,
                    random_state=seed,
                ),
            ),
        ]
    )


def _performance_row(name: str, truth: np.ndarray, probability: np.ndarray) -> dict[str, object]:
    top_count = max(1, int(len(truth) * 0.10))
    top = truth[np.argsort(probability)[-top_count:]]
    base_rate = float(np.mean(truth))
    return {
        "model": name,
        "observations": len(truth),
        "activation_rate": base_rate,
        "roc_auc": float(roc_auc_score(truth, probability)),
        "pr_auc": float(average_precision_score(truth, probability)),
        "brier_score": float(brier_score_loss(truth, probability)),
        "log_loss": float(log_loss(truth, probability)),
        "top_decile_lift": float(np.mean(top) / max(base_rate, 1e-9)),
    }


def _uplift_validation(test: pd.DataFrame, predicted_uplift: np.ndarray) -> pd.DataFrame:
    validation = test[["treatment_flag", "activated_flag"]].copy()
    validation["predicted_uplift"] = predicted_uplift
    validation["rank"] = validation["predicted_uplift"].rank(method="first", ascending=False)
    validation["decile"] = pd.qcut(validation["rank"], 10, labels=False) + 1
    rows = []
    cumulative_incremental = 0.0
    for decile, frame in validation.groupby("decile", sort=True):
        treated = frame.loc[frame["treatment_flag"] == 1, "activated_flag"]
        control = frame.loc[frame["treatment_flag"] == 0, "activated_flag"]
        treated_rate = float(treated.mean()) if len(treated) else 0.0
        control_rate = float(control.mean()) if len(control) else 0.0
        incremental_rate = treated_rate - control_rate
        cumulative_incremental += incremental_rate * len(frame)
        rows.append(
            {
                "uplift_decile": int(decile),
                "observations": len(frame),
                "treated_observations": len(treated),
                "control_observations": len(control),
                "mean_predicted_uplift": float(frame["predicted_uplift"].mean()),
                "treated_activation_rate": treated_rate,
                "control_activation_rate": control_rate,
                "observed_incremental_rate": incremental_rate,
                "cumulative_incremental_activations": cumulative_incremental,
                "data_class": DERIVED_ANALYTICS,
            }
        )
    return pd.DataFrame(rows)


def qini_area(predicted_uplift: np.ndarray, treatment: np.ndarray, outcome: np.ndarray) -> float:
    """Area between the Qini curve and the random-targeting line, per observation.

    Observations are ranked by predicted uplift (ties keep their input order). At each cut-off k
    the Qini curve counts incremental responders ``Y_T(k) - Y_C(k) * N_T(k) / N_C(k)``; random
    targeting reaches ``k / N`` of the full-population value. The mean gap is divided by N, so a
    positive value means the ranking finds more incremental responders than random contact.
    """
    order = np.argsort(-np.asarray(predicted_uplift, dtype=float), kind="mergesort")
    treated = np.asarray(treatment, dtype=float)[order]
    response = np.asarray(outcome, dtype=float)[order]
    treated_count = np.cumsum(treated)
    control_count = np.cumsum(1 - treated)
    treated_response = np.cumsum(response * treated)
    control_response = np.cumsum(response * (1 - treated))
    scaled_control = np.divide(
        control_response * treated_count,
        control_count,
        out=np.zeros_like(control_response),
        where=control_count > 0,
    )
    curve = treated_response - scaled_control
    size = len(curve)
    random_line = curve[-1] * np.arange(1, size + 1) / size
    return float(np.mean(curve - random_line) / size)


def uplift_ranking_test(
    predicted_uplift: np.ndarray,
    treatment: np.ndarray,
    outcome: np.ndarray,
    seed: int,
    permutations: int = 999,
) -> pd.DataFrame:
    """Test the uplift ranking and calibration on randomized hold-out treatment data.

    The p-value is the share of ``permutations`` random re-orderings of the same predictions
    whose Qini area is at least the model's (with the usual +1 correction). Because treatment
    was randomized, the treated-minus-control activation rate is an unbiased estimate of the
    average contact effect, against which the mean predicted uplift is compared.
    """
    predicted = np.asarray(predicted_uplift, dtype=float)
    treated = np.asarray(treatment)
    response = np.asarray(outcome)
    if not (len(predicted) == len(treated) == len(response)) or len(predicted) < 2:
        raise ValueError("Uplift test inputs must be aligned and contain observations")
    if not np.isfinite(predicted).all():
        raise ValueError("Predicted uplift must be finite")
    if set(np.unique(treated)) != {0, 1} or not set(np.unique(response)) <= {0, 1}:
        raise ValueError("Uplift test needs binary outcomes and both treated and control rows")
    if isinstance(permutations, bool) or not isinstance(permutations, int) or permutations < 1:
        raise ValueError("Permutations must be a positive integer")
    observed = qini_area(predicted, treated, response)
    rng = np.random.default_rng(seed)
    exceed = sum(
        qini_area(rng.permutation(predicted), treated, response) >= observed
        for _ in range(permutations)
    )
    observed_effect = float(response[treated == 1].mean() - response[treated == 0].mean())
    mean_predicted = float(predicted.mean())
    return pd.DataFrame(
        [
            {
                "observations": len(predicted),
                "treated_observations": int((treated == 1).sum()),
                "control_observations": int((treated == 0).sum()),
                "qini_area": observed,
                "permutations": permutations,
                "qini_permutation_p_value": (exceed + 1) / (permutations + 1),
                "observed_average_uplift": observed_effect,
                "mean_predicted_uplift": mean_predicted,
                "uplift_calibration_ratio": (
                    mean_predicted / observed_effect if observed_effect else float("nan")
                ),
                "data_class": DERIVED_ANALYTICS,
            }
        ]
    )


def _coefficient_frame(model: Pipeline) -> pd.DataFrame:
    names = model.named_steps["preprocessor"].get_feature_names_out()
    values = model.named_steps["classifier"].coef_[0]
    frame = pd.DataFrame({"feature": names, "coefficient": values})
    frame["absolute_coefficient"] = frame["coefficient"].abs()
    frame["direction"] = np.where(frame["coefficient"] >= 0, "POSITIVE", "NEGATIVE")
    frame["data_class"] = DERIVED_ANALYTICS
    return frame.sort_values("absolute_coefficient", ascending=False).reset_index(drop=True)


def _reason_codes(row: object) -> tuple[str, str, str]:
    candidates = [
        (float(row.need_signal), "STRONG_PRODUCT_NEED_SIGNAL"),
        (float(row.digital_engagement_score) / 100, "HIGH_DIGITAL_ENGAGEMENT"),
        (
            min(float(row.relationship_tenure_months) / 84, 1),
            "ESTABLISHED_RELATIONSHIP",
        ),
        (
            min(np.log1p(float(row.annual_turnover_try)) / 22, 1),
            "MATERIAL_BUSINESS_SCALE",
        ),
        (1 - min(float(row.pd_12m) / 0.20, 1), "LOWER_CREDIT_RISK_SIGNAL"),
        (
            float(bool(row.exporter_flag or row.importer_flag)),
            "CROSS_BORDER_ACTIVITY",
        ),
    ]
    ordered = sorted(candidates, key=lambda item: item[0], reverse=True)
    return tuple(item[1] for item in ordered[:3])
