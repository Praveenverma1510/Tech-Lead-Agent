"""
LLM client abstraction.

Design decision: we define a single `LLMClient` interface (`complete`) and
implement it once per provider. Everything else in the codebase (agent,
workflow) only ever talks to `LLMClient`, never to a provider SDK directly.
This means swapping Groq for OpenRouter/Gemini/Ollama is a one-line config
change, and unit tests can inject a fake client instead of hitting a real
network endpoint.

All providers used here are free-tier / zero-cost:
- Groq: generous free API (default, fastest).
- OpenRouter: has free-tagged models (":free" suffix).
- Gemini: has a free tier via Google AI Studio.
- Ollama: fully local and free, no API key required.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from app.config.settings import MissingAPIKeyError, Settings, get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMRequestError(RuntimeError):
    """Raised when an LLM call fails after all retries (network, rate limit, etc.)."""


class LLMClient(ABC):
    """Common interface every provider-specific client implements."""

    provider_name: str
    model_name: str

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's text completion for a single-turn prompt."""
        raise NotImplementedError


def _retry_call(fn, *, max_retries: int, description: str):
    """Shared retry-with-backoff wrapper used by every provider implementation.

    Why centralized: rate limits and transient network failures are common
    with free-tier LLM APIs, and every provider needs the same
    retry/backoff behaviour. Keeping it in one place avoids copy-pasted
    (and inevitably inconsistent) retry logic per provider.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentionally broad: we normalize all provider errors below
            last_error = exc
            wait_seconds = min(2 ** attempt, 10)
            logger.warning(
                "LLM call failed (%s) on attempt %d/%d: %s. Retrying in %ds.",
                description,
                attempt,
                max_retries,
                exc,
                wait_seconds,
            )
            if attempt < max_retries:
                time.sleep(wait_seconds)

    raise LLMRequestError(
        f"{description} failed after {max_retries} attempts. Last error: {last_error}"
    ) from last_error


class GroqClient(LLMClient):
    """Default provider: Groq, using the official `groq` Python SDK."""

    def __init__(self, settings: Settings) -> None:
        try:
            from groq import Groq  # Imported lazily so the package is only required if actually used.
        except ImportError as exc:  # pragma: no cover - exercised only when dependency missing
            raise RuntimeError(
                "The 'groq' package is required for the Groq provider. Install it with: pip install groq"
            ) from exc

        self.provider_name = "groq"
        self.model_name = settings.groq_model
        self._settings = settings
        self._client = Groq(api_key=settings.groq_api_key, timeout=settings.request_timeout_seconds)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        def _call() -> str:
            response = self._client.chat.completions.create(
                model=self.model_name,
                temperature=self._settings.llm_temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise LLMRequestError("Groq returned an empty completion.")
            return content

        return _retry_call(_call, max_retries=self._settings.max_retries, description="Groq completion")


class OpenRouterClient(LLMClient):
    """Optional provider: OpenRouter, called via plain HTTP (OpenAI-compatible schema)."""

    def __init__(self, settings: Settings) -> None:
        import httpx

        self.provider_name = "openrouter"
        self.model_name = settings.openrouter_model
        self._settings = settings
        self._http = httpx.Client(timeout=settings.request_timeout_seconds)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        def _call() -> str:
            resp = self._http.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._settings.openrouter_api_key}"},
                json={
                    "model": self.model_name,
                    "temperature": self._settings.llm_temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise LLMRequestError("OpenRouter returned an empty completion.")
            return content

        return _retry_call(_call, max_retries=self._settings.max_retries, description="OpenRouter completion")


class GeminiClient(LLMClient):
    """Optional provider: Google Gemini free tier, called via plain HTTP."""

    def __init__(self, settings: Settings) -> None:
        import httpx

        self.provider_name = "gemini"
        self.model_name = settings.gemini_model
        self._settings = settings
        self._http = httpx.Client(timeout=settings.request_timeout_seconds)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        def _call() -> str:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model_name}:generateContent?key={self._settings.gemini_api_key}"
            )
            resp = self._http.post(
                url,
                json={
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": self._settings.llm_temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            if not content or not content.strip():
                raise LLMRequestError("Gemini returned an empty completion.")
            return content

        return _retry_call(_call, max_retries=self._settings.max_retries, description="Gemini completion")


class OllamaClient(LLMClient):
    """Optional provider: local Ollama server, no API key required."""

    def __init__(self, settings: Settings) -> None:
        import httpx

        self.provider_name = "ollama"
        self.model_name = settings.ollama_model
        self._settings = settings
        self._http = httpx.Client(timeout=settings.request_timeout_seconds)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        def _call() -> str:
            resp = self._http.post(
                f"{self._settings.ollama_base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "options": {"temperature": self._settings.llm_temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["message"]["content"]
            if not content or not content.strip():
                raise LLMRequestError("Ollama returned an empty completion.")
            return content

        return _retry_call(_call, max_retries=self._settings.max_retries, description="Ollama completion")


_PROVIDER_REGISTRY: dict[str, type[LLMClient]] = {
    "groq": GroqClient,
    "openrouter": OpenRouterClient,
    "gemini": GeminiClient,
    "ollama": OllamaClient,
}


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """Factory: build the configured provider's client.

    Centralizing construction here (instead of instantiating provider
    classes directly in the agent) is what makes provider-swapping a
    one-line config change rather than a code change.
    """
    settings = settings or get_settings()

    try:
        settings.validate()
    except MissingAPIKeyError:
        logger.error("LLM settings validation failed for provider '%s'.", settings.llm_provider)
        raise

    provider_cls = _PROVIDER_REGISTRY.get(settings.llm_provider)
    if provider_cls is None:
        raise MissingAPIKeyError(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
            f"Expected one of: {', '.join(_PROVIDER_REGISTRY)}."
        )

    logger.info("Using LLM provider '%s'.", settings.llm_provider)
    return provider_cls(settings)
