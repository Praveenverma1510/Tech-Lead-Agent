"""
Command-line interface for the AI Tech Lead Agent, built with Typer + Rich.

Usage:
    python main.py                          # interactive mode: prompts for a feature request
    python -m app.cli.cli analyse "..."      # steps 1-4 only
    python -m app.cli.cli design "..."       # full pipeline, prints + optionally saves the document
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from app.agents.tech_lead_agent import TechLeadAgent
from app.config.settings import MissingAPIKeyError, get_settings
from app.models.schemas import FeatureRequest, OutputFormat
from app.services import document_service
from app.services.llm_client import LLMRequestError, get_llm_client
from app.utils.logger import get_logger
from app.workflows.design_workflow import DesignWorkflow

logger = get_logger(__name__)
console = Console()

cli = typer.Typer(
    name="tech-lead-agent",
    help="AI Tech Lead Agent - turn a feature request into a full technical design document.",
    add_completion=False,
)


def _build_workflow() -> DesignWorkflow:
    """Construct the workflow, surfacing configuration errors as clean CLI messages."""
    settings = get_settings()
    llm_client = get_llm_client(settings)
    agent = TechLeadAgent(llm_client)
    return DesignWorkflow(agent)


@cli.command()
def analyse(
    description: str = typer.Argument(..., help="The feature request, e.g. 'Build an online payment system.'"),
) -> None:
    """Run only steps 1-4: requirement analysis, clarifying questions, assumptions."""
    request = FeatureRequest(description=description)
    try:
        with console.status("[bold green]Analysing requirements..."):
            workflow = _build_workflow()
            requirement_analysis, questions, assumptions = workflow.run_analysis_only(request)
    except MissingAPIKeyError as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except LLMRequestError as exc:
        console.print(f"[bold red]LLM request failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(Panel(Markdown(requirement_analysis), title="Requirement Analysis"))
    console.print(Panel("\n".join(f"- {q}" for q in questions), title="Clarifying Questions"))
    console.print(Panel("\n".join(f"- {a}" for a in assumptions), title="Assumptions"))


@cli.command()
def design(
    description: str = typer.Argument(..., help="The feature request, e.g. 'Build an online payment system.'"),
    output_format: OutputFormat = typer.Option(OutputFormat.MARKDOWN, "--format", "-f", help="Output format."),
    team_size: Optional[int] = typer.Option(None, "--team-size", help="Known engineering team size."),
    timeline_weeks: Optional[int] = typer.Option(None, "--timeline-weeks", help="Target timeline in weeks."),
    save_to: Optional[Path] = typer.Option(None, "--save", help="Optional file path to save the rendered document."),
) -> None:
    """Run the full 15-step pipeline and print (and optionally save) the design document."""
    request = FeatureRequest(
        description=description,
        output_format=output_format,
        team_size=team_size,
        timeline_weeks=timeline_weeks,
    )

    try:
        with console.status("[bold green]Running full design pipeline (15 steps)..."):
            workflow = _build_workflow()
            title, sections = workflow.run(request)
            rendered = document_service.render_document(title, sections, output_format)
    except MissingAPIKeyError as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except LLMRequestError as exc:
        console.print(f"[bold red]LLM request failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if output_format == OutputFormat.MARKDOWN:
        console.print(Markdown(rendered))
    else:
        console.print(rendered)

    if save_to is not None:
        save_to.write_text(rendered, encoding="utf-8")
        console.print(f"\n[bold green]Saved to[/bold green] {save_to}")


@cli.command()
def interactive() -> None:
    """Interactive mode: prompts for a feature request, then runs the full pipeline."""
    description = Prompt.ask("[bold cyan]Describe the feature you want designed[/bold cyan]")
    design(description=description, output_format=OutputFormat.MARKDOWN, team_size=None, timeline_weeks=None, save_to=None)


if __name__ == "__main__":
    cli()
