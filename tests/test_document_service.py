"""Unit tests for app.services.document_service."""

from __future__ import annotations

import json

from app.models.schemas import DesignDocumentSections, OutputFormat
from app.services import document_service


def test_parse_bullet_list_basic() -> None:
    raw = "- First item\n- Second item\n- Third item"
    assert document_service.parse_bullet_list(raw) == ["First item", "Second item", "Third item"]


def test_parse_bullet_list_strips_numbering_and_alt_bullets() -> None:
    raw = "1. First item\n* Second item\n• Third item"
    assert document_service.parse_bullet_list(raw) == ["First item", "Second item", "Third item"]


def test_parse_bullet_list_skips_preamble_lines() -> None:
    raw = "Here are the questions:\n- Real question one\n- Real question two"
    result = document_service.parse_bullet_list(raw)
    assert "Here are the questions:" not in result
    assert result == ["Real question one", "Real question two"]


def test_parse_bullet_list_handles_empty_input() -> None:
    assert document_service.parse_bullet_list("") == []
    assert document_service.parse_bullet_list("   \n  \n") == []


def test_derive_title_strips_common_prefixes() -> None:
    assert document_service.derive_title("Build an online payment system.") == (
        "Online payment system - Technical Design Document"
    )
    assert document_service.derive_title("Design a chat application") == (
        "Chat application - Technical Design Document"
    )


def _sample_sections() -> DesignDocumentSections:
    return DesignDocumentSections(
        requirement_analysis="Some analysis.",
        clarifying_questions=["What scale?"],
        assumptions=["Assume 10k users."],
        high_level_architecture="Microservices.",
        architecture_diagram_ascii="```\n[Client] -> [API]\n```",
        technology_recommendations="| Layer | Rec |\n|---|---|\n| Backend | FastAPI |",
        database_schema="Postgres.",
        api_design="POST /pay",
        security_considerations="Use TLS.",
        scalability_plan="Scale horizontally.",
        reliability_strategy="99.9% uptime.",
        risk_analysis="### Risk Analysis\nRisk table here.",
        edge_cases="### Edge Cases\n- duplicate payment",
        sprint_planning="### Sprint Planning\nSprint 1...",
        task_breakdown="### Task Breakdown\nTask table",
        timeline="### Timeline\n8 weeks",
        team_allocation="### Team Allocation\n2 backend engineers",
        testing_strategy="Unit + integration tests.",
        deployment_strategy="Blue-green deployment.",
        monitoring_strategy="Prometheus + Grafana.",
        future_improvements="- Add fraud detection",
    )


def test_render_markdown_contains_all_sections() -> None:
    md = document_service.render_markdown("Payment System", _sample_sections())
    assert "# Payment System" in md
    assert "## 1. Requirement Analysis" in md
    assert "Some analysis." in md
    assert "## 17. Future Improvements" in md


def test_render_document_json_round_trips() -> None:
    sections = _sample_sections()
    rendered = document_service.render_document("Payment System", sections, OutputFormat.JSON)
    parsed = json.loads(rendered)
    assert parsed["title"] == "Payment System"
    assert parsed["sections"]["requirement_analysis"] == "Some analysis."


def test_render_document_html_wraps_content() -> None:
    rendered = document_service.render_document("Payment System", _sample_sections(), OutputFormat.HTML)
    assert rendered.startswith("<!DOCTYPE html>")
    assert "<h1>Payment System</h1>" in rendered


def test_render_document_pdf_ready_has_front_matter_and_pagebreaks() -> None:
    rendered = document_service.render_document(
        "Payment System", _sample_sections(), OutputFormat.PDF_READY_MARKDOWN
    )
    assert rendered.startswith("---\ntitle:")
    assert "<!-- pagebreak -->" in rendered
