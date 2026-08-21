"""Static analytical figures for README, PDF and offline review."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

NAVY = "#0B1F33"
TEAL = "#0E7490"
CYAN = "#32B7C7"
AMBER = "#D97706"
RED = "#C2413B"
GREEN = "#15803D"
MUTED = "#64748B"
SOFT = "#E2E8F0"


def create_figures(results: dict[str, pd.DataFrame], output_dir: str | Path) -> list[Path]:
    """Create a compact, consistent management figure set."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})
    paths = [
        _executive_overview(results, output / "executive-overview.png"),
        _product_opportunities(results, output / "product-opportunities.png"),
        _sales_funnel(results, output / "sales-funnel.png"),
        _rm_capacity(results, output / "rm-capacity.png"),
        _profitability(results, output / "risk-adjusted-profitability.png"),
        _model_validation(results, output / "model-validation.png"),
        _conduct_controls(results, output / "conduct-controls.png"),
    ]
    return paths


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _executive_overview(results: dict[str, pd.DataFrame], path: Path) -> Path:
    customers = results["customer_360"]
    next_best = results["next_best_conversations"]
    selected = next_best.loc[next_best["capacity_allocated_flag"]]
    controls = results["management_controls"]
    metrics = [
        ("SME customers", f"{len(customers):,}"),
        ("Prioritised conversations", f"{len(selected):,}"),
        (
            "Expected incremental profit",
            f"TRY {selected['expected_incremental_profit_try'].sum() / 1e6:.1f}m",
        ),
        ("Management breaches", f"{(controls['status'] == 'BREACH').sum()}"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 6.6))
    for axis, (label, value) in zip(axes.flat, metrics, strict=True):
        axis.axis("off")
        axis.text(
            0.5, 0.62, value, ha="center", va="center", fontsize=28, fontweight="bold", color=NAVY
        )
        axis.text(0.5, 0.35, label, ha="center", va="center", fontsize=12, color=MUTED)
        axis.add_patch(
            plt.Rectangle(
                (0.03, 0.08),
                0.94,
                0.84,
                fill=False,
                edgecolor=SOFT,
                linewidth=1.5,
                transform=axis.transAxes,
            )
        )
    fig.suptitle(
        "Aurelia Bank SME Relationship & Sales Intelligence", fontsize=18, color=NAVY, y=1.01
    )
    return _save(fig, path)


def _product_opportunities(results: dict[str, pd.DataFrame], path: Path) -> Path:
    selected = results["next_best_conversations"].loc[
        results["next_best_conversations"]["capacity_allocated_flag"]
    ]
    summary = (
        selected.groupby("product_label", as_index=False)
        .agg(
            conversations=("candidate_id", "count"),
            expected_profit=("expected_incremental_profit_try", "sum"),
        )
        .sort_values("expected_profit")
    )
    fig, axis = plt.subplots(figsize=(11.5, 6.4))
    bars = axis.barh(summary["product_label"], summary["expected_profit"] / 1e6, color=TEAL)
    axis.bar_label(bars, fmt="%.1f", padding=4, fontsize=9)
    axis.set_title(
        "Expected incremental profit is concentrated in high-need conversations",
        loc="left",
        color=NAVY,
    )
    axis.set_xlabel("Expected incremental profit (TRY million)")
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.grid(axis="x", color=SOFT, linewidth=0.8)
    return _save(fig, path)


def _sales_funnel(results: dict[str, pd.DataFrame], path: Path) -> Path:
    funnel = results["sales_funnel"].sort_values("stage_order")
    fig, axis = plt.subplots(figsize=(10.8, 5.8))
    colors = [NAVY, TEAL, CYAN, AMBER, GREEN]
    bars = axis.bar(funnel["funnel_stage"], funnel["expected_count"], color=colors)
    axis.bar_label(bars, fmt="%d", padding=4, fontweight="bold")
    axis.set_title("Capacity-constrained sales funnel", loc="left", color=NAVY)
    axis.set_ylabel("Expected count")
    axis.tick_params(axis="x", rotation=18)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", color=SOFT, linewidth=0.8)
    return _save(fig, path)


