"""Governed YAML configuration loading and validation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from .constants import PRODUCTS
from .exceptions import ConfigurationError


def load_project_config(root: str | Path) -> dict[str, Any]:
    """Load and validate project configuration from ``root/config``."""
    root = Path(root)
    assumptions = _load_yaml(root / "config" / "assumptions.yml")
    products = _load_yaml(root / "config" / "products.yml")
    configured = tuple(assumptions.get("product_codes", []))
    if configured != PRODUCTS:
        raise ConfigurationError("Configured product_codes must match the canonical order")
    if set(products.get("products", {})) != set(PRODUCTS):
        raise ConfigurationError("products.yml must define every canonical product")
    weights = assumptions.get("score_weights", {})
    expected_weights = {
        "propensity",
        "uplift",
        "need",
        "profitability",
        "relationship_gap",
    }
    if set(weights) != expected_weights:
        raise ConfigurationError("Opportunity score weights must define every scoring component")
    numeric_weights = [float(value) for value in weights.values()]
    if not all(math.isfinite(value) and value >= 0 for value in numeric_weights):
        raise ConfigurationError("Opportunity score weights must be finite and non-negative")
    if abs(sum(numeric_weights) - 1.0) > 1e-9:
        raise ConfigurationError("Opportunity score weights must sum to 1.0")
    if int(assumptions["synthetic_population"]["relationship_managers"]) < 1:
        raise ConfigurationError("At least one relationship manager is required")
    if int(assumptions["decision_policy"]["max_open_tasks_per_rm"]) < 1:
        raise ConfigurationError("max_open_tasks_per_rm must be at least 1")
    policy = assumptions["decision_policy"]
    if not isinstance(policy.get("aml_high_priority_block"), bool):
        raise ConfigurationError("aml_high_priority_block must be a boolean")
    for key in ("minimum_propensity", "minimum_uplift", "high_pd_block"):
        value = policy.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ConfigurationError(f"{key} must be a finite number between 0 and 1")
    priority = [policy.get("minimum_priority_score"), policy.get("high_priority_score")]
    if (
        any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 100
            for value in priority
        )
        or priority[0] > priority[1]
    ):
        raise ConfigurationError(
            "Priority scores must be finite values from 0 to 100 in ascending order"
        )
    return {"assumptions": assumptions, "products": products["products"]}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Missing configuration: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Configuration must be a mapping: {path}")
    return payload
