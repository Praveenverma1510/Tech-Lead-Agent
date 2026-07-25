# AI Tech Lead Agent

An AI agent that behaves like a Senior Tech Lead / Solutions Architect: give it a
one-line feature request and it produces a **complete technical design document** —
requirement analysis, architecture, database schema, API design, security plan,
scalability/reliability strategy, risk analysis, sprint plan, testing strategy,
deployment plan, monitoring strategy, and more.

Runs entirely on **free LLM providers** (Groq by default).

```
"Build an online payment system."
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  15-step reasoning pipeline (DesignWorkflow)                │
│  analyse → clarify → assume → architecture → db → api →     │
│  security → scalability/reliability/risk → deployment →     │
│  monitoring → roadmap → testing → future improvements       │
└───────────────────────────────────────────────────────────┘
        │
        ▼
Complete Markdown / JSON / HTML / PDF-ready design document
```

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Groq API Key Setup](#groq-api-key-setup)
- [Running the API](#running-the-api)
- [Running the Streamlit UI](#running-the-streamlit-ui)
- [Running the CLI](#running-the-cli)
- [Example API Requests](#example-api-requests)
- [Example CLI Usage](#example-cli-usage)
- [Testing](#testing)
- [Using Other Free Providers](#using-other-free-providers)
- [Error Handling](#error-handling)
- [Future Improvements](#future-improvements)

## Features

- **15-step multi-stage reasoning pipeline** — each design concern (architecture,
  database, API, security, scalability...) gets its own focused LLM call, using
  earlier steps as context, so the final document is internally consistent.
- **Multiple output formats** — Markdown, JSON, HTML, and PDF-ready Markdown.
- **FastAPI HTTP API** — `POST /analyse`, `POST /design`, `POST /generate`, `GET /health`.
- **Streamlit web UI** — form-based input, tabbed section browser, and one-click download of the generated document.
- **Rich CLI** — `python main.py` (interactive) or scriptable sub-commands.
- **Pluggable LLM providers** — Groq (default), OpenRouter, Gemini, or local Ollama;
  swapping providers is a one-line `.env` change.
- **Clean layered architecture** — config / models / prompts / services / agents /
  workflows / api / cli, each with a single responsibility.
- **Retry with backoff** on transient LLM/network failures; clean error envelopes
  for missing API keys, rate limits, and invalid input.
- **Pytest suite** covering services, the agent, the workflow, and the API — all
  using a fake LLM client, so tests run offline with zero API cost.

## Architecture

Clean Architecture, top to bottom:

| Layer | Package | Responsibility |
|---|---|---|
| Configuration | `app/config` | Load & validate environment variables (`.env`) |
| Models | `app/models` | Pydantic request/response/document schemas |
| Prompts | `app/prompts` | One prompt template per reasoning step |
| Services | `app/services` | LLM provider clients + document rendering |
| Agents | `app/agents` | `TechLeadAgent` — one method per reasoning step |
| Workflows | `app/workflows` | `DesignWorkflow` — orchestrates all 15 steps |
| API | `app/api` | FastAPI routes |
| UI | `app/ui` | Streamlit web interface |
| CLI | `app/cli` | Typer commands |

The **agent never decides step order** — it just executes single steps. The
**workflow never talks to the LLM directly** — it only calls agent methods and
threads state between them. This separation keeps each layer independently
testable and lets you reorder/parallelize/extend the pipeline without touching
prompt or LLM-provider code.

### Architecture Diagram

```
                     ┌─────────────┐
                     │   Client    │  (HTTP / CLI)
                     └──────┬──────┘
                            │
                 ┌──────────┴───────────┐
                 │                      │
           ┌─────▼─────┐         ┌──────▼──────┐
           │ FastAPI    │         │  Typer CLI  │
           │ app/api    │         │  app/cli    │
           └─────┬─────┘         └──────┬──────┘
                 │                      │
                 └──────────┬───────────┘
                            ▼
                  ┌───────────────────┐
                  │  DesignWorkflow    │  app/workflows
                  │  (15-step pipeline)│
                  └─────────┬──────────┘
                            ▼
                  ┌───────────────────┐
                  │  TechLeadAgent     │  app/agents
                  └─────────┬──────────┘
                            ▼
                  ┌───────────────────┐
                  │  LLMClient         │  app/services/llm_client.py
                  │  (Groq / OpenRouter │
                  │   / Gemini / Ollama)│
                  └─────────┬──────────┘
                            ▼
                  ┌───────────────────┐
                  │  Free LLM Provider  │
                  └───────────────────┘
```

## Folder Structure

```
tech_lead_agent/
├── app/
│   ├── agents/
│   │   └── tech_lead_agent.py       # One method per reasoning step
│   ├── api/
│   │   └── main.py                  # FastAPI app + routes
│   ├── cli/
│   │   └── cli.py                   # Typer CLI commands
│   ├── config/
│   │   └── settings.py              # Env loading + validation
│   ├── models/
│   │   └── schemas.py               # Pydantic request/response models
│   ├── prompts/
│   │   └── templates.py             # Prompt templates per step
│   ├── services/
│   │   ├── llm_client.py            # Provider clients (Groq/OpenRouter/Gemini/Ollama)
│   │   └── document_service.py      # Parsing + Markdown/JSON/HTML/PDF rendering
│   ├── ui/
│   │   └── streamlit_app.py         # Streamlit web UI (input form + results)
│   ├── utils/
│   │   └── logger.py                # Centralized logging setup
│   └── workflows/
│       └── design_workflow.py       # Orchestrates all 15 steps
├── tests/
│   ├── test_agent_and_workflow.py
│   ├── test_api.py
│   ├── test_document_service.py
│   └── test_settings.py
├── docs/
│   └── ARCHITECTURE.md
├── examples/
│   └── example_request.json
├── main.py                          # `python main.py` entrypoint (interactive CLI)
├── .env.example
├── requirements.txt
└── README.md
```

## Installation

Requires **Python 3.12+**.

```bash
git clone <your-repo-url> tech_lead_agent
cd tech_lead_agent

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# now edit .env and add your GROQ_API_KEY (see below)
```

## Groq API Key Setup

1. Go to [console.groq.com/keys](https://console.groq.com/keys) and sign up (free).
2. Create a new API key.
3. Open `.env` and set:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
4. That's it — no billing information required for the free tier.

## Running the API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs will be available at `http://localhost:8000/docs`.

## Running the Streamlit UI

```bash
streamlit run app/ui/streamlit_app.py
```

This opens a browser at `http://localhost:8501` with:

- A form to enter the feature description, output format, optional team size,
  and optional timeline.
- One-click example buttons to try the agent immediately.
- A sidebar showing the active provider/model and whether the API key is configured.
- Results split into three tabs:
  - **Sections** — every design section in its own expandable card, plus clarifying
    questions and assumptions.
  - **Full Document** — the complete rendered document (Markdown/HTML/JSON view).
  - **Download** — download the generated document in the selected format.

The UI calls the exact same `DesignWorkflow` used by the API and CLI — it's a thin
presentation layer only, so anything that improves the pipeline improves the UI too.

> The Streamlit UI runs the pipeline **in-process** (it does not require the FastAPI
> server to be running separately).

## Running the CLI

```bash
# Interactive mode
python main.py

# Direct sub-commands
python -m app.cli.cli analyse "Build an online payment system."
python -m app.cli.cli design "Build an online payment system." --format markdown
python -m app.cli.cli design "Build a chat application." --format json --save design.json
python -m app.cli.cli design "Build a ride-sharing app." --team-size 6 --timeline-weeks 12
```

## Example API Requests

**Health check**
```bash
curl http://localhost:8000/health
```

**Analyse only (steps 1-4)**
```bash
curl -X POST http://localhost:8000/analyse \
  -H "Content-Type: application/json" \
  -d '{"description": "Build an online payment system."}'
```

**Full design document**
```bash
curl -X POST http://localhost:8000/design \
  -H "Content-Type: application/json" \
  -d '{
        "description": "Build an online payment system.",
        "output_format": "markdown",
        "team_size": 5,
        "timeline_weeks": 10
      }'
```

## Example Response (abridged)

```json
{
  "feature_title": "Online payment system - Technical Design Document",
  "output_format": "markdown",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "sections": {
    "requirement_analysis": "### Problem Statement\n...",
    "clarifying_questions": ["What payment volume is expected at launch?", "..."],
    "assumptions": ["Assume PCI-DSS SAQ-A compliance via a hosted payment gateway.", "..."],
    "high_level_architecture": "...",
    "architecture_diagram_ascii": "```\n[Client] -> [API Gateway] -> ...\n```",
    "...": "..."
  },
  "rendered_document": "# Online payment system - Technical Design Document\n\n## 1. Requirement Analysis\n..."
}
```

See `examples/example_request.json` for a ready-to-use request body.

## Testing

```bash
pytest -v
```

All tests run **offline** — they inject a `FakeLLMClient` (see
`tests/test_agent_and_workflow.py`) instead of calling a real provider, so no
API key is required to run the suite.

## Using Other Free Providers

Change `LLM_PROVIDER` in `.env`:

| Provider | `.env` setting | Notes |
|---|---|---|
| Groq (default) | `LLM_PROVIDER=groq` | Fastest, generous free tier |
| OpenRouter | `LLM_PROVIDER=openrouter` | Use a model with a `:free` suffix |
| Gemini | `LLM_PROVIDER=gemini` | Free tier via Google AI Studio |
| Ollama | `LLM_PROVIDER=ollama` | Fully local, no API key, requires `ollama serve` running |

## Error Handling

The system explicitly handles:

- **Missing API key** → `MissingAPIKeyError`, returned as HTTP 400 with a clear message.
- **Rate limits / transient network failures** → automatic retry with exponential
  backoff (`MAX_RETRIES` in `.env`), then `LLMRequestError` → HTTP 502.
- **Invalid requests / empty prompts** → rejected by Pydantic validation → HTTP 422.
- **Timeouts** → configurable via `REQUEST_TIMEOUT_SECONDS`.
- **Unexpected errors** → caught by a global FastAPI exception handler, returned
  as a clean JSON error instead of a stack trace.

## Future Improvements

- Swap the hand-rolled sequential pipeline for a real LangGraph `StateGraph`
  (the `WorkflowState` dataclass in `design_workflow.py` was designed to make
  this a mechanical refactor).
- Stream section-by-section output over Server-Sent Events / WebSockets instead
  of waiting for the full pipeline to finish.
- Cache LLM responses per feature description to cut cost on repeated requests.
- Add a lightweight web UI on top of the existing FastAPI backend.
- Support multi-turn refinement ("regenerate just the database schema section").
