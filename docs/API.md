# REST API Documentation

GitVane exposes a FastAPI REST API under `/api/v1`.

Interactive documentation is available when the backend is running:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Endpoints

### Health

- `GET /api/v1/health`

Returns application and database health.

### Repositories

- `POST /api/v1/repositories`
- `GET /api/v1/repositories`
- `GET /api/v1/repositories/{repository_id}`
- `DELETE /api/v1/repositories/{repository_id}`

`POST /repositories` accepts `name`, `clone_url` or `local_path`, optional
`branch`, and `index_now`.

### Indexing

- `POST /api/v1/repositories/{repository_id}/index`
- `GET /api/v1/repositories/{repository_id}/index/status`

Indexing discovers tracked files, filters unsupported/generated/binary files,
parses supported source, saves symbols/chunks/dependencies, generates embeddings,
and stores recent commit metadata.

### Semantic Search

- `POST /api/v1/search/semantic`

```json
{
  "repository_id": 1,
  "query": "Where is JWT expiration validated?",
  "top_k": 10
}
```

### Impact

- `POST /api/v1/impact/analyze`
- `GET /api/v1/impact/runs/{analysis_run_id}`

Impact analysis supports Git refs, raw diffs, or explicit changed files.
Predictions include component scores and evidence-backed reasons.

### Test Recommendation

- `POST /api/v1/tests/recommend`

```json
{
  "repository_id": 1,
  "changed_files": [
    {"path": "src/auth/token.py", "change_type": "modified"}
  ],
  "impacted_files": ["src/api/routes.py"],
  "top_k": 10
}
```

GitVane recommends tests but does not execute them.

### Risk

- `GET /api/v1/risk/repositories/{repository_id}/files`

Query parameters:

- `top_k`
- `language`
- `include_tests`

### Evaluation

- `POST /api/v1/evaluation/run`
- `GET /api/v1/evaluation/{evaluation_run_id}`
- `GET /api/v1/evaluation/{evaluation_run_id}/report`
- `GET /api/v1/evaluation/{evaluation_run_id}/report.md`

Evaluation compares dependency-only, semantic-only, co-change-only, and hybrid
methods against historical commits.

### Graph

- `GET /api/v1/graph/repositories/{repository_id}/file/{file_id}/neighbors`
- `GET /api/v1/graph/repositories/{repository_id}/subgraph`

Graph responses return visualization-ready `nodes` and `edges`.

## Curl Examples

### Register a Repository

```bash
curl -X POST "http://localhost:8000/api/v1/repositories" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "clone_url": "https://github.com/example/my-project.git"
  }'
```

### Index a Repository

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
    "base_ref": "main",
    "head_ref": "feature-branch",
    "top_k": 10,
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
    "impacted_files": ["src/api/routes.py"]
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
