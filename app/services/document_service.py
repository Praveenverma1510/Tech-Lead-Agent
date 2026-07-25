"""
Document assembly and rendering.

This module is responsible for two things that are deliberately kept
separate from the agent/workflow logic:

1. Parsing small structured pieces out of raw LLM text (e.g. turning a
   "- item\\n- item" block into a Python list). Keeping parsing here (not in
   the agent) means the agent stays focused purely on orchestration.
2. Rendering a `DesignDocumentSections` object into the four supported
   output formats (Markdown, JSON, HTML, PDF-ready Markdown).
"""

from __future__ import annotations

import json

from app.models.schemas import DesignDocumentSections, OutputFormat
from app.utils.logger import get_logger

logger = get_logger(__name__)


def parse_bullet_list(raw_text: str) -> list[str]:
    """Parse an LLM response formatted as a "- item" bullet list into a list of strings.

    Defensive by design: LLMs occasionally add stray numbering, asterisks,
    or a preamble line despite instructions. We strip common bullet
    prefixes and drop empty/preamble-looking lines rather than trusting the
    format blindly.
    """
    items: list[str] = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        for prefix in ("- ", "* ", "• "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break
        else:
            # Line without a recognized bullet prefix - skip likely preamble
            # (e.g. "Here are the questions:") rather than including it as an item.
            if cleaned.endswith(":") or len(cleaned.split()) <= 2:
                continue
        # Strip leading numbering like "1. " or "1) " if present.
        import re

        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
        if cleaned:
            items.append(cleaned)
    return items


def derive_title(feature_description: str) -> str:
    """Turn the raw feature request into a short document title.

    e.g. "Build an online payment system." -> "Online Payment System - Technical Design Document"
    """
    title = feature_description.strip().rstrip(".")
    for prefix in ("Build a ", "Build an ", "Build ", "Design a ", "Design an ", "Create a ", "Create an "):
        if title.lower().startswith(prefix.lower()):
            title = title[len(prefix):]
            break
    title = title[0].upper() + title[1:] if title else "Feature"
    return f"{title} - Technical Design Document"


def render_markdown(title: str, sections: DesignDocumentSections) -> str:
    """Render the full design document as Markdown."""

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "_None specified._"

    return f"""# {title}

## 1. Requirement Analysis
{sections.requirement_analysis}

## 2. Clarifying Questions
{bullets(sections.clarifying_questions)}

## 3. Assumptions
{bullets(sections.assumptions)}

## 4. High-Level Architecture
{sections.high_level_architecture}

## 5. Architecture Diagram
{sections.architecture_diagram_ascii}

## 6. Technology Recommendations
{sections.technology_recommendations}

## 7. Database Schema
{sections.database_schema}

## 8. API Design
{sections.api_design}

## 9. Security Considerations
{sections.security_considerations}

## 10. Scalability Plan
{sections.scalability_plan}

## 11. Reliability Strategy
{sections.reliability_strategy}

## 12. Risk Analysis & Edge Cases
{sections.risk_analysis}

{sections.edge_cases}

## 13. Development Roadmap
{sections.sprint_planning}

{sections.task_breakdown}

{sections.timeline}

{sections.team_allocation}

## 14. Testing Strategy
{sections.testing_strategy}

## 15. Deployment Strategy
{sections.deployment_strategy}

## 16. Monitoring Strategy
{sections.monitoring_strategy}

## 17. Future Improvements
{sections.future_improvements}
"""


def render_pdf_ready_markdown(title: str, sections: DesignDocumentSections) -> str:
    """Render Markdown with a print-friendly front matter block (page-break hints).

    "PDF-ready" here means: a title page block, consistent heading levels,
    and explicit page-break markers (`<!-- pagebreak -->`) that tools like
    Pandoc or md-to-pdf converters respect, so the Markdown converts cleanly
    to a well-paginated PDF without further editing.
    """
    base = render_markdown(title, sections)
    front_matter = f"""---
title: "{title}"
author: "AI Tech Lead Agent"
---

<!-- pagebreak -->

"""
    # Insert a page-break hint before each top-level section for cleaner pagination.
    base_with_breaks = base.replace("\n## ", "\n<!-- pagebreak -->\n\n## ")
    return front_matter + base_with_breaks


def render_html(title: str, sections: DesignDocumentSections) -> str:
    """Render the design document as a standalone HTML page.

    We convert the Markdown rendering to HTML using a very small, dependency
    -free converter for headings/bullets/paragraphs/code-fences, rather than
    pulling in a full Markdown library, since the LLM output structure here
    is predictable (headings, bullets, fenced code blocks, tables).
    """
    markdown_text = render_markdown(title, sections)
    html_body = _minimal_markdown_to_html(markdown_text)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 900px;
          margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #1a1a1a; }}
  h1 {{ border-bottom: 3px solid #2b6cb0; padding-bottom: 8px; }}
  h2 {{ border-bottom: 1px solid #cbd5e0; padding-bottom: 4px; margin-top: 36px; }}
  code, pre {{ background: #f5f5f5; border-radius: 4px; }}
  pre {{ padding: 12px; overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #cbd5e0; padding: 6px 10px; text-align: left; }}
  th {{ background: #edf2f7; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""


def _minimal_markdown_to_html(markdown_text: str) -> str:
    """Small, dependency-free Markdown -> HTML converter for our predictable subset.

    Handles: #/##/### headings, fenced code blocks, "- " bullet lists, and
    plain paragraphs. Intentionally does not attempt to handle arbitrary
    Markdown (tables are passed through inside <pre> for readability rather
    than fully parsed) - full CommonMark support is out of scope for a
    lightweight report renderer.
    """
    import html as html_lib

    lines = markdown_text.splitlines()
    out: list[str] = []
    in_code_block = False
    in_list = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                out.append("</pre>")
            else:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                out.append("<pre>")
            in_code_block = not in_code_block
            continue

        if in_code_block:
            out.append(html_lib.escape(line))
            continue

        if stripped.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{html_lib.escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{html_lib.escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{html_lib.escape(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html_lib.escape(stripped[2:])}</li>")
        elif not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{html_lib.escape(stripped)}</p>")

    if in_list:
        out.append("</ul>")
    if in_code_block:
        out.append("</pre>")

    return "\n".join(out)


def render_document(
    title: str,
    sections: DesignDocumentSections,
    output_format: OutputFormat,
) -> str:
    """Dispatch to the correct renderer for the requested output format."""
    if output_format == OutputFormat.MARKDOWN:
        return render_markdown(title, sections)
    if output_format == OutputFormat.JSON:
        return json.dumps(
            {"title": title, "sections": sections.model_dump()},
            indent=2,
            ensure_ascii=False,
        )
    if output_format == OutputFormat.HTML:
        return render_html(title, sections)
    if output_format == OutputFormat.PDF_READY_MARKDOWN:
        return render_pdf_ready_markdown(title, sections)

    # Defensive fallback: should be unreachable because OutputFormat is an Enum,
    # but we avoid silently returning malformed output if it ever happens.
    raise ValueError(f"Unsupported output format: {output_format}")
