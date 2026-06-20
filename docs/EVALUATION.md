# Historical Commit Evaluation

RepoLens includes a historical evaluation framework to assess prediction accuracy. It simulates predictions on previous repository commits and compares the recommendations against actual historical changes.

## Methodology

1. **Commit Filtering**:
   - Commits with fewer than 2 changed code files are ignored (single-file commits don't show co-changes).
   - Large or automated commits (e.g., lockfiles, refactors > 20 files) are skipped.
2. **Simulation**:
   - For a commit with changed files $\{F_1, F_2, \ldots, F_n\}$, one file $F_i$ is treated as the "known change".
   - The remaining files $\{F_j\}_{j \neq i}$ are treated as ground-truth targets.
3. **Execution**:
   - RepoLens predicts impacted files using $F_i$ as input.
   - Predictions are compared against the ground-truth targets.

## Evaluated Baselines
- **Dependency-only**: Considers only static imports/exports and dependency paths.
- **Semantic-only**: Considers only the semantic cosine similarity of code chunks.
- **Cochange-only**: Considers only historical commit co-occurrences.
- **Hybrid**: Combined weighted prediction model of RepoLens.

## Evaluation Metrics
- **Precision@K**: The percentage of recommended files in top K that were actually modified.
- **Recall@K**: The percentage of actual modified files successfully captured in top K.
- **F1@K**: Harmonic mean of Precision@K and Recall@K.
- **Mean Reciprocal Rank (MRR)**: Evaluates the rank of the first relevant prediction.
- **MAP@K (Mean Average Precision)**: Incorporates the precision at all ranks up to K.
- **NDCG@K (Normalized Discounted Cumulative Gain)**: Measures ranking quality based on relevance position.

## Limitations
- **Current Index Approximation**: Evaluating historical commits against the current state of the dependency graph/index rather than checking out the repository at the historical commit ref. This approximation is documented and can be updated to full ref checkout simulations in future iterations.
