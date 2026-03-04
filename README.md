# Celery Worker

Standalone Celery worker service for Learning Panda.
Handles all heavy ML operations so the FastAPI service stays lightweight and responsive.

## Responsibilities

| Task | Description |
|------|-------------|
| `ingest_pdf_task` | Downloads a PDF from S3, converts it with Docling, embeds chunks with SentenceTransformer, and upserts into Milvus |

## Package layout

```
celery_worker/
├── core/
│   └── config.py        # Minimal settings (REDIS_URL, MILVUS_URI)
├── services/
│   └── milvus.py        # PDF ingestion pipeline (Docling + SentenceTransformer + Milvus)
├── worker/
│   ├── celery_app.py    # Celery app instance
│   └── tasks.py         # Task definitions
└── requirements.txt
```

## Setup

```bash
cd celery_worker

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in env vars
cp .env.example .env
```

## Running the worker

The worker must be started from the `celery_worker/` directory so that the
`worker` and `services` packages resolve correctly.

```bash
cd celery_worker
celery -A worker.celery_app.celery_app worker --loglevel=info
```

### Concurrency

For CPU/memory-heavy ML tasks use a low concurrency (1–2 per machine):

```bash
celery -A worker.celery_app.celery_app worker --loglevel=info --concurrency=2
```

### With Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["celery", "-A", "worker.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
```

## How it connects to the FastAPI service

- Both services share the **same Redis** instance (broker + result backend).
- The FastAPI service dispatches tasks by name (`"ingest_pdf_task"`) via
  `celery_app.send_task(...)` — it does **not** import this package.
- Results are stored in Redis and polled by the `/ingest/pdf/status/{task_id}` endpoint.

## Dependencies vs FastAPI service

| Dependency | FastAPI service | Celery worker |
|------------|:-:|:-:|
| `docling` | ✗ | ✓ |
| `sentence-transformers` | ✓ (RAG queries) | ✓ (ingestion) |
| `pymilvus` | ✓ (RAG queries) | ✓ (ingestion) |
| `celery[redis]` | ✓ (client only) | ✓ (worker) |
| `fastapi` / `uvicorn` | ✓ | ✗ |
| `sqlalchemy` / `asyncpg` | ✓ | ✗ |
# celery-worker
# celery-worker
