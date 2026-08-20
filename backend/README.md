# GitVane Backend

FastAPI backend for repository indexing, semantic search, change impact prediction,
test recommendation, architectural risk scoring, LLM explanations, and historical evaluation.

## Installation & Setup

Install dependencies using `uv`:

```powershell
cd backend
uv sync --all-extras
```

## Running Backend Services

During development, start the required background services in dedicated terminals:

### 1. Database Migrations

```powershell
cd backend
uv run alembic upgrade head
```

### 2. FastAPI Web Server

```powershell
cd backend
uv run uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

### 3. Celery Task Worker

- **CPU Worker:**
  ```powershell
  cd backend
  uv run celery -A app.core.celery_app worker -Q indexing_cpu,workflow_control,evaluation_cpu --loglevel=info -P solo --without-mingle --without-gossip --without-heartbeat
  ```
- **With GPU Acceleration:**
  ```powershell
  cd backend
  uv run celery -A app.core.celery_app worker -Q indexing_cpu,embeddings_gpu,workflow_control,evaluation_cpu --loglevel=info -P solo --without-mingle --without-gossip --without-heartbeat
  ```

### 4. Outbox Dispatcher

```powershell
cd backend
uv run python -m app.cli.dispatcher
```

### 5. Outbox Reconciler

```powershell
cd backend
uv run python -m app.cli.reconciler
```

## Testing & Quality Checks

Run unit and integration tests:

```powershell
cd backend
$env:DEBUG='true'
uv run pytest -q -p no:cacheprovider --basetemp .test-tmp
uv run ruff check app tests
```

## API Documentation

With the backend running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