def _rm_capacity(results: dict[str, pd.DataFrame], path: Path) -> Path:
    rm = results["rm_performance"].sort_values("capacity_utilisation", ascending=False).head(20)
    fig, axis = plt.subplots(figsize=(11.5, 6.2))
    colors = np.where(rm["capacity_utilisation"] > 0.95, AMBER, TEAL)
    axis.bar(rm["rm_id"], rm["capacity_utilisation"] * 100, color=colors)
    axis.axhline(100, color=RED, linewidth=1.4, linestyle="--", label="Capacity limit")
    axis.set_title("Top relationship-manager capacity utilisation", loc="left", color=NAVY)
    axis.set_ylabel("Capacity utilisation (%)")
    axis.tick_params(axis="x", rotation=45)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False)
    return _save(fig, path)


def _profitability(results: dict[str, pd.DataFrame], path: Path) -> Path:
    frame = results["product_opportunities"].sample(
        min(2500, len(results["product_opportunities"])), random_state=21
    )
    fig, axis = plt.subplots(figsize=(10.8, 6.2))
    selected = frame["recommendation_status"].isin(["HIGH_PRIORITY", "MEDIUM_PRIORITY"])
    axis.scatter(
        frame.loc[~selected, "propensity_probability"],
        frame.loc[~selected, "expected_incremental_profit_try"] / 1000,
        s=11,
        alpha=0.32,
        color=MUTED,
        label="Monitor / suppressed",
    )
    axis.scatter(
        frame.loc[selected, "propensity_probability"],
        frame.loc[selected, "expected_incremental_profit_try"] / 1000,
        s=18,
        alpha=0.62,
        color=TEAL,
        label="Policy-qualified",
    )
    axis.axhline(0, color=RED, linewidth=1)
    axis.set_title(
        "Propensity alone is insufficient: economics changes prioritisation", loc="left", color=NAVY
    )
    axis.set_xlabel("Activation propensity")
    axis.set_ylabel("Expected incremental profit (TRY thousand)")
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False)
    return _save(fig, path)


def _model_validation(results: dict[str, pd.DataFrame], path: Path) -> Path:
    performance = results["model_performance"].copy()
    labels = performance["model"].str.replace("_", " ").str.title()
    x = np.arange(len(performance))
    fig, axis = plt.subplots(figsize=(9.8, 5.6))
    width = 0.22
    axis.bar(x - width, performance["roc_auc"], width, label="ROC AUC", color=NAVY)
    axis.bar(x, performance["pr_auc"], width, label="PR AUC", color=TEAL)
    axis.bar(x + width, performance["brier_score"], width, label="Brier (lower)", color=AMBER)
    axis.set_xticks(x, labels)
    axis.set_ylim(0, 1)
    axis.set_title(
        "Temporal validation balances discrimination and calibration", loc="left", color=NAVY
    )
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, ncol=3)
    axis.grid(axis="y", color=SOFT, linewidth=0.8)
    return _save(fig, path)


def _conduct_controls(results: dict[str, pd.DataFrame], path: Path) -> Path:
    controls = results["management_controls"]
    colors = [GREEN if value == "PASS" else RED for value in controls["status"]]
    fig, axis = plt.subplots(figsize=(11, 6.3))
    axis.barh(
        controls["control_id"] + "  " + controls["control_name"],
        np.ones(len(controls)),
        color=colors,
    )
    axis.set_xlim(0, 1)
    axis.set_xticks([])
    axis.set_title("Management control status", loc="left", color=NAVY)
    axis.spines[:].set_visible(False)
    for index, status in enumerate(controls["status"]):
        axis.text(0.5, index, status, ha="center", va="center", color="white", fontweight="bold")
    return _save(fig, path)
