"""
Pydantic models shared across the API, CLI, agent, and workflow layers.

Design decision: keeping all schemas in one module (rather than scattering
them next to each consumer) makes it trivial to see the full "shape" of data
flowing through the system, and avoids circular imports between
app.api / app.agents / app.workflows.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OutputFormat(str, Enum):
    """Supported output formats for the final design document."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    PDF_READY_MARKDOWN = "pdf_ready_markdown"


class FeatureRequest(BaseModel):
    """Incoming request describing the feature the user wants designed."""

    description: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Plain-English description of the feature, e.g. 'Build an online payment system.'",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.MARKDOWN,
        description="Desired format of the generated design document.",
    )
    team_size: int | None = Field(
        default=None,
        ge=1,
        le=200,
        description="Optional: known engineering team size, used to tailor sprint planning.",
    )
    timeline_weeks: int | None = Field(
        default=None,
        ge=1,
        le=104,
        description="Optional: target delivery timeline in weeks.",
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only descriptions early, before they hit the LLM.

        This is cheap to check here and saves an unnecessary (and costly)
        network round-trip to the LLM provider for obviously-empty input.
        """
        if not value.strip():
            raise ValueError("description cannot be blank or whitespace-only")
        return value.strip()


class ClarifyingQuestions(BaseModel):
    """Step-3 output: open questions the agent would ask a real stakeholder."""

    questions: list[str] = Field(default_factory=list)


class Assumptions(BaseModel):
    """Step-4 output: assumptions made in lieu of stakeholder answers."""

    assumptions: list[str] = Field(default_factory=list)


class DesignDocumentSections(BaseModel):
    """Every section of the final Tech Lead design document.

    Each field maps 1:1 to one of the reasoning steps in the workflow
    (analysis -> ... -> roadmap). Keeping this flat (rather than deeply
    nested) makes it trivial to render into Markdown/HTML/JSON without
    bespoke per-format logic for nested structures.
    """

    requirement_analysis: str = ""
    clarifying_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    high_level_architecture: str = ""
    architecture_diagram_ascii: str = ""
    technology_recommendations: str = ""
    database_schema: str = ""
    api_design: str = ""
    security_considerations: str = ""
    scalability_plan: str = ""
    reliability_strategy: str = ""
    risk_analysis: str = ""
    edge_cases: str = ""
    sprint_planning: str = ""
    task_breakdown: str = ""
    timeline: str = ""
    team_allocation: str = ""
    testing_strategy: str = ""
    deployment_strategy: str = ""
    monitoring_strategy: str = ""
    future_improvements: str = ""


class DesignDocumentResponse(BaseModel):
    """Top-level API/CLI response wrapping the generated document."""

    feature_title: str
    output_format: OutputFormat
    sections: DesignDocumentSections
    rendered_document: str = Field(
        description="The fully rendered document in the requested output_format."
    )
    provider: str = Field(description="Which LLM provider generated this document, e.g. 'groq'.")
    model: str = Field(description="Which model generated this document.")


class AnalyseResponse(BaseModel):
    """Response for the lightweight /analyse endpoint (steps 1-4 only)."""

    requirement_analysis: str
    clarifying_questions: list[str]
    assumptions: list[str]


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str
    provider: str
    model: str
    api_key_configured: bool


class ErrorResponse(BaseModel):
    """Uniform error envelope returned by the API on failure."""

    error: str
    detail: str
