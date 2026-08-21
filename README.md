<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/gitvane-dark-readme-header.jpg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/gitvane-light-readme-header.jpg">
    <img alt="GitVane" src="docs/assets/brand/gitvane-light-readme-header.jpg" width="100%">
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

- Register remote Git repositories with automatic clone, branch discovery, and optional PAT authentication.
- Index Python, JavaScript, and TypeScript files with AST and tree-sitter parsers.
- Extract imports, classes, functions, methods, calls, exports, and test blocks.
- Build file-level dependency edges and call graphs.
- Generate and store code chunk embeddings with pgvector (local models or NVIDIA NIM).
- Run semantic natural language code search across indexed codebases.
- Analyze change impact from Git refs, raw unified diffs, or explicit changed files.
- Recommend targeted test files without executing the test suite.
- Rank architectural risk hot spots using churn, dependency centrality, complexity, and size.
- Explain predictions through NVIDIA NIM LLM reasoning or deterministic fallback text.
- Evaluate prediction quality against historical Git commits using standard IR metrics (Precision, Recall, MRR, MAP, NDCG).
- Return interactive graph data for frontend dependency visualization.
- Provide a modern Next.js dashboard for repository management, real-time SSE indexing progress, semantic search, change impact, test recommendations, risk ranking, interactive dependency graphs, and evaluation reports.
- Provide a Model Context Protocol (MCP) server (`gitvane-mcp`) integrating directly with AI coding assistants (Claude Desktop, Cursor, Claude Code, Windsurf, OpenAI Codex, Antigravity).

## Dashboard Preview

Here is an architectural walkthrough of the GitVane Next.js dashboard in action:

### 1. Repository Inventory & Real-Time Indexing Pipeline

Register codebases, manage multi-branch tracking, and observe live Server-Sent Events (SSE) progress as AST parsing, symbol extraction, dependency graph generation, and vector embeddings are computed asynchronously.

![Repository Inventory & Multi-Branch Management](docs/assets/screenshots/repositories-page.png)
![Repository Details & Real-Time SSE Indexing Progress](docs/assets/screenshots/repository-details-page.png)

### 2. Semantic Code Search

Query codebases using natural language intent (e.g., _"How is the authentication handled?"_). Vector embeddings retrieve scored, syntax-highlighted code chunks with direct action links into impact analysis, risk assessment, and dependency graph views.

![Semantic Code Search](docs/assets/screenshots/semantic-search-page.png)

### 3. Change Impact Analysis (Blast Radius Prediction)

Predict downstream blast radius for candidate code modifications from changed file paths, raw Git diffs, or branch refs. GitVane computes explainable prediction scores combining deterministic AST dependencies, semantic similarity, historical commit co-change frequencies, and test naming heuristics alongside LLM reasoning summaries.

![Change Impact Analysis - Input Configuration & Analysis Lookup](docs/assets/screenshots/impact-analysis-page-1.png)
![Change Impact Analysis - Multi-Signal Impact Scores & Test Mapping](docs/assets/screenshots/impact-analysis-page-2.png)
![Change Impact Analysis - Risk Summary & LLM Evidence Explanation](docs/assets/screenshots/impact-analysis-page-3.png)

### 4. Targeted Test Recommendations

Identify and prioritize the exact test candidates impacted by proposed changes without executing untrusted test suites, providing instant feedback for pull request reviews and local pre-commit validation.

![Targeted Test Recommendations](docs/assets/screenshots/test-recommendations-page.png)

### 5. Interactive Dependency Graph & Risk-Impact Matrix

Explore architectural structure and module coupling across multiple visual perspectives—from layered interactive node topologies with real-time traversal depth controls to a 2D Risk vs. Coupling quadrant matrix highlighting critical architectural hubs.

![Interactive Dependency Topology Explorer](docs/assets/screenshots/dependency-graph-page-interactive-topology.png)
![2D Risk vs. Module Coupling Quadrant Matrix](docs/assets/screenshots/dependency-graph-page-risk-impact-matrix-view.png)

### 6. Architectural Risk Ranking & Hotspots

Pinpoint high-risk modules and maintenance bottlenecks across the repository using weighted heuristic signals: cyclomatic complexity, churn rate, test coverage proxy, and structural graph centrality (fan-in/fan-out).

![Architectural Risk Ranking - Summary Metrics & Risk Distribution](docs/assets/screenshots/risk-ranking-page-1.png)
![Architectural Risk Ranking - Granular Module Breakdown](docs/assets/screenshots/risk-ranking-page-2.png)

### 7. Model Context Protocol (MCP) & AI Agent Integration

Connect autonomous AI agents and IDE assistants (Claude Desktop, Cursor, Claude Code, Windsurf, Antigravity) directly to GitVane intelligence endpoints with personal API key provisioning, one-click client configuration templates, and exposed tool definitions.

![MCP & AI Agent Integration - Personal API Keys & Client Setup](docs/assets/screenshots/mcp-page-1.png)
![MCP & AI Agent Integration - Exposed Tools & Agent Intelligence](docs/assets/screenshots/mcp-page-2.png)

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

> [!NOTE]
> All API requests require authentication. Pass your personal API key (`gv_live_...`) or JWT access token in the `Authorization: Bearer <token>` header.

### 1. Register a Repository

```bash
curl -X POST "http://localhost:8000/api/v1/repositories" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "example-repo",
    "clone_url": "https://github.com/example/example-repo.git",
    "branch": "main",
    "index_now": true
  }'
```

### 2. Index a Repository

```bash
curl -X POST "http://localhost:8000/api/v1/repositories/7b886d91-3839-4458-9a3b-2856f616d24f/index" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ref": "main"}'
```

### 3. Run Change Impact Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/impact/analyze" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "7b886d91-3839-4458-9a3b-2856f616d24f",
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

### 4. Run Semantic Code Search

```bash
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "7b886d91-3839-4458-9a3b-2856f616d24f",
    "query": "Where is JWT expiration validated?",
    "top_k": 10
  }'
```

### 5. Recommend Targeted Tests

```bash
curl -X POST "http://localhost:8000/api/v1/tests/recommend" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "7b886d91-3839-4458-9a3b-2856f616d24f",
    "changed_files": [{"path": "src/auth/token.py"}],
    "impacted_files": ["src/api/routes.py"],
    "top_k": 10
  }'
```

### 6. Run Historical Impact Evaluation

```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/run" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "7b886d91-3839-4458-9a3b-2856f616d24f",
    "name": "Initial benchmark",
    "commit_limit": 100,
    "methods": ["dependency_only", "semantic_only", "cochange_only", "hybrid"],
    "k_values": [5, 10, 20]
  }'
```

## Current Limitations

- JavaScript/TypeScript symbol resolution is best-effort.
- TypeScript path aliases are only partially supported.
- Historical evaluation currently uses the current index as an approximation instead of checking out every historical commit.
- Test execution is intentionally out of scope (GitVane provides test recommendations based on deterministic and semantic mapping, without executing untrusted test code).

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design, outbox pattern, and data flow
- [docs/API.md](docs/API.md) — Complete REST API reference and schemas
- [docs/EVALUATION.md](docs/EVALUATION.md) — Historical evaluation harness and metrics
- [mcp/README.md](mcp/README.md) — Model Context Protocol (MCP) server documentation

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE) — free for personal, educational, research, and non-commercial evaluation. Commercial use is prohibited without prior authorization.
