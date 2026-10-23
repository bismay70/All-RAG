# RAGLab AI

RAGLab AI is a local-first Retrieval-Augmented Generation research workbench. It lets you upload documents, index them, ask grounded questions, inspect citations and traces, and compare RAG strategies without requiring a paid hosted vector database.

## What Is Implemented

- FastAPI backend skeleton with versioned routes and OpenAPI docs.
- Safe root `.env` loading with secret values kept server-side.
- Local SQLite persistence for documents, chunks, runs, datasets, and experiments.
- Upload and parsing for TXT, Markdown, PDF, HTML, DOCX, and CSV.
- Configurable chunking, duplicate detection by content hash, local deterministic embeddings, and hybrid dense plus lexical retrieval.
- xAI/Grok chat-completions adapter with bounded timeout/retry and local extractive fallback.
- Strategy catalogue with honest `implemented`, `experimental`, and `planned` labels.
- Simple, two-step, hybrid, reranked, adaptive, multi-query-style, and Corrective RAG-inspired paths.
- Citation objects, local trace events, retrieval metrics, abstention, and provider health status.
- React + TypeScript workbench styled from `image.png`, with real API calls for health, providers, uploads, deletion, chat, citations, traces, and pipeline status.

## Folder Structure

```text
backend/
  app/
    api/routes/
    core/
    db/
    ingestion/
    retrieval/
    generation/
    strategies/
    evaluation/
    observability/
    schemas/
  tests/
  requirements.txt
frontend/
  src/
    lib/
    types/
    App.tsx
RAGLab_AI_Master_Architecture_and_Agent_Build_Spec.md
prompt.md
image.png
```

## Prerequisites

- Python 3.12+
- Node.js 22+
- npm 10+
- Optional: Docker for future Qdrant/PostgreSQL services

## Backend Setup

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`. You can also set `VITE_API_BASE_URL=http://localhost:8000/api/v1` in `frontend/.env`.

## Environment

The backend reads the root `.env` explicitly. Do not put real secrets in frontend variables.

Supported variables include:

- `GROK_API_KEY` or `XAI_API_KEY`
- `GROK_MODEL`
- `XAI_BASE_URL`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `LANGSMITH_TRACING`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- `X_BEARER_TOKEN`

Only variable names are surfaced in health responses, never values.

## Providers And Storage

The current local vector-store adapter stores vectors in SQLite as JSON and uses deterministic hashing embeddings. This is intended for local development and tests. Qdrant, PostgreSQL plus pgvector, OCR, GraphRAG storage, and multimodal embeddings are documented as future adapters unless implemented and tested.

xAI/Grok is used through the backend provider adapter when configured. If the key, model, quota, or network access fails, the app returns a warning and uses local extractive synthesis instead of faking a hosted response.

X API retrieval is optional. The provider status endpoint reports whether credentials are present, but the app does not simulate successful X search without verified access.

## Testing

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm run build
```

## Troubleshooting

- CORS: keep `CORS_ORIGINS` aligned with the Vite URL, usually `http://localhost:5173`.
- Backend import errors: reinstall dependencies inside `backend/.venv`; do not use global Python packages.
- Grok errors: verify `GROK_API_KEY`, `GROK_MODEL`, quota, and API access. The local fallback should keep the app operational.
- Empty answers: upload at least one readable document and confirm it reaches `indexed` status.
- Docker warning: Docker is not required for the current SQLite adapter.

## Known Limits

This is a working vertical slice, not the full research catalogue. Advanced methods such as faithful Self-RAG, GraphRAG, RAPTOR, multimodal RAG, FLARE, REPLUG, durable background workers, and pgvector/Qdrant production indexing are labelled planned or experimental until their dependencies, tests, and UI flows are complete.

