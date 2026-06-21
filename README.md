# RepoLens

RepoLens is an AI-assisted software engineering backend that analyzes Git
repositories and predicts which files, tests, and risky modules are likely to
matter for a proposed change.

It is intentionally not a black-box LLM wrapper. The prediction scores come from
deterministic software engineering evidence: language-aware parsing, dependency
graphs, semantic code embeddings, historical co-change mining, test mappings,
and risk heuristics. The LLM layer only summarizes already-computed evidence.

## What RepoLens Solves

When a change touches one file, related work often hides elsewhere: importers,
nearby tests, files that historically changed together, semantically similar
code, or high-risk modules with heavy fan-in. RepoLens indexes a repository and
turns those signals into explainable impact predictions.

Current backend capabilities:

- Register local or remote Git repositories.
- Index Python, JavaScript, and TypeScript files.
- Extract imports, classes, functions, methods, calls, exports, and test blocks.
- Build file-level dependency edges.
- Generate and store code chunk embeddings with pgvector.
- Run semantic code search.
- Analyze change impact from Git refs, raw diffs, or explicit changed files.
- Recommend tests without executing them.
- Rank risky files using churn, dependency centrality, complexity, and size.
- Explain predictions through NVIDIA NIM or deterministic fallback text.
- Evaluate prediction quality against historical commits.
- Return graph data for future visualization.

The frontend is intentionally deferred. `frontend/README.md` is a placeholder.

## Architecture

```mermaid
flowchart LR
    Repo[Git repository] --> Git[GitService]
    Git --> Index[Indexing service]
    Index --> Parsers[Python AST / tree-sitter parsers]
    Parsers --> DB[(PostgreSQL + pgvector)]
    Parsers --> Graph[Dependency graph]
    Index --> Embeddings[Local or NIM embeddings]
    Git --> History[Commit history mining]
    DB --> Impact[Impact prediction]
    Graph --> Impact
    Embeddings --> Search[Semantic search]
    Search --> Impact
    History --> Impact
    Impact --> Tests[Test recommendation]
    Impact --> Risk[Risk scoring]
    Impact --> Explain[LLM explanation layer]
    Impact --> Eval[Historical evaluation]
    Explain --> API[FastAPI REST API]
    Eval --> API
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Local Setup

Use the repository-local virtual environment. Do not install backend
dependencies globally.

```powershell
cd repolens
.\venv\Scripts\activate
cd backend
python -m pip install -e ".[dev]"
```

Copy the example environment file:

```powershell
cd ..
Copy-Item .env.example .env
```

For host-local backend execution while PostgreSQL/Redis run in Docker, set the
database host in `.env` to `localhost`:

```env
DATABASE_URL=postgresql+asyncpg://repolens:repolens@localhost:5432/repolens
SYNC_DATABASE_URL=postgresql+psycopg://repolens:repolens@localhost:5432/repolens
REDIS_URL=redis://localhost:6379/0
REPOLENS_WORKSPACE=./workspace/repos
```

Start PostgreSQL and Redis:

```powershell
docker compose up -d postgres redis
```

Run migrations:

```powershell
cd backend
alembic upgrade head
```

Run the backend:

```powershell
uvicorn app.main:app --reload
```

OpenAPI docs are available at `http://localhost:8000/docs`.

## Docker Compose Setup

Run the full backend stack:

```powershell
docker compose up --build
```

In another shell, run migrations inside the backend container:

```powershell
docker compose exec backend alembic upgrade head
```

GPU support is optional. Docker Compose is configured for CPU-compatible local
development. Host execution can use CUDA automatically when PyTorch and the
local GPU setup are available and `USE_CUDA_IF_AVAILABLE=true`.

## Tests And Checks

```powershell
cd backend
$env:DEBUG='true'
python -m pytest -q
python -m ruff check app tests
```

If the Windows temp directory is locked down, use a repo-local pytest temp dir:

```powershell
python -m pytest -q -p no:cacheprovider --basetemp .test-tmp
```

## Example API Calls

### Create Repository

```bash
curl -X POST "http://localhost:8000/api/v1/repositories" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "example",
    "clone_url": "https://github.com/example/example.git"
  }'
```

For a local repository, place it inside `REPOLENS_WORKSPACE` and pass
`local_path`.

### Index Repository

```bash
curl -X POST "http://localhost:8000/api/v1/repositories/1/index" \
  -H "Content-Type: application/json" \
  -d '{"max_commits": 100}'
```

### Run Impact Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/impact/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "changed_files": [
      {
        "path": "src/auth/token.py",
        "change_type": "modified",
        "changed_lines": [[10, 25]]
      }
    ],
    "top_k": 20,
    "include_explanation": true
  }'
```

### Run Semantic Search

```bash
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "query": "Where is JWT expiration validated?",
    "top_k": 10
  }'
```

### Recommend Tests

```bash
curl -X POST "http://localhost:8000/api/v1/tests/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "changed_files": [{"path": "src/auth/token.py"}],
    "impacted_files": ["src/api/routes.py"],
    "top_k": 10
  }'
```

### Run Evaluation

```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/run" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "name": "Initial evaluation",
    "commit_limit": 100,
    "methods": ["dependency_only", "semantic_only", "cochange_only", "hybrid"],
    "k_values": [5, 10, 20]
  }'
```

## Current Limitations

- JavaScript/TypeScript symbol resolution is best-effort.
- TypeScript path aliases are only partially supported.
- Historical evaluation currently uses the current index as an approximation
  instead of checking out every historical commit.
- Test execution is intentionally out of scope.
- The frontend dashboard is intentionally deferred.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API.md](docs/API.md)
- [docs/EVALUATION.md](docs/EVALUATION.md)
- [docs/RESUME_BULLETS.md](docs/RESUME_BULLETS.md)
