# REST API Documentation

RepoLens exposes a REST API built with FastAPI under the `/api/v1` prefix.

## Endpoints Summary

### Health
- `GET /api/v1/health` - Checks application database and redis connection health.

### Repositories
- `POST /api/v1/repositories` - Registers a git repository (clones if remote, validates if local).
- `GET /api/v1/repositories` - Lists all registered repositories.
- `GET /api/v1/repositories/{id}` - Retrieves repository details.
- `DELETE /api/v1/repositories/{id}` - Deletes repository and local files/index.

### Indexing
- `POST /api/v1/repositories/{id}/index` - Launches background indexing (parsing files, generating chunks/embeddings).
- `GET /api/v1/repositories/{id}/index/status` - Returns the current indexing progress/status.

### Semantic Search
- `POST /api/v1/search/semantic` - Query codebase using natural language.

### Impact Analysis
- `POST /api/v1/impact/analyze` - Predicts changes using Git refs, raw diff, or changed files.
- `GET /api/v1/impact/runs/{id}` - Retrieves predictions of a past run.

### Risk
- `GET /api/v1/risk/repositories/{id}/files` - Retrieves risk metrics (complexity, churn, centrality) for repository files.

### Evaluation
- `POST /api/v1/evaluation/run` - Runs historical evaluation on a repository.
- `GET /api/v1/evaluation/{id}` - Gets status/results.
- `GET /api/v1/evaluation/{id}/report` - Returns evaluation summary report in Markdown.

### Graph
- `GET /api/v1/graph/repositories/{id}/file/{file_id}/neighbors` - Retrieves direct node dependencies.
- `GET /api/v1/graph/repositories/{id}/subgraph` - Retrieves subgraph data for visualization.

---

## Example Usage

### 1. Register a Repository
```bash
curl -X POST "http://localhost:8000/api/v1/repositories" \
     -H "Content-Type: application/json" \
     -d '{"name": "my-project", "clone_url": "https://github.com/example/my-project.git"}'
```

### 2. Index Repository
```bash
curl -X POST "http://localhost:8000/api/v1/repositories/1/index"
```

### 3. Run Impact Analysis
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
