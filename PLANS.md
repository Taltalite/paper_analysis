# PLANS

## Scope

This file tracks the phased evolution of the current CrewAI demo into a research paper analysis system.

Current rule: preserve the existing runnable behavior until a compatible replacement exists.

## Phase 0 Audit

Status: completed on 2026-04-15

### Current implementation

- The repository already contains a runnable local analysis flow centered on `PaperAnalysisFlow`.
- The current chain is:
  `src/paper_analysis/main.py`
  -> `src/paper_analysis/flow.py`
  -> `src/paper_analysis/crews/content_crew/content_crew.py`
  -> `src/paper_analysis/crews/content_crew/config/*.yaml`
  -> `output/report.md` and `output/report.json`
- `state.py` already defines structured Pydantic output/state models:
  `PaperMetadata`, `ExtractedNotes`, `PaperAnalysisOutput`, `PaperAnalysisState`.
- The crew is no longer the default blog/content template. It has been specialized into a 2-agent academic paper analyzer:
  `reader` extracts notes, `analyst` synthesizes structured output.
- `src/paper_analysis/tools/custom_tool.py` contains two useful custom tools:
  section extraction from plain text and keyword-based evidence lookup.
- `input/sample_paper.txt` and `output/report.{md,json}` show the intended local file-in / report-out workflow.

### Remaining starter-template residue

- `README.md` is still almost entirely the default CrewAI template with placeholder text like `{{crew_name}}`.
- `pyproject.toml` still contains starter metadata such as `description = "paper_analysis using crewAI"` and placeholder author info.
- Script names such as `kickoff`, `run_crew`, and `plot` still reflect template conventions rather than stable product-facing entrypoints.
- Package layout is still close to a single-flow starter project rather than the target architecture in `AGENTS.md`.
- `tests/` exists but is empty.

### Modules to keep

- Keep CrewAI as the runtime foundation.
- Keep the existing two-agent separation as the seed of the analysis pipeline.
- Keep the Pydantic output/state schemas as the basis for stronger domain modeling.
- Keep the custom text tools and evolve them behind clearer parser/tool boundaries.
- Keep local file input/output behavior until a service/API layer replaces it compatibly.

### Modules to refactor

- Refactor `flow.py` so it orchestrates services/runtime only, instead of owning file I/O, report assembly, and domain behavior directly.
- Refactor `state.py` into clearer domain schemas plus runtime/job state.
- Refactor `content_crew.py` and YAML config into a reusable text-analysis runtime instead of a paper-specific crew embedded at top level.
- Refactor `main.py` into a thin CLI entrypoint only.
- Replace starter-template `README.md` with repository-specific documentation once Phase 1 lands.
- Add tests before broadening scope further.

### Current runnable chain

Input:
- `input/sample_paper.txt`

Execution:
- `bash scripts/codex_run.sh`

Observed status during audit:
- The code path is present and prior run artifacts exist in `output/`.
- In the current sandbox, execution is blocked by environment issues outside business logic:
  `uv` cache permissions unless `UV_CACHE_DIR` is redirected, and CrewAI telemetry/proxy connection failures during runtime.
- Conclusion:
  the repository has a coherent local demo path, but runtime verification is environment-sensitive and not yet hardened.

## Delivery Roadmap

Rule for all phases:
- change the smallest viable surface
- preserve compatibility where possible
- add minimal tests
- update `README.md`
- keep `PLANS.md` current

### Phase 1: General Text Analysis Base

Goal:
- turn the current 2-agent plain-text paper demo into a reusable general text-analysis base without losing the existing local workflow

Checkpoint:
- 2026-04-15: target package skeleton added for `domain/`, `adapters/`, `runtime/`, `services/`, `api/`, `web/`, and split test folders without moving the existing runnable flow yet
- 2026-04-15: existing parsing, CrewAI execution, and artifact writing moved behind service/runtime layers; `flow.py` reduced to a thin wrapper over the Phase 1 application path

Planned work:
- introduce target package slices under `src/paper_analysis/`:
  `domain/`, `adapters/`, `runtime/`, `services/`
- split current schemas into:
  generic text analysis request/result schemas
  paper-specific analysis schemas layered on top
  runtime/job state schemas
- move file loading, report building, and orchestration support out of `flow.py` into services
- define a unified LLM adapter interface and keep provider-specific configuration out of business logic
- keep the existing CrewAI runtime, but reorganize crew construction so it can support more than one analysis workflow
- preserve a compatible CLI path for `input/sample_paper.txt -> output/report.{md,json}`
- add minimal tests for:
  schemas
  text tool behavior
  service orchestration with fakes/mocks

