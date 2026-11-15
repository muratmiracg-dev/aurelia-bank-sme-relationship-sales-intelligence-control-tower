from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3

import pytest
import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from aurelia_sme_sales.api import create_app
from aurelia_sme_sales.cli import app as cli_app
from aurelia_sme_sales.pipeline import run_pipeline


def _prepare_root(tmp_path, small_config, project_root):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/assumptions.yml").write_text(
        yaml.safe_dump(small_config["assumptions"]), encoding="utf-8"
    )
    (tmp_path / "config/products.yml").write_text(
        yaml.safe_dump({"products": small_config["products"]}), encoding="utf-8"
    )
    (tmp_path / "data/reference").mkdir(parents=True)
    shutil.copy(
        project_root / "data/reference/market_context.csv",
        tmp_path / "data/reference/market_context.csv",
    )
    return tmp_path


def test_pipeline_writes_reproducible_pack(tmp_path, small_config, project_root):
    root = _prepare_root(tmp_path, small_config, project_root)
    summary = run_pipeline(root, seed=31)
    assert summary["synthetic_customers"] == 260
    assert summary["prioritised_conversations"] > 0
    assert (root / "artifacts/results/executive_summary.json").exists()
    assert (root / "artifacts/aurelia_sme_sales_demo.sqlite").exists()
    assert len(list((root / "artifacts/figures").glob("*.png"))) == 7


def test_api_read_only_endpoints(tmp_path, small_config, project_root):
    root = _prepare_root(tmp_path, small_config, project_root)
    run_pipeline(root, seed=31)
    client = TestClient(create_app(root))
    assert client.get("/health").status_code == 200
    summary = client.get("/api/v1/portfolio/summary")
    assert summary.status_code == 200
    next_best_path = root / "artifacts/results/next_best_conversations.csv"
    import pandas as pd

    next_best = pd.read_csv(next_best_path)
    customer_id = next_best.iloc[0]["customer_id"]
    rm_id = next_best.loc[
        next_best["capacity_allocated_flag"].astype(str).str.lower() == "true"
    ].iloc[0]["rm_id"]
    assert client.get(f"/api/v1/customers/{customer_id}/next-conversation").status_code == 200
    assert client.get(f"/api/v1/rms/{rm_id}/worklist?limit=3").status_code == 200
    assert client.get("/api/v1/products/CASH_MANAGEMENT/opportunities?limit=3").status_code == 200
    assert client.get("/api/v1/products/UNKNOWN/opportunities").status_code == 404
    assert client.get("/api/v1/controls").status_code == 200


def test_api_missing_outputs_returns_503(tmp_path):
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/v1/portfolio/summary").status_code == 503


def test_cli_summary(project_root):
    runner = CliRunner()
    result = runner.invoke(cli_app, ["summary", "--root", str(project_root)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["project"].startswith("Aurelia Bank")


def _load_compare_outputs(project_root):
    spec = importlib.util.spec_from_file_location(
        "compare_outputs", project_root / "scripts" / "compare_outputs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def full_demo_root(project_root, tmp_path_factory):
    """The committed configuration regenerated in a throwaway root."""
    root = tmp_path_factory.mktemp("full-demo")
    shutil.copytree(project_root / "config", root / "config")
    shutil.copytree(project_root / "data" / "reference", root / "data" / "reference")
    run_pipeline(root)
    return root


def test_committed_outputs_match_regeneration(project_root, full_demo_root):
    # The committed results once predated the RM task-policy cap (#8): two columns
    # were missing and 16 RMs showed the uncapped utilisation, yet CI stayed green.
    compare_outputs = _load_compare_outputs(project_root)
    assert compare_outputs.compare(project_root, full_demo_root) == []


def test_compare_outputs_detects_stale_committed_results(project_root, full_demo_root, tmp_path):
    compare_outputs = _load_compare_outputs(project_root)
    stale = tmp_path / "stale"
    shutil.copytree(full_demo_root / "data" / "demo", stale / "data" / "demo")
    shutil.copytree(full_demo_root / "artifacts" / "results", stale / "artifacts" / "results")
    shutil.copy2(full_demo_root / compare_outputs.SQLITE_FILE, stale / compare_outputs.SQLITE_FILE)
    rm_path = stale / "artifacts/results/rm_performance.csv"
    rm_path.write_text(
        rm_path.read_text(encoding="utf-8").replace(
            ",effective_contact_capacity", ",effective_capacity_renamed", 1
        ),
        encoding="utf-8",
    )
    summary_path = stale / "artifacts/results/executive_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["expected_incremental_profit_try"] += 1.0
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    with sqlite3.connect(stale / compare_outputs.SQLITE_FILE) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT 1"
        ).fetchone()[0]
        connection.execute(f'DELETE FROM "{table}" WHERE rowid = 1')

    errors = compare_outputs.compare(stale, full_demo_root)
    assert "artifacts/results/rm_performance.csv: columns differ" in errors
    assert any("executive_summary.json.expected_incremental_profit_try" in e for e in errors)
    assert any(e.startswith(f"{compare_outputs.SQLITE_FILE}:{table}") for e in errors)
    assert compare_outputs.main(["compare_outputs.py", str(stale), str(full_demo_root)]) == 1
