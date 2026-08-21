"""Typer command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .pipeline import run_pipeline

app = typer.Typer(help="Aurelia Bank SME relationship-sales decision support")
ROOT_OPTION = typer.Option(
    None,
    "--root",
    exists=True,
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
)


@app.command()
def demo(root: Path | None = ROOT_OPTION, seed: int = 20260821) -> None:
    """Run the deterministic end-to-end demo."""
    summary = run_pipeline(root or Path.cwd(), seed=seed)
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def summary(root: Path | None = ROOT_OPTION) -> None:
    """Print the latest executive summary."""
    path = (root or Path.cwd()) / "artifacts" / "results" / "executive_summary.json"
    if not path.exists():
        raise typer.BadParameter("Run `aurelia-sme-sales demo` first")
    typer.echo(path.read_text(encoding="utf-8"))
