# Architecture

## Layering & Dependency Direction

```
api/cli  →  workflows  →  agents  →  services (llm_client, document_service)  →  models / prompts / config / utils
```

Dependencies only ever point "downward". `app.services.llm_client` has no idea
`app.workflows` exists; `app.agents.tech_lead_agent` has no idea whether it's
being called from the API or the CLI. This means:

- You can unit test any layer by mocking only the layer directly below it.
- Adding a new interface (e.g. a Slack bot) only requires a new thin adapter
  in a new package that calls `DesignWorkflow` — zero changes to existing code.

## Why a 15-step pipeline instead of one giant prompt?

A single prompt asking an LLM to produce architecture + database + API +
security + sprint planning all at once tends to produce shallow, generic
output for each section because the model is splitting its attention budget
across many unrelated concerns simultaneously. Splitting into one focused
call per concern, while feeding forward the outputs of earlier steps as
context, produces:

- More specific, detailed output per section (the model can "think" about
  just database design for one whole completion).
- A consistent design (the API design step reads the requirement analysis;
  the deployment step reads the technology recommendations; etc.).
- Predictable, parseable output shapes per step (some steps request bullet
  lists, others request Markdown tables, matched to what's easy to parse
  and easy for a human to scan).

Trade-off: more LLM calls per document (~16 calls) means higher latency and
token cost per request than one giant prompt. Given Groq's free tier and
low latency, this trade-off favors quality.

## State management

`app.workflows.design_workflow.WorkflowState` is a plain mutable dataclass
threaded through every step function. It intentionally mirrors what a
LangGraph `StateGraph`'s typed state would look like, so if/when this project
migrates to real LangGraph orchestration (for conditional branching, human-in
-the-loop review between steps, or parallel step execution), each
`_step_*` method becomes a graph node with minimal rework.

## Provider abstraction

`app.services.llm_client.LLMClient` is an abstract base class with exactly
one method: `complete(system_prompt, user_prompt) -> str`. Four concrete
implementations exist (Groq, OpenRouter, Gemini, Ollama). `get_llm_client()`
is the single factory function that reads `Settings.llm_provider` and
constructs the right one. No other file in the codebase imports a provider
SDK directly — this is what makes provider-swapping a `.env` change instead
of a code change.

## Rendering pipeline

`app.services.document_service` has two responsibilities kept deliberately
separate from parsing/orchestration:

1. **Parsing** LLM free text into structured Python data (`parse_bullet_list`,
   the risk/edge-case and roadmap section splitters in the agent).
2. **Rendering** a validated `DesignDocumentSections` model into one of four
   output formats. A tiny dependency-free Markdown→HTML converter handles the
   predictable subset of Markdown our prompts produce (headings, bullets,
   fenced code blocks) rather than depending on a full CommonMark library.
