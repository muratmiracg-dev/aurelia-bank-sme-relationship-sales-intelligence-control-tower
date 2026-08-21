"""Read-only FastAPI interface for governed portfolio outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from .constants import PRODUCTS


def create_app(root: str | Path | None = None) -> FastAPI:
    """Create a read-only API bound to generated demo outputs."""
    project_root = Path(root or os.getenv("AURELIA_SME_SALES_ROOT", Path.cwd())).resolve()
    app = FastAPI(
        title="Aurelia Bank SME Relationship & Sales Intelligence API",
        version="1.0.0",
        description="Read-only, controlled-synthetic decision-support evidence.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "read_only_synthetic_demo"}

    @app.get("/api/v1/portfolio/summary")
    def portfolio_summary() -> dict[str, Any]:
        path = project_root / "artifacts" / "results" / "executive_summary.json"
        if not path.exists():
            raise HTTPException(status_code=503, detail="Run the demo pipeline first")
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/api/v1/customers/{customer_id}/next-conversation")
    def customer_next_conversation(customer_id: str) -> dict[str, Any]:
        frame = _read_csv(project_root, "next_best_conversations")
        match = frame.loc[frame["customer_id"] == customer_id]
        if match.empty:
            raise HTTPException(status_code=404, detail="No governed conversation found")
        return _record(match.sort_values("opportunity_score", ascending=False).iloc[0])

    @app.get("/api/v1/rms/{rm_id}/worklist")
    def rm_worklist(rm_id: str, limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
        frame = _read_csv(project_root, "rm_worklist")
        match = frame.loc[frame["rm_id"] == rm_id].sort_values("opportunity_score", ascending=False)
        if match.empty:
            raise HTTPException(status_code=404, detail="Relationship manager not found")
        return [_record(row) for _, row in match.head(limit).iterrows()]

    @app.get("/api/v1/products/{product_code}/opportunities")
    def product_opportunities(
        product_code: str,
        limit: int = Query(20, ge=1, le=100),
    ) -> list[dict[str, Any]]:
        if product_code not in PRODUCTS:
            raise HTTPException(status_code=404, detail="Unknown governed product code")
        frame = _read_csv(project_root, "product_opportunities")
        match = frame.loc[
            (frame["product_code"] == product_code)
            & frame["recommendation_status"].isin(["HIGH_PRIORITY", "MEDIUM_PRIORITY"])
        ].sort_values("opportunity_score", ascending=False)
        return [_record(row) for _, row in match.head(limit).iterrows()]

    @app.get("/api/v1/controls")
    def controls() -> list[dict[str, Any]]:
        frame = _read_csv(project_root, "management_controls")
        return [_record(row) for _, row in frame.iterrows()]

    return app


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    path = root / "artifacts" / "results" / f"{name}.csv"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Run the demo pipeline first")
    return pd.read_csv(path)


def _record(row: pd.Series) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if pd.isna(value):
            result[str(key)] = None
        elif hasattr(value, "item"):
            result[str(key)] = value.item()
        else:
            result[str(key)] = value
    return result


app = create_app()
