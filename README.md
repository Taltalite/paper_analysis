# Paper Analysis

This repository has been refactored in three phases from a small CrewAI demo into a minimal end-to-end research paper analysis system.

Current status: Phase 3 is complete.

- CrewAI remains the analysis runtime.
- Plain-text and PDF inputs are supported.
- The backend owns job state and analysis artifacts.
- The frontend is a thin React/Vite UI over the backend API.

## Architecture

- `src/paper_analysis/domain/`
  enums, domain models, and typed request/response schemas
- `src/paper_analysis/adapters/`
  LLM, parser, and storage adapters
- `src/paper_analysis/runtime/`
  CrewAI runtime, reusable 2-agent runner, and specialized pipelines
- `src/paper_analysis/services/`
  analysis orchestration, artifact persistence, and job lifecycle logic
- `src/paper_analysis/api/`
  FastAPI app, dependency wiring, and HTTP routes
- `web/`
  React/Vite frontend for upload, polling, markdown preview, and downloads

## Supported Inputs

- `.txt`
- `.md`
- `.pdf`

## Runtime Shape

The reusable base remains a 2-agent pipeline:

- `reader`
  extracts grounded notes from selected source text
- `analyst`
  produces the final structured analysis

For research-paper analysis, the backend pipeline does:

1. Parse the source document through the parser abstraction.
2. Extract structure such as abstract, introduction, method, experimental setup, results, conclusion, and figures.
3. Narrow LLM usage to the highest-value sections instead of resending the whole document.
4. Run the CrewAI 2-agent analysis on the focused text.
5. Persist markdown, JSON, and parsed-markdown artifacts under the job workspace.

## API

The frontend only depends on these backend endpoints:

- `POST /api/analysis/jobs`
- `GET /api/analysis/jobs/{job_id}`
- `GET /api/analysis/jobs/{job_id}/report`
- `GET /api/analysis/jobs/{job_id}/artifact`

The backend remains the only source of truth for:

- job status
- uploaded source files
- markdown reports
- JSON results
- parsed PDF markdown artifacts

## Runtime Config

Runtime host and port settings are now centralized in:

- `config/app.json`

Current default values:

```json
{
  "backend": {
    "host": "127.0.0.1",
    "port": 8010
  },
  "frontend": {
    "host": "127.0.0.1",
    "port": 5173
  }
}
```

If you need to change the backend or frontend port, edit this file and rerun the corresponding script.

## Running

### 1. Local File Workflow

Do not run `uv run kickoff` directly in this repository.

Use:

```bash
bash scripts/codex_run.sh
```

Default behavior:

- input: `input/sample_paper.txt`
- output markdown: `output/report.md`
- output json: `output/report.json`

### 2. PDF Example

To run the bundled PDF example:

```bash
INPUT_PATH=input/template.pdf \
OUTPUT_MARKDOWN_PATH=output/template_report.md \
OUTPUT_JSON_PATH=output/template_report.json \
bash scripts/codex_run.sh
```

This produces:

- `output/template_report.md`
- `output/template_report.json`
- `output/template_report.parsed.md`

### 3. Backend API

Start the FastAPI server:

```bash
bash scripts/codex_run_api.sh
```

The backend listens on:

- `http://127.0.0.1:8010`

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### 4. Frontend Web App

Install frontend dependencies once:

```bash
cd web
npm install
```

Start the Vite dev server:

```bash
cd ..
bash scripts/codex_run_web.sh
```

Default frontend URL:

- `http://127.0.0.1:5173`

If that port is occupied, Vite may pick the next available local port.

The frontend reads its API base URL from `config/app.json` through the Vite config, so you do not need to edit frontend source files when changing the backend port.

## Frontend Scope

The current UI intentionally stays minimal:

- upload a source document
- submit an analysis job
- poll and display job status
- render markdown report
- download markdown
- download JSON
- download parsed markdown when the input is a PDF

The frontend does not persist business state outside the current page session.

## LLM Configuration

Provider-specific wiring is hidden behind `src/paper_analysis/adapters/llm/`.

Currently implemented:

- openai-compatible adapter

Expected environment variables when using it directly:

- `OPENAI_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`

If these are not set, CrewAI still uses its normal environment-based resolution.

## Tests

Run unit tests:

```bash
UV_CACHE_DIR=.uv-cache XDG_CACHE_HOME=.cache uv run python -m unittest discover -s tests/unit -p 'test_*.py'
```

Run integration tests:

```bash
UV_CACHE_DIR=.uv-cache XDG_CACHE_HOME=.cache uv run python -m unittest discover -s tests/integration -p 'test_*.py'
```

Current coverage includes:

- schema defaults
- parser contracts
- LLM adapter contract
- analysis service orchestration
- pipeline happy paths
- FastAPI health route
- FastAPI job creation, completion, report retrieval, and artifact retrieval

## Output Artifacts

For plain-text input:

- markdown report
- JSON result

For PDF input:

- parsed markdown artifact with extracted structure
- markdown research-paper analysis report
- JSON result with structured analysis fields

## Phase 3 Notes

- `api/routes/analysis.py` exposes a stable job-oriented API surface.
- `services/job_service.py` owns upload persistence, status transitions, analysis execution, and artifact access.
- `adapters/storage/job_store.py` now supports local file-backed job persistence.
- `web/` remains intentionally thin and does not know about CrewAI internals.
- The Phase 1 and Phase 2 local file workflow remains compatible.
