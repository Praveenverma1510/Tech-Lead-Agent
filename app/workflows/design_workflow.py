"""
DesignWorkflow: orchestrates the full 15-step reasoning pipeline.

Design decision: this is intentionally implemented as a plain sequential
Python pipeline rather than a LangGraph `StateGraph`, to keep the dependency
surface small and the control flow easy to read/debug/test line-by-line.
The `WorkflowState` dataclass below plays the same role LangGraph's typed
graph state would play (an explicit, inspectable state object threaded
through every step), so migrating this to a real LangGraph `StateGraph`
later is a mechanical refactor: each `_step_*` method below becomes a graph
node, and `WorkflowState` becomes the graph's state schema.

Steps 1-15 as specified in the project brief:
  1. Analyse the feature request              -> _step_analyse
  2. Detect missing information                -> folded into _step_clarify
  3. Generate clarifying questions             -> _step_clarify
  4. Create assumptions                        -> _step_assumptions
  5. Generate requirements                     -> covered by step 1's output
  6. Generate architecture                     -> _step_architecture
  7. Generate database design                  -> _step_database
  8. Generate API design                       -> _step_api
  9. Generate security plan                    -> _step_security
  10. Generate scalability strategy            -> _step_scalability (+ reliability/risk)
  11. Generate deployment plan                 -> _step_deployment
  12. Generate monitoring strategy             -> _step_monitoring
  13. Generate development roadmap             -> _step_roadmap
  14. Generate engineering tasks               -> folded into _step_roadmap
  15. Generate final design document           -> _step_finalize
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.tech_lead_agent import TechLeadAgent
from app.models.schemas import DesignDocumentSections, FeatureRequest
from app.services import document_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorkflowState:
    """Explicit state object threaded through every workflow step.

    Kept as a plain dataclass (not the final Pydantic model) because
    intermediate state is mutated incrementally step-by-step, which is
    awkward with frozen/validated models but natural with a dataclass.
    It's converted into the validated `DesignDocumentSections` model only
    once, at the end, in `_step_finalize`.
    """

    feature_description: str
    team_size: int | None = None
    timeline_weeks: int | None = None

    requirement_analysis: str = ""
    clarifying_questions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
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
    future_improvements: list[str] = field(default_factory=list)


class DesignWorkflow:
    """Runs the full pipeline, turning a FeatureRequest into a DesignDocumentSections."""

    def __init__(self, agent: TechLeadAgent) -> None:
        self._agent = agent

    def run(self, request: FeatureRequest) -> tuple[str, DesignDocumentSections]:
        """Execute all 15 steps in order and return (title, sections).

        Steps are intentionally sequential (not parallelized) because later
        steps consume the *text output* of earlier steps as context (e.g.
        the database schema step reads the requirement analysis), which
        produces a more internally-consistent document than generating all
        sections independently from just the raw feature description.
        """
        state = WorkflowState(
            feature_description=request.description,
            team_size=request.team_size,
            timeline_weeks=request.timeline_weeks,
        )

        self._step_analyse(state)
        self._step_clarify(state)
        self._step_assumptions(state)
        self._step_architecture(state)
        self._step_database(state)
        self._step_api(state)
        self._step_security(state)
        self._step_scalability(state)
        self._step_deployment(state)
        self._step_monitoring(state)
        self._step_roadmap(state)
        self._step_testing_and_future(state)

        title = document_service.derive_title(request.description)
        sections = self._step_finalize(state)
        logger.info("Design document generation complete for: %s", title)
        return title, sections

    # -- individual steps -----------------------------------------------------------

    def _step_analyse(self, state: WorkflowState) -> None:
        """Step 1 & 5: requirement analysis (functional + non-functional requirements)."""
        state.requirement_analysis = self._agent.analyse_requirements(state.feature_description)

    def _step_clarify(self, state: WorkflowState) -> None:
        """Steps 2-3: detect gaps and phrase them as clarifying questions."""
        state.clarifying_questions = self._agent.generate_clarifying_questions(
            state.feature_description, state.requirement_analysis
        )

    def _step_assumptions(self, state: WorkflowState) -> None:
        """Step 4: convert clarifying questions into working assumptions."""
        state.assumptions = self._agent.generate_assumptions(state.feature_description, state.clarifying_questions)

    def _step_architecture(self, state: WorkflowState) -> None:
        """Step 6: architecture narrative + ASCII diagram + technology recommendations."""
        state.high_level_architecture = self._agent.generate_architecture(
            state.feature_description, state.requirement_analysis, state.assumptions
        )
        state.architecture_diagram_ascii = self._agent.generate_architecture_diagram(
            state.feature_description, state.high_level_architecture
        )
        state.technology_recommendations = self._agent.generate_technology_recommendations(
            state.feature_description, state.high_level_architecture
        )

    def _step_database(self, state: WorkflowState) -> None:
        """Step 7: database schema design."""
        state.database_schema = self._agent.generate_database_schema(
            state.feature_description, state.requirement_analysis
        )

    def _step_api(self, state: WorkflowState) -> None:
        """Step 8: API design."""
        state.api_design = self._agent.generate_api_design(state.feature_description, state.requirement_analysis)

    def _step_security(self, state: WorkflowState) -> None:
        """Step 9: security plan."""
        state.security_considerations = self._agent.generate_security_plan(
            state.feature_description, state.requirement_analysis
        )

    def _step_scalability(self, state: WorkflowState) -> None:
        """Step 10: scalability, reliability, risk analysis, and edge cases."""
        state.scalability_plan = self._agent.generate_scalability_plan(
            state.feature_description, state.high_level_architecture
        )
        state.reliability_strategy = self._agent.generate_reliability_strategy(
            state.feature_description, state.high_level_architecture
        )
        state.risk_analysis, state.edge_cases = self._agent.generate_risk_and_edge_cases(
            state.feature_description, state.requirement_analysis
        )

    def _step_deployment(self, state: WorkflowState) -> None:
        """Step 11: deployment plan."""
        state.deployment_strategy = self._agent.generate_deployment_plan(
            state.feature_description, state.technology_recommendations
        )

    def _step_monitoring(self, state: WorkflowState) -> None:
        """Step 12: monitoring/observability strategy."""
        state.monitoring_strategy = self._agent.generate_monitoring_strategy(
            state.feature_description, state.high_level_architecture
        )

    def _step_roadmap(self, state: WorkflowState) -> None:
        """Steps 13-14: sprint planning, task breakdown, timeline, team allocation."""
        (
            state.sprint_planning,
            state.task_breakdown,
            state.timeline,
            state.team_allocation,
        ) = self._agent.generate_roadmap(
            state.feature_description, state.requirement_analysis, state.team_size, state.timeline_weeks
        )

    def _step_testing_and_future(self, state: WorkflowState) -> None:
        """Step 15 (part a/b): testing strategy and future improvements."""
        state.testing_strategy = self._agent.generate_testing_strategy(state.feature_description, state.api_design)
        state.future_improvements = self._agent.generate_future_improvements(
            state.feature_description, state.requirement_analysis
        )

    def _step_finalize(self, state: WorkflowState) -> DesignDocumentSections:
        """Step 15: assemble the final validated DesignDocumentSections model."""
        return DesignDocumentSections(
            requirement_analysis=state.requirement_analysis,
            clarifying_questions=state.clarifying_questions,
            assumptions=state.assumptions,
            high_level_architecture=state.high_level_architecture,
            architecture_diagram_ascii=state.architecture_diagram_ascii,
            technology_recommendations=state.technology_recommendations,
            database_schema=state.database_schema,
            api_design=state.api_design,
            security_considerations=state.security_considerations,
            scalability_plan=state.scalability_plan,
            reliability_strategy=state.reliability_strategy,
            risk_analysis=state.risk_analysis,
            edge_cases=state.edge_cases,
            sprint_planning=state.sprint_planning,
            task_breakdown=state.task_breakdown,
            timeline=state.timeline,
            team_allocation=state.team_allocation,
            testing_strategy=state.testing_strategy,
            deployment_strategy=state.deployment_strategy,
            monitoring_strategy=state.monitoring_strategy,
            future_improvements="\n".join(f"- {item}" for item in state.future_improvements),
        )

    def run_analysis_only(self, request: FeatureRequest) -> tuple[str, list[str], list[str]]:
        """Lightweight path for the /analyse endpoint: steps 1-4 only.

        Kept separate from `run()` (rather than having `run()` accept a
        "stop early" flag) because it has a distinct, simpler return type
        and callers (the /analyse route) shouldn't need to know about the
        full WorkflowState/DesignDocumentSections machinery.
        """
        state = WorkflowState(feature_description=request.description)
        self._step_analyse(state)
        self._step_clarify(state)
        self._step_assumptions(state)
        return state.requirement_analysis, state.clarifying_questions, state.assumptions
