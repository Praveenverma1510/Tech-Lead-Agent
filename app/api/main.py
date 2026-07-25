"""
FastAPI HTTP interface for the AI Tech Lead Agent.

Endpoints:
  GET  /health    - liveness/readiness + provider/config check
  POST /analyse   - lightweight steps 1-4 (requirement analysis, questions, assumptions)
  POST /design    - full 15-step pipeline, returns the rendered design document
  POST /generate  - alias for /design (kept for API naming flexibility per spec)

Design decision: route handlers stay thin - they validate input (via Pydantic
models), delegate to the workflow, and translate exceptions into HTTP error
responses. All actual business logic lives in app.workflows/app.agents/app.services.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.agents.tech_lead_agent import TechLeadAgent
from app.config.settings import MissingAPIKeyError, get_settings
from app.models.schemas import (
    AnalyseResponse,
    DesignDocumentResponse,
    ErrorResponse,
    FeatureRequest,
    HealthResponse,
)
from app.services import document_service
from app.services.llm_client import LLMRequestError, get_llm_client
from app.utils.logger import get_logger
from app.workflows.design_workflow import DesignWorkflow

logger = get_logger(__name__)

app = FastAPI(
    title="AI Tech Lead Agent",
    description="Generates complete technical design documents from a plain-English feature request.",
    version="1.0.0",
)


def _build_workflow() -> DesignWorkflow:
    """Construct a fresh DesignWorkflow for this request.

    We build the LLM client per-request (not as a global singleton) so that
    a missing/invalid API key is reported as a clean HTTP error on the
    request that needs it, rather than crashing the whole app at startup -
    important because `/health` should still be reachable even if the key
    is misconfigured, so operators can diagnose the problem.
    """
    settings = get_settings()
    llm_client = get_llm_client(settings)
    agent = TechLeadAgent(llm_client)
    return DesignWorkflow(agent)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness/readiness probe. Never raises - always reports current config state."""
    settings = get_settings()
    key_map = {
        "groq": settings.groq_api_key,
        "openrouter": settings.openrouter_api_key,
        "gemini": settings.gemini_api_key,
        "ollama": "local",
    }
    configured = bool(key_map.get(settings.llm_provider))
    model_map = {
        "groq": settings.groq_model,
        "openrouter": settings.openrouter_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    return HealthResponse(
        status="ok",
        provider=settings.llm_provider,
        model=model_map.get(settings.llm_provider, "unknown"),
        api_key_configured=configured,
    )


@app.post(
    "/analyse",
    response_model=AnalyseResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def analyse(request: FeatureRequest) -> AnalyseResponse:
    """Run steps 1-4 only: requirement analysis, clarifying questions, assumptions."""
    try:
        workflow = _build_workflow()
        requirement_analysis, questions, assumptions = workflow.run_analysis_only(request)
        return AnalyseResponse(
            requirement_analysis=requirement_analysis,
            clarifying_questions=questions,
            assumptions=assumptions,
        )
    except MissingAPIKeyError as exc:
        logger.error("Configuration error on /analyse: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMRequestError as exc:
        logger.error("LLM error on /analyse: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _run_full_design(request: FeatureRequest) -> DesignDocumentResponse:
    """Shared implementation for /design and /generate."""
    settings = get_settings()
    workflow = _build_workflow()
    title, sections = workflow.run(request)
    rendered = document_service.render_document(title, sections, request.output_format)

    model_map = {
        "groq": settings.groq_model,
        "openrouter": settings.openrouter_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    return DesignDocumentResponse(
        feature_title=title,
        output_format=request.output_format,
        sections=sections,
        rendered_document=rendered,
        provider=settings.llm_provider,
        model=model_map.get(settings.llm_provider, "unknown"),
    )


@app.post(
    "/design",
    response_model=DesignDocumentResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def design(request: FeatureRequest) -> DesignDocumentResponse:
    """Run the full 15-step pipeline and return the complete design document."""
    try:
        return _run_full_design(request)
    except MissingAPIKeyError as exc:
        logger.error("Configuration error on /design: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMRequestError as exc:
        logger.error("LLM error on /design: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(
    "/generate",
    response_model=DesignDocumentResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def generate(request: FeatureRequest) -> DesignDocumentResponse:
    """Alias of /design, provided to match the spec's requested endpoint names."""
    return design(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request, exc: Exception) -> JSONResponse:
    """Catch-all so unexpected failures return a clean JSON error, not an HTML stack trace."""
    logger.exception("Unhandled exception while processing request: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="internal_server_error", detail=str(exc)).model_dump(),
    )
