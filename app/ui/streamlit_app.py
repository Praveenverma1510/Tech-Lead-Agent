"""
Streamlit UI for the AI Tech Lead Agent.

This is a thin presentation layer only: it collects a `FeatureRequest` from
the user, calls the exact same `DesignWorkflow` used by the API and CLI, and
renders the resulting `DesignDocumentSections`. No business logic lives here
-- if you change how a section is generated or rendered, that happens in
`app.agents` / `app.workflows` / `app.services`, and this UI picks it up for
free.

Run with:
    streamlit run app/ui/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit runs this file as a standalone script and only adds *this file's*
# directory (app/ui) to sys.path - not the project root. Without this, `import
# app...` fails with `ModuleNotFoundError: No module named 'app'` even though
# we're launched from the project root. We insert the project root (two
# levels up: app/ui -> app -> project root) at the front of sys.path before
# any `app.*` imports below.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from app.agents.tech_lead_agent import TechLeadAgent
from app.config.settings import MissingAPIKeyError, get_settings
from app.models.schemas import FeatureRequest, OutputFormat
from app.services import document_service
from app.services.llm_client import LLMRequestError, get_llm_client
from app.workflows.design_workflow import DesignWorkflow

# --- Page setup -----------------------------------------------------------------
st.set_page_config(
    page_title="AI Tech Lead Agent",
    page_icon="🧭",
    layout="wide",
)

# Human-friendly labels for the section fields on DesignDocumentSections,
# in display order. Kept here (not in app.models) since this ordering/labeling
# is a UI concern, not a data-model concern.
SECTION_LABELS: list[tuple[str, str]] = [
    ("requirement_analysis", "1. Requirement Analysis"),
    ("high_level_architecture", "4. High-Level Architecture"),
    ("architecture_diagram_ascii", "5. Architecture Diagram"),
    ("technology_recommendations", "6. Technology Recommendations"),
    ("database_schema", "7. Database Schema"),
    ("api_design", "8. API Design"),
    ("security_considerations", "9. Security Considerations"),
    ("scalability_plan", "10. Scalability Plan"),
    ("reliability_strategy", "11. Reliability Strategy"),
    ("risk_analysis", "12. Risk Analysis"),
    ("edge_cases", "12. Edge Cases"),
    ("sprint_planning", "13. Sprint Planning"),
    ("task_breakdown", "13. Task Breakdown"),
    ("timeline", "13. Timeline"),
    ("team_allocation", "13. Team Allocation"),
    ("testing_strategy", "14. Testing Strategy"),
    ("deployment_strategy", "15. Deployment Strategy"),
    ("monitoring_strategy", "16. Monitoring Strategy"),
    ("future_improvements", "17. Future Improvements"),
]

FILE_EXTENSION_BY_FORMAT = {
    OutputFormat.MARKDOWN: "md",
    OutputFormat.JSON: "json",
    OutputFormat.HTML: "html",
    OutputFormat.PDF_READY_MARKDOWN: "md",
}


@st.cache_resource(show_spinner=False)
def _get_workflow() -> DesignWorkflow:
    """Build the workflow once per Streamlit session/process.

    Cached with `st.cache_resource` (not `st.cache_data`, since LLMClient
    holds a live HTTP connection object) so we don't reconstruct the LLM
    client on every widget interaction/rerun - only once, lazily, the first
    time a generation actually happens.
    """
    settings = get_settings()
    llm_client = get_llm_client(settings)
    agent = TechLeadAgent(llm_client)
    return DesignWorkflow(agent)


def _sidebar() -> None:
    """Render provider/config info and a link to setup instructions."""
    settings = get_settings()
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.markdown(f"**Provider:** `{settings.llm_provider}`")
        model_map = {
            "groq": settings.groq_model,
            "openrouter": settings.openrouter_model,
            "gemini": settings.gemini_model,
            "ollama": settings.ollama_model,
        }
        st.markdown(f"**Model:** `{model_map.get(settings.llm_provider, 'unknown')}`")

        key_map = {
            "groq": settings.groq_api_key,
            "openrouter": settings.openrouter_api_key,
            "gemini": settings.gemini_api_key,
            "ollama": "local",
        }
        configured = bool(key_map.get(settings.llm_provider))
        if configured:
            st.success("API key configured ✅")
        else:
            st.error("No API key found for this provider.")
            st.caption(
                "Copy `.env.example` to `.env`, set the appropriate key "
                "(e.g. `GROQ_API_KEY`), then restart Streamlit."
            )

        st.divider()
        st.caption(
            "Change provider via the `LLM_PROVIDER` value in `.env` "
            "(`groq` | `openrouter` | `gemini` | `ollama`)."
        )


def _render_examples_row() -> None:
    """Quick-fill example buttons so users can try the agent with one click."""
    st.caption("Try an example:")
    examples = [
        "Build an online payment system.",
        "Build a real-time chat application.",
        "Build a ride-sharing platform.",
        "Build a URL shortener service.",
    ]
    cols = st.columns(len(examples))
    for col, example in zip(cols, examples):
        if col.button(example, use_container_width=True):
            st.session_state["description_input"] = example


def _input_form() -> FeatureRequest | None:
    """Render the input form and return a validated FeatureRequest on submit."""
    st.subheader("Describe the feature you want designed")
    _render_examples_row()

    with st.form("feature_request_form"):
        description = st.text_area(
            "Feature request",
            key="description_input",
            placeholder="e.g. Build an online payment system that lets users pay merchants with a credit card or wallet balance.",
            height=110,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            output_format = st.selectbox(
                "Output format",
                options=list(OutputFormat),
                format_func=lambda f: f.value.replace("_", " ").title(),
                index=0,
            )
        with col2:
            team_size = st.number_input(
                "Team size (optional)", min_value=0, max_value=200, value=0, step=1
            )
        with col3:
            timeline_weeks = st.number_input(
                "Timeline in weeks (optional)",
                min_value=0,
                max_value=104,
                value=0,
                step=1,
            )

        submitted = st.form_submit_button(
            "🚀 Generate Design Document", use_container_width=True, type="primary"
        )

    if not submitted:
        return None

    if not description or not description.strip():
        st.warning("Please describe the feature before generating a design document.")
        return None

    return FeatureRequest(
        description=description.strip(),
        output_format=output_format,
        team_size=int(team_size) or None,
        timeline_weeks=int(timeline_weeks) or None,
    )


def _render_results(
    title: str, sections, rendered_document: str, output_format: OutputFormat
) -> None:
    """Render the generated document: quick-scan cards + full rendered document + download."""
    st.success(f"Design document generated: **{title}**")

    tab_sections, tab_document, tab_download = st.tabs(
        ["📋 Sections", "📄 Full Document", "⬇️ Download"]
    )

    with tab_sections:
        if sections.clarifying_questions:
            with st.expander("❓ Clarifying Questions", expanded=True):
                for q in sections.clarifying_questions:
                    st.markdown(f"- {q}")
        if sections.assumptions:
            with st.expander("📌 Assumptions", expanded=True):
                for a in sections.assumptions:
                    st.markdown(f"- {a}")

        for field_name, label in SECTION_LABELS:
            content = getattr(sections, field_name, "")
            if not content:
                continue
            with st.expander(label):
                st.markdown(content)

    with tab_document:
        if output_format == OutputFormat.HTML:
            st.components.v1.html(rendered_document, height=800, scrolling=True)
        elif output_format == OutputFormat.JSON:
            st.json(rendered_document)
        else:
            st.markdown(rendered_document)

    with tab_download:
        extension = FILE_EXTENSION_BY_FORMAT[output_format]
        file_name = f"{title.lower().replace(' ', '_').replace('-', '')}.{extension}"
        st.download_button(
            "Download design document",
            data=rendered_document,
            file_name=file_name,
            mime="text/plain",
            use_container_width=True,
        )


def main() -> None:
    """Streamlit entrypoint."""
    st.title("🧭 AI Tech Lead Agent")
    st.caption(
        "Describe a feature in plain English and get a complete technical design document: "
        "architecture, database schema, API design, security, scalability, sprint plan, and more."
    )

    _sidebar()
    request = _input_form()

    if request is None:
        return

    try:
        with st.spinner(
            "Running the 15-step design pipeline... this can take 30-90 seconds."
        ):
            workflow = _get_workflow()
            title, sections = workflow.run(request)
            rendered_document = document_service.render_document(
                title, sections, request.output_format
            )
    except MissingAPIKeyError as exc:
        st.error(f"Configuration error: {exc}")
        return
    except LLMRequestError as exc:
        st.error(f"The LLM provider request failed: {exc}")
        return

    _render_results(title, sections, rendered_document, request.output_format)


if __name__ == "__main__":
    main()
