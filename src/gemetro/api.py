"""I-17: stateless HTTP API (deployed on Render, PHASE_1_ARCHITECTURE.md §1).

Endpoints:
- GET  /health    liveness and whether the comfort model artifact is loaded;
- GET  /config    slider ranges, defaults, fixed parameters, provenance, ML domain, PMV
                  validity ranges and guided-mode periods;
- POST /scenario  one complete scenario record (gemetro.scenario.run_scenario);
- GET  /guided    one representative scenario record per hour of a line and period
                  (gemetro.guided.run_guided, GUIDED_MODE.md).

The API only reads versioned artifacts at startup; it never writes files nor keeps state
between requests. No class probability or confidence is exposed (§3.1).
CORS origins come from GEMETRO_ALLOWED_ORIGINS (comma separated); the local frontend dev
origin (LOCAL_FRONTEND_ORIGIN) is always allowed.

Run locally: uvicorn gemetro.api:app
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from gemetro.comfort_model import MODEL_DIR, ComfortModel
from gemetro.guided import guided_config, run_guided
from gemetro.pmv import VALIDITY_RANGES
from gemetro.scenario import DEFAULTS, Scenario, ScenarioError, run_scenario, scenario_config


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line: Literal["A", "B"] = DEFAULTS["line"]
    hour: int = DEFAULTS["hour"]
    phi_peak: float = DEFAULTS["phi_peak"]
    tau_r: int = DEFAULTS["tau_r"]
    vel: float = DEFAULTS["vel"]
    clo: float = DEFAULTS["clo"]
    posture: Literal["seated", "standing"] = DEFAULTS["posture"]
    delta_t: float | None = None


LOCAL_FRONTEND_ORIGIN = "http://localhost:5500"


def _allowed_origins() -> list[str]:
    raw = os.environ.get("GEMETRO_ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if LOCAL_FRONTEND_ORIGIN not in origins:
        origins.append(LOCAL_FRONTEND_ORIGIN)
    return origins


def create_app(model_dir: Path = MODEL_DIR) -> FastAPI:
    state: dict[str, ComfortModel | str] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            state["model"] = ComfortModel.load(model_dir)
        except FileNotFoundError as error:
            state["error"] = str(error)
        yield
        state.clear()

    app = FastAPI(title="Gemetro Digital — Pseudo Digital Twin API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "model_loaded": "model" in state}

    def loaded_model() -> ComfortModel:
        model = state.get("model")
        if not isinstance(model, ComfortModel):
            raise HTTPException(status_code=503, detail=state.get("error", "model not loaded"))
        return model

    @app.get("/config")
    def config() -> dict:
        model = state.get("model")
        return {
            **scenario_config(),
            # The domain comes from the loaded artifact; None while it is unavailable.
            "domain": model.domain.to_dict() if isinstance(model, ComfortModel) else None,
            "pmv_ranges": {k: {"min": lo, "max": hi} for k, (lo, hi) in VALIDITY_RANGES.items()},
            "guided": guided_config(),
        }

    @app.post("/scenario")
    def scenario(request: ScenarioRequest) -> dict:
        model = loaded_model()
        try:
            return run_scenario(Scenario(**request.model_dump()), model)
        except ScenarioError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None

    @app.get("/guided")
    def guided(line: Literal["A", "B"],
               period: Literal["morning", "midday", "afternoon", "night"]) -> dict:
        model = loaded_model()
        try:
            return run_guided(line, period, model)
        except ScenarioError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None

    return app


app = create_app()
