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

## Local Setup

Use the repository-local virtual environment. Do not install backend
dependencies globally.

```powershell
cd gitvane
.\venv\Scripts\activate
cd backend
python -m pip install -r requirements.txt
```

Copy the example environment file:

```powershell
cd ..
Copy-Item .env.example .env
```

For host-local backend execution while PostgreSQL/Redis run in Docker, set the
database host in `.env` to `localhost`:

```env
DATABASE_URL=postgresql+asyncpg://gitvane:gitvane@localhost:5432/gitvane
SYNC_DATABASE_URL=postgresql+psycopg://gitvane:gitvane@localhost:5432/gitvane
REDIS_URL=redis://localhost:6379/0
GITVANE_WORKSPACE=./workspace/repos
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

Run the frontend in another shell:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend opens at `http://localhost:3000` and talks to the backend through:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Frontend Dashboard

The dashboard is a Next.js app under `frontend/`. It covers repository
registration and indexing, overview metrics, semantic search, impact analysis,
test recommendations, risk ranking, dependency graph exploration, and evaluation
reports.

Use these commands for local frontend work:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Run the browser smoke tests after installing Playwright's Chromium build:

```powershell
npx playwright install chromium
npm run test:e2e
```

## Docker Compose Setup

Run the full local stack:

```powershell
docker compose up --build
```

In another shell, run migrations inside the backend container:

```powershell
docker compose exec backend alembic upgrade head
```

The API is available at `http://localhost:8000`; the frontend is available at
`http://localhost:3000`.

GPU support is optional. By default, Docker Compose runs in CPU-only mode. If you have an NVIDIA GPU and want the container to use it, you can run the stack using the GPU override file:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

_(Note: This requires the NVIDIA Container Toolkit installed on your host machine. If run without the GPU configuration override, the container will automatically and gracefully fall back to CPU-only execution)._

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
