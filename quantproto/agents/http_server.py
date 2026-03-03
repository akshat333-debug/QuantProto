"""HTTP server for A2A task protocol.

FastAPI app with JWT-protected endpoints for submitting and executing
orchestrator tasks.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from quantproto.agents.auth import verify_token, DEFAULT_SECRET
from quantproto.agents.orchestrator import Orchestrator
from quantproto.agents.agent_card import AgentCard

import jwt as pyjwt


app = FastAPI(title="QuantProto A2A Server", version="0.1.0")


# ── Agent Card ────────────────────────────────────────────────────────

ORCHESTRATOR_CARD = AgentCard(
    name="QuantProto Orchestrator",
    description="Runs the full alpha → risk → decision pipeline",
    capabilities=["alpha_generation", "risk_evaluation", "backtest", "regime_detection"],
    endpoint="/tasks",
    auth_scheme="bearer_jwt",
)


# ── Models ────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    """A2A task submission."""
    prices: dict[str, list[float]]
    factor_weights: dict[str, float] | None = None
    train_window: int = 60
    test_window: int = 20
    seed: int = 42


class TaskResponse(BaseModel):
    """A2A task result."""
    action: str
    backtest: dict[str, Any]
    risk_report: dict[str, Any]
    gate: dict[str, Any]


# ── Auth dependency ───────────────────────────────────────────────────

def _verify_auth(authorization: str = Header(...)) -> dict:
    """Extract and verify JWT from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth scheme")
    token = authorization[7:]
    try:
        return verify_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    except pyjwt.DecodeError:
        raise HTTPException(status_code=401, detail="Malformed token")


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/agent-card")
def get_agent_card() -> dict:
    """Return the orchestrator's A2A agent card."""
    return ORCHESTRATOR_CARD.to_dict()


@app.post("/tasks", response_model=TaskResponse)
def submit_task(
    request: TaskRequest,
    authorization: str = Header(...),
) -> TaskResponse:
    """Submit a task for orchestrator execution.

    Requires a valid JWT in the Authorization header.
    """
    _verify_auth(authorization)

    orchestrator = Orchestrator(
        lookback=20,
        train_window=request.train_window,
        test_window=request.test_window,
        seed=request.seed,
    )

    prices_df = pd.DataFrame(request.prices)
    result = orchestrator.run_pipeline(prices_df, factor_weights=request.factor_weights)

    return TaskResponse(
        action=result["action"],
        backtest=result["backtest"],
        risk_report=result["risk_report"],
        gate=result["gate"],
    )


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
