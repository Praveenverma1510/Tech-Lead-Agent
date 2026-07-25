"""
TechLeadAgent: wraps an LLMClient and exposes one method per reasoning step.

Design decision: the agent is intentionally "dumb" - each method does exactly
one LLM call using a prompt template from app.prompts.templates, and returns
either raw text or a parsed structure. It does NOT decide the *order* of
steps or how outputs feed into each other; that orchestration logic lives in
app.workflows.design_workflow.DesignWorkflow. This separation means:
  - The agent is trivially unit-testable (mock the LLMClient, assert the
    right prompt was built and the right parsing happened).
  - The workflow can be modified (reordered, parallelized, steps skipped)
    without touching any prompt or parsing logic.
"""

from __future__ import annotations

from app.prompts import templates
from app.services.document_service import parse_bullet_list
from app.services.llm_client import LLMClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TechLeadAgent:
    """Performs each individual reasoning step of the design process via the LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    # -- Step 1 -----------------------------------------------------------------
    def analyse_requirements(self, feature_description: str) -> str:
        """Step 1: produce the requirement analysis section."""
        logger.info("Step 1/15: analysing requirements.")
        prompt = templates.requirement_analysis_prompt(feature_description)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Steps 2-3 ----------------------------------------------------------------
    def generate_clarifying_questions(self, feature_description: str, requirement_analysis: str) -> list[str]:
        """Steps 2-3: detect missing information and phrase it as clarifying questions."""
        logger.info("Step 2-3/15: generating clarifying questions.")
        prompt = templates.clarifying_questions_prompt(feature_description, requirement_analysis)
        raw = self._llm.complete(templates.SYSTEM_PROMPT, prompt)
        return parse_bullet_list(raw)

    # -- Step 4 -------------------------------------------------------------------
    def generate_assumptions(self, feature_description: str, clarifying_questions: list[str]) -> list[str]:
        """Step 4: convert clarifying questions into concrete working assumptions."""
        logger.info("Step 4/15: generating assumptions.")
        prompt = templates.assumptions_prompt(feature_description, clarifying_questions)
        raw = self._llm.complete(templates.SYSTEM_PROMPT, prompt)
        return parse_bullet_list(raw)

    # -- Step 6 ---------------------------------------------------------------------
    def generate_architecture(self, feature_description: str, requirement_analysis: str, assumptions: list[str]) -> str:
        """Step 6: high-level architecture narrative."""
        logger.info("Step 6/15: generating high-level architecture.")
        prompt = templates.architecture_prompt(feature_description, requirement_analysis, assumptions)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    def generate_architecture_diagram(self, feature_description: str, high_level_architecture: str) -> str:
        """Step 6b: ASCII architecture diagram."""
        logger.info("Step 6b/15: generating ASCII architecture diagram.")
        prompt = templates.architecture_diagram_prompt(feature_description, high_level_architecture)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    def generate_technology_recommendations(self, feature_description: str, high_level_architecture: str) -> str:
        """Step 6c: concrete technology stack recommendations."""
        logger.info("Step 6c/15: generating technology recommendations.")
        prompt = templates.technology_recommendations_prompt(feature_description, high_level_architecture)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Step 7 -----------------------------------------------------------------------
    def generate_database_schema(self, feature_description: str, requirement_analysis: str) -> str:
        """Step 7: database design."""
        logger.info("Step 7/15: generating database schema.")
        prompt = templates.database_schema_prompt(feature_description, requirement_analysis)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Step 8 -------------------------------------------------------------------------
    def generate_api_design(self, feature_description: str, requirement_analysis: str) -> str:
        """Step 8: API design."""
        logger.info("Step 8/15: generating API design.")
        prompt = templates.api_design_prompt(feature_description, requirement_analysis)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Step 9 ---------------------------------------------------------------------------
    def generate_security_plan(self, feature_description: str, requirement_analysis: str) -> str:
        """Step 9: security considerations."""
        logger.info("Step 9/15: generating security plan.")
        prompt = templates.security_prompt(feature_description, requirement_analysis)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Step 10 --------------------------------------------------------------------------
    def generate_scalability_plan(self, feature_description: str, high_level_architecture: str) -> str:
        """Step 10: scalability strategy."""
        logger.info("Step 10/15: generating scalability plan.")
        prompt = templates.scalability_prompt(feature_description, high_level_architecture)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    def generate_reliability_strategy(self, feature_description: str, high_level_architecture: str) -> str:
        """Step 10b: reliability strategy."""
        logger.info("Step 10b/15: generating reliability strategy.")
        prompt = templates.reliability_prompt(feature_description, high_level_architecture)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    def generate_risk_and_edge_cases(self, feature_description: str, requirement_analysis: str) -> tuple[str, str]:
        """Step 10c: risk analysis and edge cases, split back into two sections.

        The prompt asks for both under one call (they're closely related and
        benefit from shared context), so we split the "### Risk Analysis" /
        "### Edge Cases" headings back apart here for storage in separate
        DesignDocumentSections fields.
        """
        logger.info("Step 10c/15: generating risk analysis and edge cases.")
        prompt = templates.risk_and_edge_cases_prompt(feature_description, requirement_analysis)
        raw = self._llm.complete(templates.SYSTEM_PROMPT, prompt)
        return self._split_two_sections(raw, "### Edge Cases")

    @staticmethod
    def _split_two_sections(raw: str, second_heading: str) -> tuple[str, str]:
        """Split a two-section Markdown response at `second_heading`."""
        if second_heading in raw:
            first, _, second = raw.partition(second_heading)
            return first.strip(), (second_heading + second).strip()
        # Fallback: model didn't include the heading exactly as asked - return
        # everything as the first section rather than losing content.
        return raw.strip(), ""

    # -- Step 11 -------------------------------------------------------------------------
    def generate_deployment_plan(self, feature_description: str, technology_recommendations: str) -> str:
        """Step 11: deployment strategy."""
        logger.info("Step 11/15: generating deployment plan.")
        prompt = templates.deployment_prompt(feature_description, technology_recommendations)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Step 12 ----------------------------------------------------------------------------
    def generate_monitoring_strategy(self, feature_description: str, high_level_architecture: str) -> str:
        """Step 12: monitoring and observability strategy."""
        logger.info("Step 12/15: generating monitoring strategy.")
        prompt = templates.monitoring_prompt(feature_description, high_level_architecture)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    # -- Steps 13-14 ---------------------------------------------------------------------------
    def generate_roadmap(
        self,
        feature_description: str,
        requirement_analysis: str,
        team_size: int | None,
        timeline_weeks: int | None,
    ) -> tuple[str, str, str, str]:
        """Steps 13-14: sprint planning, task breakdown, timeline, team allocation.

        Returned as a 4-tuple split from the model's four labeled Markdown
        sections, in the order (sprint_planning, task_breakdown, timeline, team_allocation).
        """
        logger.info("Step 13-14/15: generating development roadmap.")
        prompt = templates.roadmap_prompt(feature_description, requirement_analysis, team_size, timeline_weeks)
        raw = self._llm.complete(templates.SYSTEM_PROMPT, prompt)
        return self._split_four_sections(raw)

    @staticmethod
    def _split_four_sections(raw: str) -> tuple[str, str, str, str]:
        """Split the roadmap response into its four labeled subsections."""
        headings = ["### Sprint Planning", "### Task Breakdown", "### Timeline", "### Team Allocation"]
        positions = [raw.find(h) for h in headings]

        # If any heading is missing, fall back to putting all content in the
        # first bucket rather than raising - a partially-malformed roadmap is
        # still more useful to the user than a hard failure.
        if any(p == -1 for p in positions):
            logger.warning("Roadmap response missing expected headings; returning unsplit content.")
            return raw.strip(), "", "", ""

        ordered = sorted(zip(positions, headings), key=lambda pair: pair[0])
        chunks: list[str] = []
        for idx, (pos, _heading) in enumerate(ordered):
            end = ordered[idx + 1][0] if idx + 1 < len(ordered) else len(raw)
            chunks.append(raw[pos:end].strip())

        # Re-map back to the original (sprint, task, timeline, team) order.
        heading_to_chunk = {h: c for (_, h), c in zip(ordered, chunks)}
        return tuple(heading_to_chunk[h] for h in headings)  # type: ignore[return-value]

    # -- Step 15 ------------------------------------------------------------------------------
    def generate_testing_strategy(self, feature_description: str, api_design: str) -> str:
        """Step 15a: testing strategy."""
        logger.info("Step 15/15 (a): generating testing strategy.")
        prompt = templates.testing_strategy_prompt(feature_description, api_design)
        return self._llm.complete(templates.SYSTEM_PROMPT, prompt)

    def generate_future_improvements(self, feature_description: str, requirement_analysis: str) -> list[str]:
        """Step 15b: future improvements list."""
        logger.info("Step 15/15 (b): generating future improvements.")
        prompt = templates.future_improvements_prompt(feature_description, requirement_analysis)
        raw = self._llm.complete(templates.SYSTEM_PROMPT, prompt)
        return parse_bullet_list(raw)
