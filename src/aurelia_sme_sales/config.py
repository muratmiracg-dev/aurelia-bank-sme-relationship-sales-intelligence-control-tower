"""Governed YAML configuration loading and validation."""

from __future__ import annotations

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
    if abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
        raise ConfigurationError("Opportunity score weights must sum to 1.0")
    if int(assumptions["synthetic_population"]["relationship_managers"]) < 1:
        raise ConfigurationError("At least one relationship manager is required")
    if int(assumptions["decision_policy"]["max_open_tasks_per_rm"]) < 1:
        raise ConfigurationError("max_open_tasks_per_rm must be at least 1")
    return {"assumptions": assumptions, "products": products["products"]}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Missing configuration: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Configuration must be a mapping: {path}")
    return payload
