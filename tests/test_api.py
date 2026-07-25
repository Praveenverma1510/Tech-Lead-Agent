"""
Tests for app.api.main FastAPI endpoints.

We monkeypatch `app.api.main.get_llm_client` to return a fake client so
these tests never hit a real network endpoint or require a real API key.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import main as api_main
from tests.test_agent_and_workflow import FakeLLMClient


@pytest.fixture(autouse=True)
def _patch_llm_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the real provider factory with one that returns a FakeLLMClient."""
    monkeypatch.setattr(api_main, "get_llm_client", lambda settings=None: FakeLLMClient())


@pytest.fixture()
def client() -> TestClient:
    return TestClient(api_main.app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "provider" in body


def test_analyse_endpoint_returns_expected_shape(client: TestClient) -> None:
    response = client.post("/analyse", json={"description": "Build an online payment system."})
    assert response.status_code == 200
    body = response.json()
    assert body["requirement_analysis"]
    assert isinstance(body["clarifying_questions"], list)
    assert isinstance(body["assumptions"], list)


def test_analyse_endpoint_rejects_blank_description(client: TestClient) -> None:
    response = client.post("/analyse", json={"description": "   "})
    assert response.status_code == 422  # Pydantic validation error


def test_design_endpoint_returns_full_document(client: TestClient) -> None:
    response = client.post(
        "/design",
        json={"description": "Build an online payment system.", "output_format": "markdown"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feature_title"] == "Online payment system - Technical Design Document"
    assert "# Online payment system" in body["rendered_document"]
    assert body["sections"]["requirement_analysis"]


def test_design_endpoint_supports_json_format(client: TestClient) -> None:
    response = client.post(
        "/design",
        json={"description": "Build a chat application.", "output_format": "json"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["output_format"] == "json"
    # rendered_document should itself be a JSON string containing the sections.
    assert "requirement_analysis" in body["rendered_document"]


def test_generate_endpoint_is_alias_for_design(client: TestClient) -> None:
    response = client.post("/generate", json={"description": "Build a URL shortener."})
    assert response.status_code == 200
    body = response.json()
    assert body["feature_title"].endswith("Technical Design Document")
