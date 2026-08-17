<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/gitvane-dark-readme-header.jpg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/gitvane-light-readme-header.jpg">
    <img alt="GitVane" src="docs/assets/gitvane-light-readme-header.jpg" width="100%">
  </picture>
</p>

# GitVane

> _Just as a weather vane shows which way the wind blows, **GitVane** shows developers which way their Git changes and dependency impacts propagate._

GitVane is an AI-assisted software engineering backend that analyzes Git
repositories and predicts which files, tests, and risky modules are likely to
matter for a proposed change.

It is intentionally not a black-box LLM wrapper. The prediction scores come from
deterministic software engineering evidence: language-aware parsing, dependency
graphs, semantic code embeddings, historical co-change mining, test mappings,
and risk heuristics. The LLM layer only summarizes already-computed evidence.

## What GitVane Solves

When a change touches one file, related work often hides elsewhere: importers,
nearby tests, files that historically changed together, semantically similar
code, or high-risk modules with heavy fan-in. GitVane indexes a repository and
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
- Return graph data for frontend visualization.
- Provide a Next.js dashboard for repository management, search, impact
  analysis, test recommendations, risk ranking, graph exploration, and
  evaluation reports.

## Dashboard Preview

Here is a look at the GitVane Next.js dashboard in action, showcasing its core capabilities:

### 1. Repository Management & Indexing

Manage your repositories, track indexing status, and see high-level metadata (branches, latest commits, files).

<!-- The repository management dashboard screenshot will be put here -->
<!-- ![Repository Management Dashboard](docs/assets/repo_dashboard.png) -->

### 2. Semantic Code Search

Search your codebase using natural language queries (e.g., _"Where are API keys loaded?"_) powered by vector embeddings.

<!-- The semantic search UI screenshot will be put here -->
<!-- ![Semantic Search UI](docs/assets/semantic_search.png) -->

### 3. Change Impact & Test Recommendation

Analyze the potential impact of proposed file edits, find dependency-linked risk areas, and get specific recommendations on which tests to run.

<!-- The change impact analysis screenshot will be put here -->
<!-- ![Change Impact Analysis](docs/assets/impact_analysis.png) -->

### 4. Interactive Graph Explorer

Visualize your code structure, import maps, and dependencies as an interactive file-level node graph.

<!-- The interactive dependency graph explorer screenshot will be put here -->
<!-- ![Dependency Graph Explorer](docs/assets/graph_explorer.png) -->

### 5. Historical Evaluation Reports

Run and compare prediction performance benchmarks (Precision, Recall, MRR, NDCG) against actual historical Git commits.

<!-- The historical evaluation report screenshot will be put here -->
<!-- ![Historical Evaluation Report](docs/assets/evaluation_report.png) -->

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

## Development Setup (Fast Iteration & Hot Reloading)

When developing and frequently modifying frontend and backend files, the recommended workflow is to run the pure infrastructure services (**PostgreSQL**, **Redis**, **PgBouncer**, **RabbitMQ**) inside Docker containers, and run the Python backend services and Next.js frontend directly in dedicated terminals on your host machine using `uv` and `npm`. This provides instant code hot-reloading without container rebuild overhead.

### 1. Configure Environment Variables

Create your local `.env` configuration from the template:

```powershell
Copy-Item .env.example .env
```

Ensure required infrastructure credentials and keys are set in `.env` (such as `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `JWT_SECRET_KEY`, and `ENCRYPTION_KEY`).

For host-local execution, point database and broker connections to `localhost` with the exposed port mapping:
```env
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:6432/${POSTGRES_DB}
SYNC_DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:6432/${POSTGRES_DB}
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```
*(Note: Port `6432` routes through PgBouncer with connection pooling. If you need direct PostgreSQL access for administrative tools or direct DDL migrations, use port `5433`).*

### 2. Start Docker Infrastructure

Spin up only the database, cache, connection pooler, and message broker containers:

```powershell
docker compose up -d postgres redis pgbouncer rabbitmq
```

### 3. Run Database Migrations

Apply the latest database migrations from the `backend/` directory:

```powershell
cd backend
uv run alembic upgrade head
```

### 4. Run Application Services in 5 Separate Terminals

Execute each of the following commands in its own dedicated terminal:

#### Terminal 1: FastAPI Backend
```powershell
cd backend
uv run uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```
* **API Documentation**: Available at `http://localhost:8000/docs`

#### Terminal 2: Celery Worker
- **For CPU-Only:**
  ```powershell
  cd backend
  uv run celery -A app.core.celery_app worker -Q indexing_cpu,workflow_control,evaluation_cpu --loglevel=info -P solo --without-mingle --without-gossip --without-heartbeat
  ```
- **With NVIDIA GPU (Local Embeddings Acceleration):**
  If you have an NVIDIA GPU and PyTorch with CUDA installed, include the `embeddings_gpu` queue (and ensure `USE_CUDA_IF_AVAILABLE=true` in `.env`):
  ```powershell
  cd backend
  uv run celery -A app.core.celery_app worker -Q indexing_cpu,embeddings_gpu,workflow_control,evaluation_cpu --loglevel=info -P solo --without-mingle --without-gossip --without-heartbeat
  ```

#### Terminal 3: Outbox Dispatcher
```powershell
cd backend
uv run python -m app.cli.dispatcher
```

#### Terminal 4: Outbox Reconciler
```powershell
cd backend
uv run python -m app.cli.reconciler
```

#### Terminal 5: Next.js Frontend
```powershell
cd frontend
npm install
npm run dev
```
* **Web UI Dashboard**: Accessible at `http://localhost:3000`

---

## Production Deployment (Full Docker Compose Stack)

For production deployments, staging environments, or testing the fully containerized system with the Nginx edge proxy, reverse proxying, rate limiting, and network isolation, run the complete Docker Compose stack:

```powershell
docker compose up --build -d
```

- **Unified Application Gateway (Nginx)**: `http://localhost` (proxies `/` to the Next.js frontend container and `/api/` / `/docs` to the FastAPI backend container)
- **Run Migrations inside container**:
  ```powershell
  docker compose exec backend alembic upgrade head
  ```
- **Scale Backend API Workers (Optional)**:
  ```powershell
  docker compose up --scale backend=2 -d
  ```

### GPU Support (Optional)

By default, Docker Compose runs in CPU-only mode. If you have an NVIDIA GPU and the NVIDIA Container Toolkit installed on your host:

- **Local development with GPU:**
  ```powershell
  docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.gpu.yml up --build -d
  ```
- **Production deployment with GPU:**
  ```powershell
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
  ```

*(Note: This requires the NVIDIA Container Toolkit installed on your host machine. If run without the GPU configuration override, the containers automatically and gracefully fall back to CPU-only execution).*

## Tests And Checks

```powershell
cd backend
$env:DEBUG='true'
python -m pytest -q
python -m ruff check app tests
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
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

For a local repository, place it inside `GITVANE_WORKSPACE` and pass
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
- The frontend does not implement authentication or execute repository tests.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API.md](docs/API.md)
- [docs/EVALUATION.md](docs/EVALUATION.md)
