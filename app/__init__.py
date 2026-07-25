"""
AI Tech Lead Agent
===================

A production-quality AI agent that behaves like an experienced Tech Lead /
Solutions Architect. Given a plain-English feature request, it produces a
complete technical design document: requirements, architecture, database
schema, API design, security plan, scalability strategy, sprint plan, and
more.

The project follows a clean, layered architecture:

- app.config     -> environment / settings loading
- app.models     -> Pydantic data models (requests, responses, document sections)
- app.prompts    -> prompt templates used to instruct the LLM
- app.services   -> external integrations (Groq LLM client) + document assembly
- app.agents     -> the TechLeadAgent itself (owns LLM calls per reasoning step)
- app.workflows  -> orchestrates the agent's multi-step reasoning pipeline
- app.utils      -> logging, formatting, and misc helpers
- app.api        -> FastAPI HTTP interface
- app.cli        -> Typer command-line interface
"""

__version__ = "1.0.0"
