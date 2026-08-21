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
    coefficients: pd.DataFrame
    split_date: pd.Timestamp


def fit_propensity_models(
    campaign_history: pd.DataFrame,
    seed: int,
) -> PropensityBundle:
    """Fit an interpretable champion, nonlinear challenger and T-learner uplift pair."""
    ordered = campaign_history.sort_values("campaign_date").reset_index(drop=True)
    split_index = int(len(ordered) * 0.80)
    train = ordered.iloc[:split_index].copy()
    test = ordered.iloc[split_index:].copy()
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
    uplift_deciles = _uplift_validation(test, treated_probability - control_probability)
    coefficients = _coefficient_frame(champion)
    return PropensityBundle(
        champion=champion,
        treated_model=treated_model,
        control_model=control_model,
        performance=performance,
        uplift_deciles=uplift_deciles,
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
