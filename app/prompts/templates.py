"""
Prompt templates for every reasoning step of the Tech Lead Agent.

Design decisions:
- Each step gets its own focused prompt (rather than one giant prompt asking
  for everything at once). This produces noticeably higher-quality output
  because the model isn't context-switching between unrelated concerns
  (e.g. database schema vs. sprint planning) within a single completion,
  and it lets us feed the output of earlier steps into later ones so the
  document stays internally consistent.
- A shared SYSTEM_PROMPT establishes persona + tone once; per-step prompts
  stay short and stay focused on *what* to produce, not *how to sound*.
- Prompts that need structured output (clarifying questions, assumptions)
  explicitly request a strict format (one item per line, prefixed with "-")
  so downstream parsing in app.services.document_service is reliable
  without needing a second LLM call to "fix" formatting.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a Senior Staff Software Architect and Tech Lead with 15+ years of \
experience designing production systems at scale (payments, e-commerce, fintech, and \
high-traffic consumer platforms). You write like a pragmatic, experienced engineer: concrete, \
specific, and free of fluff or marketing language. You always consider security, scalability, \
reliability, and cost. When you don't have enough information, you state clear assumptions \
rather than asking the user to stop and answer questions - you keep the design moving forward. \
Output plain Markdown only: no code fences around the whole answer, use headings/bullets/tables \
where they aid clarity."""


def requirement_analysis_prompt(feature_description: str) -> str:
    """Step 1: turn a one-line feature request into a structured requirement analysis."""
    return f"""Analyse the following feature request like a Tech Lead performing intake for a new project.

Feature request: "{feature_description}"

Produce a concise requirement analysis covering:
- Problem statement (what user/business problem this solves)
- Functional requirements (bullet list)
- Non-functional requirements (performance, availability, compliance, etc. - bullet list)
- Primary user personas / actors
- Out-of-scope items (explicitly state what this design does NOT cover)

Keep it under 350 words. Use Markdown headings (###) for each subsection."""


def clarifying_questions_prompt(feature_description: str, requirement_analysis: str) -> str:
    """Step 3: generate the open questions a real Tech Lead would ask stakeholders."""
    return f"""Feature request: "{feature_description}"

Requirement analysis so far:
{requirement_analysis}

List the 5-8 most important clarifying questions a Tech Lead would ask the product owner \
before finalizing the design (e.g. scale expectations, compliance requirements, budget, \
existing infrastructure constraints). Output ONLY a plain list, one question per line, each \
line starting with "- ". No preamble, no numbering, no closing remarks."""


def assumptions_prompt(feature_description: str, clarifying_questions: list[str]) -> str:
    """Step 4: since we won't get real stakeholder answers, generate reasonable assumptions."""
    questions_block = "\n".join(f"- {q}" for q in clarifying_questions)
    return f"""Feature request: "{feature_description}"

Clarifying questions that would normally be asked:
{questions_block}

Since no stakeholder is available to answer these questions right now, state the most \
reasonable, industry-standard assumption for each one so the design can proceed. Output ONLY \
a plain list, one assumption per line, each line starting with "- ". No preamble, no numbering, \
no closing remarks."""


def architecture_prompt(feature_description: str, requirement_analysis: str, assumptions: list[str]) -> str:
    """Step 6: high-level architecture narrative."""
    assumptions_block = "\n".join(f"- {a}" for a in assumptions)
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

Assumptions:
{assumptions_block}

Describe the high-level architecture. Cover:
- Overall architectural style (e.g. microservices, modular monolith, event-driven) and why
- Major components/services and their responsibilities
- How components communicate (sync REST/gRPC, async events/queues)
- Key third-party integrations if applicable (e.g. payment gateways, identity providers)
- Data flow for the 1-2 most important use cases

