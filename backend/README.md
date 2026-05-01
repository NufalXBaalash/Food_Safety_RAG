# Backend — Food Safety RAG API

FastAPI server powering the Food Safety RAG application. See the [project root README](../README.md) for the full API documentation with examples.

## Quick Start

```bash
# From the project root
python run_web_app.py
# or directly:
python -m backend.main
```

Server starts at `http://0.0.0.0:8000`.

## Endpoints

| Method | Path                   | Description                   |
|--------|------------------------|-------------------------------|
| POST   | `/api/ingest`          | Upload & process documents    |
| GET    | `/api/ingest/progress` | Poll ingestion progress       |
| POST   | `/api/chat`            | Ask a food safety question    |
| GET    | `/` (catch-all)        | Serves the static frontend UI |

See the [main README](../README.md) for request/response schemas and curl/Python examples.
