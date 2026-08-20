# Historical Evaluation

GitVane includes an evaluation harness to measure whether its prediction
methods can recover files that actually changed together in historical commits.

The goal is not to manufacture high scores. Low scores are useful because they
show where the current signals are weak.

## Scenario Construction

For each indexed historical commit:

1. Collect changed files from stored commit metadata.
2. Keep only files that are present in the current index.
3. Skip commits with fewer than two indexed code files.
4. Skip broad commits with more than 20 indexed code files.
5. Pick one changed file as the known input.
6. Treat the remaining changed files as ground truth impacted files.

This simulates a developer saying, "I know this file changed; what else is
likely affected?"

## Compared Methods

GitVane compares four methods:

- `dependency_only`: reverse dependency relationships from indexed imports.
- `semantic_only`: vector search over indexed chunks.
- `cochange_only`: normalized historical co-change scores.
- `hybrid`: reciprocal-rank style blend of dependency, semantic, and co-change
  prediction lists.

The full impact API uses more signals than these baselines, including risk and
test scores. The evaluation harness isolates core retrieval methods for clearer
comparison.

## Metrics

GitVane computes:

- `precision_at_k`
- `recall_at_k`
- `f1_at_k`
- `mrr`
- `map_at_k`
- `ndcg_at_k`

Default K values are `5`, `10`, and `20`.

## API

Start an evaluation run (runs asynchronously in the background):

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

Fetch evaluation status & summary:

```bash
curl -H "Authorization: Bearer $GITVANE_API_KEY" \
  "http://localhost:8000/api/v1/evaluation/1"
```

Fetch Markdown report:

```bash
curl -H "Authorization: Bearer $GITVANE_API_KEY" \
  "http://localhost:8000/api/v1/evaluation/1/report.md"
```

## Interpreting Results

- High recall means relevant historical co-change files were found.
- High precision means fewer unrelated files were recommended.
- MRR rewards putting the first relevant file near the top.
- MAP@K rewards multiple relevant hits at strong ranks.
- NDCG@K rewards ranking quality with position discounting.

The best method may vary by repository. A small library with clean imports may
favor dependency-only predictions; a product codebase with repeated coordinated
changes may favor co-change.

## Limitations

The current MVP uses the current indexed graph as an approximation instead of
checking out and re-indexing each historical commit. This is faster and keeps the
service simple, but it can overstate or understate historical relationships when
files moved, imports changed, or symbols were renamed after the evaluated commit.

The service stores this limitation in run configuration and includes it in the
generated report.

Future work can add checkout-per-commit evaluation for stronger historical
fidelity.
