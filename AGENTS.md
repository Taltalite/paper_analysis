# AGENTS.md

For any local execution, do not call `uv run kickoff` directly.
Always use `bash scripts/codex_run.sh` so uv cache, proxy env, and telemetry settings are consistent.

## Mission

This repository is evolving from a small CrewAI text-analysis demo into a production-oriented research paper analysis system.

The long-term target is:

- backend: Python service with CrewAI-based multi-agent runtime
- frontend: simple web app for PDF upload, job status, markdown visualization, and markdown download
- runtime: general text analysis base first, then specialized research-paper analysis pipeline
- adapters: unified LLM abstraction and parser abstraction
- source of truth: backend only; frontend must not own persistent workflow state

## Current priority

Always work in phases and preserve working behavior.

### Phase 1
Refactor the current 2-agent plain-text analysis demo into a reusable general text-analysis base.

### Phase 2
Add PDF parsing and structured markdown output, then specialize the base into a research-paper analysis tool.

### Phase 3
Add a backend API and a lightweight frontend web app with unified contracts.

Do not jump to phase 3 before phase 1 and 2 are stable.

---

## Non-negotiable architecture rules

1. Keep CrewAI as the agent framework.
2. Do not replace the project with another orchestration framework.
3. Keep domain logic out of routes and CLI entrypoints.
4. LLM providers must be hidden behind a unified adapter interface.
5. PDF/text parsing must be hidden behind parser interfaces.
6. Backend is the only source of truth for job state and artifacts.
7. Frontend is stateless except for current UI state.
8. Use explicit schemas for API input/output.
9. Prefer incremental refactors over rewrites.
10. Preserve existing runnable features unless they are replaced compatibly.

---

## Preferred repository shape

Target structure:

- `src/paper_analysis/domain/`:
  domain models, enums, request/response schemas
- `src/paper_analysis/adapters/`:
  llm adapters, parser adapters, storage adapters
- `src/paper_analysis/runtime/`:
  CrewAI runtime, flow builders, pipeline orchestration
- `src/paper_analysis/services/`:
  application services and job orchestration
- `src/paper_analysis/api/`:
  FastAPI app and routes
- `src/paper_analysis/web/` or top-level `web/`:
  frontend app
- `tests/`:
  unit and integration tests

---

## Coding standards

### Python
- Python 3.11+
- use type hints everywhere
- use pydantic for input/output schemas
- use dataclass or pydantic for domain entities
- prefer small, composable classes and functions
- avoid giant files and giant functions
- avoid implicit globals
- avoid loose dictionaries when a schema is appropriate

### API
- FastAPI routes should remain thin
- validation belongs in schemas/services
- orchestration belongs in services/runtime
- adapters isolate third-party SDK details

### CrewAI
- flows should orchestrate; they should not contain all business logic
- tools should be narrow and testable
- prompts/config should live in dedicated config files where possible
- new agents must have a clear responsibility boundary
- add agents only when they reduce complexity or improve quality materially

### Frontend
- keep frontend simple
- upload PDF
- show job status
- render markdown
- download markdown
- no persistent business state outside backend
- no frontend-generated analysis result snapshots as source of truth

---

## Token-efficiency rules

This project should not spend tokens uniformly across the whole document.

Prefer:
- cheap structural parsing first
- targeted extraction of key sections
- deeper LLM analysis only on relevant segments
- explicit narrowing for research-paper workflows
- reuse parsed structure and intermediate artifacts when possible

Avoid:
- sending full long PDFs repeatedly
- duplicating the same large prompt across agents
- broad expensive summarization before section selection

---

## Workflow for Codex

For every substantial task:

1. inspect current code first
2. explain the plan briefly
3. edit the smallest set of files needed
4. run relevant tests or commands
5. summarize changed files and verification steps
6. update README and/or PLANS.md when behavior changes

For multi-step work:
- keep `PLANS.md` updated
- mark completed steps
- leave clear next steps

---

## Testing expectations

Add tests for:
- schema validation
- parser contracts
- adapter contracts
- service orchestration
- API happy path

Do not add brittle tests that depend on live LLM calls unless explicitly requested.

Prefer mocks/fakes for provider tests.

---

## Forbidden moves

Do not:
- hardcode vendor-specific LLM logic in business services
- couple frontend components directly to CrewAI internals
- put PDF parsing logic directly in API routes
- make the frontend the source of truth for job state
- introduce heavy infrastructure before the local version runs
- delete working modules without replacement
- silently change public interfaces

---

## Definition of done for each phase

A phase is done only if:
- the feature runs locally
- the architecture remains decoupled
- tests cover the critical path
- README is updated
- the next phase has a clear starting point