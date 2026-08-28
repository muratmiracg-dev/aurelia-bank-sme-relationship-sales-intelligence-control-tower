from __future__ import annotations

import json
import shutil

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