Under 400 words. Use Markdown headings (###)."""


def architecture_diagram_prompt(feature_description: str, high_level_architecture: str) -> str:
    """Step 6b: render the architecture as an ASCII diagram."""
    return f"""Feature request: "{feature_description}"

High-level architecture:
{high_level_architecture}

Draw this architecture as a clean ASCII diagram using box-drawing characters or +/-/| characters. \
Show the major components/services, the client, the database(s), and the direction of data flow \
with arrows. Output ONLY the diagram inside a single fenced code block (```), nothing else."""


def technology_recommendations_prompt(feature_description: str, high_level_architecture: str) -> str:
    """Step 6c: concrete technology choices with justification."""
    return f"""Feature request: "{feature_description}"

High-level architecture:
{high_level_architecture}

Recommend specific technologies for this system: backend language/framework, database(s), \
cache, message queue/broker (if needed), frontend (if applicable), infrastructure/cloud \
provider, and CI/CD tooling. For each choice give a one-line justification. Present as a \
Markdown table with columns: Layer | Recommendation | Justification."""


def database_schema_prompt(feature_description: str, requirement_analysis: str) -> str:
    """Step 7: database design."""
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

Design a database schema. Include:
- Choice of database type (relational/NoSQL) with justification
- Main entities/tables with key columns and types
- Relationships between entities (1:1, 1:N, N:M)
- Important indexes and why they're needed

Present entities as Markdown tables or SQL-like DDL in a fenced code block. Under 400 words."""


def api_design_prompt(feature_description: str, requirement_analysis: str) -> str:
    """Step 8: API design."""
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

Design the core REST API. List the key endpoints as a Markdown table with columns: \
Method | Path | Description | Request Body (brief) | Response (brief). Include auth-related \
endpoints if relevant. Limit to the 8-12 most important endpoints."""


def security_prompt(feature_description: str, requirement_analysis: str) -> str:
    """Step 9: security considerations."""
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

List the key security considerations: authentication/authorization approach, data encryption \
(at rest/in transit), input validation, relevant compliance standards (e.g. PCI-DSS, GDPR, \
SOC2) if applicable, secrets management, and abuse/fraud prevention if relevant. Use bullet \
points grouped under Markdown headings (###). Under 350 words."""


def scalability_prompt(feature_description: str, high_level_architecture: str) -> str:
    """Step 10: scalability strategy."""
    return f"""Feature request: "{feature_description}"

High-level architecture:
{high_level_architecture}

Describe the scalability strategy: horizontal vs vertical scaling approach, caching strategy, \
database scaling (read replicas, sharding, partitioning), load balancing, and expected \
bottlenecks with mitigations. Under 300 words, bullet points under Markdown headings (###)."""


def reliability_prompt(feature_description: str, high_level_architecture: str) -> str:
    """Step 10b: reliability strategy (fault tolerance, availability targets)."""
    return f"""Feature request: "{feature_description}"

High-level architecture:
{high_level_architecture}

Describe the reliability strategy: target SLA/uptime, redundancy/failover approach, retry and \
circuit-breaker patterns where relevant, backup and disaster recovery approach, and graceful \
degradation strategy. Under 250 words, bullet points."""


def risk_and_edge_cases_prompt(feature_description: str, requirement_analysis: str) -> str:
    """Step 10c: risk analysis + edge cases in one pass (closely related concerns)."""
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

Provide two sections:

### Risk Analysis
List the top technical, business, and operational risks with likelihood, impact, and \
mitigation, as a Markdown table (Risk | Likelihood | Impact | Mitigation).

### Edge Cases
List the important edge cases this system must handle correctly (bullet list), e.g. concurrent \
updates, partial failures, duplicate requests, invalid/malicious input, etc."""


def deployment_prompt(feature_description: str, technology_recommendations: str) -> str:
    """Step 11: deployment plan."""
    return f"""Feature request: "{feature_description}"

Technology recommendations:
{technology_recommendations}

Describe the deployment strategy: environments (dev/staging/prod), CI/CD pipeline stages, \
deployment method (e.g. blue-green, canary, rolling), containerization/orchestration approach, \
and rollback strategy. Under 300 words, bullet points under Markdown headings (###)."""


def monitoring_prompt(feature_description: str, high_level_architecture: str) -> str:
    """Step 12: monitoring & observability strategy."""
    return f"""Feature request: "{feature_description}"

High-level architecture:
{high_level_architecture}

Describe the monitoring and observability strategy: key metrics to track (golden signals), \
logging approach, distributed tracing if relevant, alerting thresholds/on-call approach, and \
recommended tooling (open-source or free-tier friendly where possible). Under 250 words."""


def roadmap_prompt(
    feature_description: str,
    requirement_analysis: str,
    team_size: int | None,
    timeline_weeks: int | None,
) -> str:
    """Step 13+14: development roadmap - sprint plan, task breakdown, timeline, team allocation."""
    team_hint = f"The team has {team_size} engineers." if team_size else "Assume a team of 4-6 engineers."
    timeline_hint = (
        f"The target timeline is {timeline_weeks} weeks." if timeline_weeks else "Propose a realistic timeline."
    )
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

{team_hint} {timeline_hint}

Produce a development roadmap with four clearly labeled Markdown sections:

### Sprint Planning
Break the work into 2-week sprints with a goal for each sprint.

### Task Breakdown
List concrete engineering tasks as a Markdown table (Task | Owner Role | Est. Days).

### Timeline
A brief week-by-week or milestone-based timeline summary.

### Team Allocation
Recommend roles needed (e.g. backend, frontend, DevOps, QA) and how many of each."""


def testing_strategy_prompt(feature_description: str, api_design: str) -> str:
    """Step 15a: testing strategy."""
    return f"""Feature request: "{feature_description}"

API design:
{api_design}

Describe the testing strategy: unit testing approach, integration testing, contract/API \
testing, end-to-end testing, load/performance testing, and the target test coverage. Under \
250 words, bullet points under Markdown headings (###)."""


def future_improvements_prompt(feature_description: str, requirement_analysis: str) -> str:
    """Step 15b: forward-looking suggestions."""
    return f"""Feature request: "{feature_description}"

Requirement analysis:
{requirement_analysis}

List 5-8 realistic future improvements or v2 features that were intentionally left out of this \
initial design to keep scope manageable. Output ONLY a plain bullet list, each line starting \
with "- "."""
