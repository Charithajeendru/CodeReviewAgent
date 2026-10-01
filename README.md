# CodeReview Agent

A production-oriented multi-agent code review platform built with FastAPI and a modular language-aware review pipeline.

## Quick start (Windows PowerShell)

Run these commands from the `CodeReviewAgent` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, also from `CodeReviewAgent`, serve the frontend:

```powershell
python -m http.server 8080 --directory frontend
```

Open the frontend at `http://127.0.0.1:8080`. Its API URL defaults to `http://127.0.0.1:8000/api`; the backend health endpoint is `http://127.0.0.1:8000/api/health`.

The frontend is a static JavaScript app with no build-time environment support. To use a different backend URL, set `window.CODE_REVIEW_API_URL` before `config.js` is loaded in `frontend/index.html`, for example:

```html
<script>window.CODE_REVIEW_API_URL = "https://api.example.com/api";</script>
<script src="config.js"></script>
```

## Configuration and limits

`.env.example` documents supported backend environment variables. The code limits default to 250,000 characters per single review and per batch file, 20 batch files, 1,000,000 total batch characters, and 5,000,000 request-body bytes. Set `MAX_CODE_CHARS`, `MAX_BATCH_FILES`, `MAX_BATCH_FILE_CHARS`, `MAX_BATCH_TOTAL_CHARS`, and `MAX_REQUEST_BYTES` in `.env` to override them. Keep the frontend `maxCodeChars` value in `frontend/config.js` aligned with `MAX_CODE_CHARS` for early upload feedback; the backend remains authoritative.

Project reviews accept structured relative paths at `POST /api/reviews/project`. Defaults are 100 files, 250,000 UTF-8 bytes per file, 2,000,000 total UTF-8 bytes, 512 path characters, and 255 filename characters. Related-file context is limited to 50,000 characters total and 12,000 per related file. These settings can be changed with `MAX_PROJECT_FILES`, `MAX_PROJECT_FILE_BYTES`, `MAX_PROJECT_TOTAL_BYTES`, `MAX_PROJECT_PATH_CHARS`, `MAX_PROJECT_FILENAME_CHARS`, `MAX_PROJECT_CONTEXT_CHARS`, and `MAX_PROJECT_RELATED_FILE_CHARS`.

`GET /api/languages` reports registry capabilities. The registry contains Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, PHP, Ruby, Kotlin, Swift, SQL, HTML, CSS, Shell, and PowerShell. Deterministic pattern checks can run over registered source files; they are heuristics, not language-specific static analyzers or AI. Python syntax is parsed with the standard-library AST. Other language parsers are reported unavailable unless an optional tool is explicitly reported as installed but not invoked. Dependency analysis extracts declarations from recognized manifests/lockfiles, with no vulnerability intelligence. Project scanning stays in memory: application code, packages, and scripts are never executed, and archive uploads are not accepted.

Finding workflows use `POST /api/findings/{finding_id}/fix`, `GET /api/fixes/{fix_id}`, `POST /api/fixes/{fix_id}/generate-test`, `POST /api/fixes/{fix_id}/verify`, and `GET /api/verifications/{verification_id}`. Fixes and tests require `LLM_PROVIDER=openai`, `LLM_MODEL`, and `LLM_API_KEY`; the default stub provider returns explicit unavailable/failure results rather than fabricated code. Fixes are proposals only and never overwrite submitted source. Python syntax is checked with AST parsing; unavailable parsers are reported as such. Verification re-runs the corresponding heuristic but remains partial because generated tests and application code are never executed. Test execution reports `EXECUTION_UNAVAILABLE`; no sandbox is configured.

No submitted source code is executed.

## Tests

```powershell
python -m pytest -q
```

## Architecture

- backend/api: FastAPI routes
- backend/agents: specialized review agents
- backend/analyzers: language-aware analyzers
- backend/services: LLM, parser, static analysis, sandbox helpers
- backend/database: SQLite storage layer
- frontend: UI for code review and fix previews