Acceptance criteria:
- local plain-text analysis still runs through a single supported command
- flow/crew code is thinner and reusable
- provider details are behind an adapter interface
- tests cover the critical happy path without live LLM dependence
- `README.md` documents the actual project instead of template text

Status:
- completed on 2026-04-15
- retained the txt-based local runnable path
- moved parsing, runtime orchestration, and artifact writing behind `adapters/`, `runtime/`, and `services/`
- added minimal unit tests and replaced the starter README

Rollback point:
- the old file-based kickoff path remains callable until the new service-backed path is verified

### Phase 2: Paper-Specific Pipeline and PDF -> Structured Markdown

Goal:
- specialize the text-analysis base into a research paper analysis workflow with parser abstractions and token-efficient processing

Planned work:
- add parser interfaces under `adapters/` for plain text and PDF parsing
- introduce paper document structure models:
  sections, metadata hints, extracted artifacts
- add a paper-analysis service that narrows analysis to relevant sections instead of repeatedly sending full documents
- evolve output from simple report text to structured markdown artifacts with explicit sections and reusable intermediate data
- keep current plain-text input support while adding PDF input
- add minimal tests for parser contracts and paper-analysis service behavior

Acceptance criteria:
- plain text and PDF both work through the same analysis contract
- output is structured markdown plus machine-readable JSON
- the analysis path reuses parsed structure and avoids full-document repeated prompting
- the paper pipeline remains decoupled from provider/parser implementation details

Status:
- completed on 2026-04-15
- added parser abstractions for plain text and PDF under `adapters/parser/`
- implemented a PDF parser that extracts title, metadata, section-like structure, and a parsed markdown intermediate artifact
- added a research-paper pipeline that narrows agent input to selected sections instead of repeatedly sending the whole document
- preserved the existing txt/md workflow while adding PDF support through the same service/runtime path
- verified the bundled PDF example through `scripts/codex_run.sh`
- 2026-04-17 hardening update:
  replaced the earlier font-size-heavy PDF heuristics with a more stable path:
  sequential block extraction -> rule-based coarse structure draft -> document-structuring agent for semantic correction -> downstream text/figure analysis agents
- 2026-04-17 hardening update:
  parser now persists ordered text/image blocks plus a coarse structure draft into `ParsedDocument.metadata`, and the research pipeline consumes the refined structure before running the existing analysis agents

Rollback point:
- existing plain-text path remains available while PDF support is introduced

### Phase 3: Backend API and Lightweight Web App

Goal:
- add a backend service and stateless frontend on top of the stabilized analysis pipeline

Planned work:
- add `api/` with FastAPI app, thin routes, and explicit request/response/job schemas
- add job orchestration and local persistence for status/artifacts
- make backend the only source of truth for job state and outputs
- add a lightweight web UI for:
  PDF upload
  job status
  markdown visualization
  markdown download
- keep frontend contracts aligned with backend schemas only
- add API happy-path tests

Acceptance criteria:
- a local user can submit a paper, poll job status, view markdown, and download results
- backend owns job state and artifact storage
- frontend does not persist business state beyond current UI state
- API contracts are typed and explicit

Status:
- completed on 2026-04-15
- added a FastAPI backend under `src/paper_analysis/api/`
- added a file-backed job store and job service for upload persistence, status transitions, and artifact retrieval
- added typed job/report/artifact schemas for the backend API
- added a minimal React/Vite frontend under `web/` for upload, polling, markdown preview, and downloads
- added integration tests for backend health and job happy path
- verified backend startup, frontend production build, and frontend dev-server startup path
  note: sandbox networking limited direct local HTTP smoke checks across isolated exec sessions, so endpoint behavior was validated primarily through FastAPI integration tests

Rollback point:
- CLI/local flow continues to function while API and web layers are introduced

## Immediate Next Loop

Next implementation loop can focus on hardening, not architecture reshaping:

1. improve PDF structure extraction on more varied publisher layouts and multi-column figure/table pages
2. strengthen document-structuring prompts and fallbacks using more real-paper samples
3. add richer job error reporting and optional retry semantics
4. add backend integration coverage with the real analysis service behind feature flags or fakes for provider calls
5. refine the frontend UX without moving business logic out of the backend
