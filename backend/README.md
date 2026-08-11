# GitVane Backend

FastAPI backend for repository indexing, semantic search, impact prediction,
test recommendation, risk scoring, LLM explanations, and historical evaluation.

## Install

Use the repo-local virtual environment from the repository root:

```powershell
.\venv\Scripts\activate
cd backend
python -m pip install -e ".[dev]"
```

## Run

```powershell
uvicorn app.main:app --reload
```

## Migrations

```powershell
alembic upgrade head
```

## Tests

```powershell
$env:DEBUG='true'
python -m pytest -q -p no:cacheprovider --basetemp .test-tmp
python -m ruff check app tests
```

## API Docs

With the backend running:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
