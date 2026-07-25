"""Unit tests for app.config.settings."""

from __future__ import annotations

import pytest

from app.config.settings import MissingAPIKeyError, Settings


def test_validate_passes_when_groq_key_present() -> None:
    settings = Settings(llm_provider="groq", groq_api_key="fake-key")
    settings.validate()  # should not raise


def test_validate_raises_when_groq_key_missing() -> None:
    settings = Settings(llm_provider="groq", groq_api_key=None)
    with pytest.raises(MissingAPIKeyError):
        settings.validate()


def test_validate_raises_for_unknown_provider() -> None:
    settings = Settings(llm_provider="not-a-real-provider")
    with pytest.raises(MissingAPIKeyError):
        settings.validate()


def test_validate_passes_for_ollama_without_key() -> None:
    # Ollama is local and needs no API key.
    settings = Settings(llm_provider="ollama")
    settings.validate()  # should not raise
