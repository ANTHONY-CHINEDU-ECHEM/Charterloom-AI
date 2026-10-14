"""REST API for Charterloom AI.

Endpoints
  GET  /health                 service status and model manifest summary
  GET  /templates              the workflow template library
  GET  /templates/{archetype}  a single canonical template
  POST /recommend              recommend, customise and explain for a charter
  POST /retrieve               hybrid search over the knowledge base
  POST /validate               validate a workflow configuration
"""

from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from charterloom import __version__
from charterloom.catalog import ARCHETYPE_KEYS
from charterloom.config import load_settings
from charterloom.knowledge.templates import build_template
from charterloom.pipeline import CharterloomPipeline
from charterloom.state_machine import validate


class RecommendRequest(BaseModel):
    charter_text: str = Field(..., min_length=40, description="Full text of the project charter")
    project_name: str = Field(None, description="Optional display name for the project")
    include_configuration: bool = Field(True, description="Generate the tailored state machine")


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=3)
    top_k: int = Field(5, ge=1, le=50)
    doc_types: list = Field(None, description="Subset of blueprint, post_mortem, methodology, workflow_template")


class ValidateRequest(BaseModel):
    configuration: dict


def create_app(settings=None, pipeline=None):
    settings = settings or load_settings()
    app = FastAPI(title="Charterloom AI", version=__version__,
                  description="Intelligent workflow and template recommender for custom project lifecycles.")

    @lru_cache(maxsize=1)
    def get_pipeline():
        return pipeline or CharterloomPipeline.load(settings.artifacts_dir)

    @app.get("/health")
    def health():
        try:
            manifest = get_pipeline().manifest
        except FileNotFoundError as exc:
            return {"status": "untrained", "detail": str(exc), "version": __version__}
        return {"status": "ok", "version": __version__, "trained_at": manifest.get("trained_at"),
                "training_projects": manifest.get("training_projects"), "chunks_indexed": manifest.get("chunks_indexed")}

    @app.get("/templates")
    def templates():
        return {key: {"display_name": build_template(key)["display_name"], "summary": build_template(key)["summary"]}
                for key in ARCHETYPE_KEYS}

    @app.get("/templates/{archetype}")
    def template(archetype: str):
        if archetype not in ARCHETYPE_KEYS:
            raise HTTPException(status_code=404, detail=f"Unknown archetype {archetype}")
        return build_template(archetype)

    @app.post("/recommend")
    def recommend(request: RecommendRequest):
        try:
            return get_pipeline().recommend(request.charter_text, project_name=request.project_name,
                                            include_configuration=request.include_configuration)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/retrieve")
    def retrieve(request: RetrieveRequest):
        hits = get_pipeline().retriever.search(request.query, top_k=request.top_k, doc_types=request.doc_types)
        return {"query": request.query, "hits": [h.to_dict() for h in hits]}

    @app.post("/validate")
    def validate_configuration(request: ValidateRequest):
        required = {"states", "transitions"}
        if not required <= set(request.configuration):
            raise HTTPException(status_code=422, detail="Configuration needs states and transitions")
        return validate(request.configuration).to_dict()

    return app
