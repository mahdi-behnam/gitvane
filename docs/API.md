# REST API Documentation

GitVane exposes a FastAPI REST API under `/api/v1`.

Interactive documentation is available when the backend is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Authentication

All protected endpoints accept either:
1. **Personal API Key**: Pass `Authorization: Bearer gv_live_...`
2. **JWT Access Token**: Pass `Authorization: Bearer <jwt_token>` (or via `access_token` session cookie)

Personal API keys can be generated in the UI dashboard or via the `POST /api/v1/api-keys` endpoint.

---

## Endpoints

### 1. Health

- `GET /api/v1/health`
  - Returns application status, database connectivity, and Redis connectivity.

---

### 2. Authentication (`/api/v1/auth`)

- `POST /api/v1/auth/signup` — Register a new user account with `email`, `password`, and `full_name`.
- `POST /api/v1/auth/login` — Authenticate with email and password; returns access token and sets refresh cookie.
- `POST /api/v1/auth/refresh` — Issue a new access token using the HTTP-only refresh cookie.
- `POST /api/v1/auth/logout` — Revoke active refresh token and clear auth cookies.
- `GET /api/v1/auth/me` — Retrieve profile information of the authenticated user.
- `PATCH /api/v1/auth/me` — Update user profile details (`full_name`, `email`, `picture`).
- `GET /api/v1/auth/github` & `GET /api/v1/auth/github/callback` — GitHub OAuth2 authentication.
- `GET /api/v1/auth/google` & `GET /api/v1/auth/google/callback` — Google OAuth2 authentication.
- `POST /api/v1/auth/password-reset/request` — Request password reset email.
- `POST /api/v1/auth/password-reset/confirm` — Reset password using verification token.

---

### 3. API Keys (`/api/v1/api-keys`)

- `GET /api/v1/api-keys` — List all personal API keys belonging to the authenticated user.
- `POST /api/v1/api-keys` — Generate and register a new personal API key (`name`, optional `expires_in_days`). Returns the `raw_key` once.
- `DELETE /api/v1/api-keys/{key_id}` — Revoke an API key by its UUID.

---

### 4. Repositories (`/api/v1/repositories`)

- `POST /api/v1/repositories` — Register and clone a Git repository.
  - Body: `name`, `clone_url`, `branch`, optional `index_now` (default `true`), optional `pat` (Personal Access Token).
- `GET /api/v1/repositories` — List user repositories (paginated with `skip` and `limit`).
- `GET /api/v1/repositories/{repository_id}` — Get single repository details and status.
- `DELETE /api/v1/repositories/{repository_id}` — Delete a repository and remove cloned files from disk.
- `POST /api/v1/repositories/remote-branches` — Discover available remote branches for a repository clone URL before registration.
- `GET /api/v1/repositories/{repository_id}/languages` — List distinct indexed programming languages in the repository.
- `GET /api/v1/repositories/{repository_id}/files/search` — Autocomplete search repository files by path prefix and language.
- `GET /api/v1/repositories/{repository_id}/refs` — Autocomplete search Git branches, tags, and commits.
- `POST /api/v1/repositories/{repository_id}/sync` — Pull latest upstream changes from remote and queue re-indexing.

---

### 5. Indexing & SSE Progress Streams

- `POST /api/v1/repositories/{repository_id}/index` — Queue an indexing run for a specific Git ref.
  - Body: optional `ref`, `pipeline_version`, `embedding_backend`, `embedding_model`, `embedding_dimension`.
- `GET /api/v1/repositories/{repository_id}/index/status` — Get high-level counts of indexed files, symbols, chunks, edges, and commits.
- `GET /api/v1/repositories/{repository_id}/index/events` — Server-Sent Events (SSE) stream for repository indexing progress.
- `GET /api/v1/indexing/{generation_id}/stream` — Server-Sent Events (SSE) stream for a specific index generation with Redis Stream resume support.

---

### 6. Semantic Code Search (`/api/v1/search`)

- `POST /api/v1/search/semantic` — Search codebase using natural language queries powered by pgvector embeddings.
  - Body: `repository_id` (UUID), `query` (string), `top_k` (default `10`).

---

### 7. Change Impact Analysis (`/api/v1/impact`)

- `POST /api/v1/impact/analyze` — Predict ripple effect of changes across dependencies, semantic neighbors, co-change history, and risk hot spots.
  - Body: `repository_id` (UUID), optional `base_ref` + `head_ref` or `raw_diff` or `changed_files`, `top_k` (default `20`), `include_explanation` (default `true`), `max_dependency_depth` (default `3`).
- `GET /api/v1/impact/runs/{analysis_run_id}` — Retrieve results for a specific impact analysis run.
- `GET /api/v1/impact/repository/{repository_id}/runs` — List historical impact analysis runs for a repository.

---

### 8. Test Recommendation (`/api/v1/tests`)

- `POST /api/v1/tests/recommend` — Recommend targeted test files for modified or impacted code without executing the test suite.
  - Body: `repository_id` (UUID), `changed_files`, optional `impacted_files`, `top_k` (default `10`).

---

### 9. Architectural Risk Intelligence (`/api/v1/risk`)

- `GET /api/v1/risk/repositories/{repository_id}/files` — Rank repository files by composite risk score (churn, centrality, complexity, size, bugfix frequency).
  - Query parameters: `top_k` (default `20`), `language`, `include_tests` (default `false`), `path_search`.

---

### 10. Historical Evaluation Benchmark (`/api/v1/evaluation`)

- `POST /api/v1/evaluation/run` — Run background benchmark comparing retrieval methods (`dependency_only`, `semantic_only`, `cochange_only`, `hybrid`) against historical Git commits.
  - Body: `repository_id` (UUID), optional `name`, `commit_limit` (default `100`), `methods`, `k_values` (default `[5, 10, 20]`).
- `GET /api/v1/evaluation/{evaluation_run_id}` — Check status and metric summaries (Precision, Recall, MRR, MAP, NDCG).
- `GET /api/v1/evaluation/{evaluation_run_id}/report` — Get structured JSON evaluation report.
- `GET /api/v1/evaluation/{evaluation_run_id}/report.md` — Get formatted Markdown evaluation report.
- `GET /api/v1/evaluation/repository/{repository_id}/runs` — List historical evaluation runs for a repository.

---

### 11. Dependency Graph Visualization (`/api/v1/graph`)

- `GET /api/v1/graph/repositories/{repository_id}/file/{file_id}/neighbors` — Return 1-hop inbound and outbound dependency neighbors for a file node.
- `GET /api/v1/graph/repositories/{repository_id}/subgraph` — Return visualization-ready node and edge graph.
  - Query parameters: `max_nodes` (default `500`), `language`, `include_tests` (default `true`).

---

## Curl Examples

### Register a Repository

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

### Queue Repository Indexing

```bash
curl -X POST "http://localhost:8000/api/v1/repositories/7b886d91-3839-4458-9a3b-2856f616d24f/index" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ref": "main"}'
```

### Run Impact Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/impact/analyze" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "7b886d91-3839-4458-9a3b-2856f616d24f",
    "base_ref": "main",
    "head_ref": "feature-branch",
    "top_k": 20,
    "include_explanation": true
  }'
```

### Run Semantic Search

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

### Recommend Tests

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

### Run Historical Evaluation

```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/run" \
  -H "Authorization: Bearer $GITVANE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "7b886d91-3839-4458-9a3b-2856f616d24f",
    "name": "Historical benchmark",
    "commit_limit": 100,
    "methods": ["dependency_only", "semantic_only", "cochange_only", "hybrid"],
    "k_values": [5, 10, 20]
  }'
```
