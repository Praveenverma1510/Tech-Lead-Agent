"""
Application configuration.

Design decision: we centralize *all* environment/configuration access in a
single module so that no other file in the codebase calls `os.getenv`
directly. This keeps configuration auditable, testable (we can monkeypatch
`get_settings`), and prevents secrets from leaking into random modules.

We deliberately use a lightweight dataclass instead of pydantic-settings to
keep the dependency footprint small, but the validation logic below gives us
the same safety guarantees (fail fast if the API key is missing).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load the .env file once, at import time. `override=False` means real
# environment variables (e.g. injected by Docker/CI) always win over the
# .env file, which is the expected behaviour in production deployments.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


class MissingAPIKeyError(RuntimeError):
    """Raised when no LLM provider API key is configured.

    Kept as a distinct exception type (rather than a bare RuntimeError) so
    that API/CLI layers can catch it specifically and return a clean,
    actionable error message instead of a stack trace.
    """


@dataclass(frozen=True)
class Settings:
    """Immutable application settings.

    Frozen so settings can't be mutated accidentally at runtime once loaded,
    which avoids a whole class of "who changed this config mid-request" bugs.
    """

    # --- LLM Provider selection -------------------------------------------------
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq").lower())

    # --- Groq (primary, free-tier friendly) --------------------------------------
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))

    # --- OpenRouter (optional fallback / free models) ----------------------------
    openrouter_api_key: str | None = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    openrouter_model: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    )

    # --- Gemini (optional) --------------------------------------------------------
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

    # --- Ollama (optional, local, no key required) --------------------------------
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1"))

    # --- General app behaviour -----------------------------------------------------
    request_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.3")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))

    def validate(self) -> None:
        """Fail fast if the configured provider has no usable credentials.

        We intentionally do NOT validate at import time (module import
        should never crash a test runner) - callers invoke this explicitly
        at the point where an LLM call is actually about to happen.
        """
        provider_key_map = {
            "groq": self.groq_api_key,
            "openrouter": self.openrouter_api_key,
            "gemini": self.gemini_api_key,
            "ollama": "local",  # Ollama needs no API key, just a reachable server.
        }

        if self.llm_provider not in provider_key_map:
            raise MissingAPIKeyError(
                f"Unknown LLM_PROVIDER '{self.llm_provider}'. "
                f"Expected one of: {', '.join(provider_key_map)}."
            )

        if not provider_key_map[self.llm_provider]:
            raise MissingAPIKeyError(
                f"LLM_PROVIDER is set to '{self.llm_provider}' but no matching API key "
                f"was found in the environment. Copy .env.example to .env and set the "
                f"appropriate key (e.g. GROQ_API_KEY)."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton.

    Cached via lru_cache so we parse environment variables once per process,
    not on every request. Tests that need fresh settings should call
    `get_settings.cache_clear()` after monkeypatching environment variables.
    """
    return Settings()
