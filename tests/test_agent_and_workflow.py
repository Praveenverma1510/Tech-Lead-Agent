"""
Tests for app.agents.tech_lead_agent and app.workflows.design_workflow.

We inject a `FakeLLMClient` instead of hitting a real provider, so these
tests are fast, deterministic, and require no API key / network access.
"""

from __future__ import annotations

from app.agents.tech_lead_agent import TechLeadAgent
from app.models.schemas import FeatureRequest
from app.services.llm_client import LLMClient
from app.workflows.design_workflow import DesignWorkflow


class FakeLLMClient(LLMClient):
    """Returns canned, step-appropriate responses instead of calling a real API."""

    provider_name = "fake"
    model_name = "fake-model"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if "clarifying questions" in user_prompt.lower():
            return "- What is the expected scale?\n- Is PCI-DSS compliance required?"
        if "reasonable, industry-standard assumption" in user_prompt.lower():
            return "- Assume 10k daily active users.\n- Assume PCI-DSS compliance is required."
        if "ASCII diagram" in user_prompt:
            return "```\n[Client] -> [API Gateway] -> [Payment Service] -> [DB]\n```"
        if "Recommend specific technologies" in user_prompt:
            return "| Layer | Recommendation | Justification |\n|---|---|---|\n| Backend | FastAPI | Fast + typed |"
        if "Provide two sections" in user_prompt:
            return (
                "### Risk Analysis\n| Risk | Likelihood | Impact | Mitigation |\n|---|---|---|---|\n"
                "| Fraud | Medium | High | Add fraud detection |\n\n"
                "### Edge Cases\n- Duplicate payment submission\n- Partial refund"
            )
        if "development roadmap" in user_prompt.lower():
            return (
                "### Sprint Planning\nSprint 1: setup. Sprint 2: core payments.\n\n"
                "### Task Breakdown\n| Task | Owner Role | Est. Days |\n|---|---|---|\n"
                "| Build payment API | Backend | 5 |\n\n"
                "### Timeline\n4 sprints, 8 weeks total.\n\n"
                "### Team Allocation\n2 backend, 1 QA, 1 DevOps."
            )
        if "future improvements" in user_prompt.lower():
            return "- Add multi-currency support\n- Add fraud ML model"
        # Default: generic prose response for analysis/architecture/db/api/security/etc.
        return "Generated section content for testing purposes."


def _make_workflow() -> DesignWorkflow:
    agent = TechLeadAgent(FakeLLMClient())
    return DesignWorkflow(agent)


def test_agent_generate_clarifying_questions_parses_bullets() -> None:
    agent = TechLeadAgent(FakeLLMClient())
    questions = agent.generate_clarifying_questions("Build a payment system.", "some analysis")
    assert questions == ["What is the expected scale?", "Is PCI-DSS compliance required?"]


def test_agent_generate_risk_and_edge_cases_splits_sections() -> None:
    agent = TechLeadAgent(FakeLLMClient())
    risk, edge = agent.generate_risk_and_edge_cases("Build a payment system.", "some analysis")
    assert risk.startswith("### Risk Analysis")
    assert edge.startswith("### Edge Cases")
    assert "Fraud" in risk
    assert "Duplicate payment" in edge


def test_agent_generate_roadmap_splits_four_sections() -> None:
    agent = TechLeadAgent(FakeLLMClient())
    sprint, tasks, timeline, team = agent.generate_roadmap("Build a payment system.", "analysis", 4, 8)
    assert sprint.startswith("### Sprint Planning")
    assert tasks.startswith("### Task Breakdown")
    assert timeline.startswith("### Timeline")
    assert team.startswith("### Team Allocation")


def test_workflow_run_produces_complete_sections() -> None:
    workflow = _make_workflow()
    request = FeatureRequest(description="Build an online payment system.", team_size=4, timeline_weeks=8)
    title, sections = workflow.run(request)

    assert title == "Online payment system - Technical Design Document"
    assert sections.requirement_analysis
    assert sections.clarifying_questions
    assert sections.assumptions
    assert sections.high_level_architecture
    assert sections.architecture_diagram_ascii.startswith("```")
    assert "FastAPI" in sections.technology_recommendations
    assert sections.database_schema
    assert sections.api_design
    assert sections.security_considerations
    assert sections.scalability_plan
    assert sections.reliability_strategy
    assert sections.risk_analysis.startswith("### Risk Analysis")
    assert sections.edge_cases.startswith("### Edge Cases")
    assert sections.sprint_planning.startswith("### Sprint Planning")
    assert sections.task_breakdown.startswith("### Task Breakdown")
    assert sections.timeline.startswith("### Timeline")
    assert sections.team_allocation.startswith("### Team Allocation")
    assert sections.testing_strategy
    assert sections.deployment_strategy
    assert sections.monitoring_strategy
    assert "multi-currency" in sections.future_improvements


def test_workflow_run_analysis_only_returns_three_parts() -> None:
    workflow = _make_workflow()
    request = FeatureRequest(description="Build a chat application.")
    requirement_analysis, questions, assumptions = workflow.run_analysis_only(request)

    assert requirement_analysis == "Generated section content for testing purposes."
    assert questions == ["What is the expected scale?", "Is PCI-DSS compliance required?"]
    assert assumptions == ["Assume 10k daily active users.", "Assume PCI-DSS compliance is required."]
