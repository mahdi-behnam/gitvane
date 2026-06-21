from collections import Counter
from math import sqrt
from typing import Any, Iterable


class CochangeMiner:
    """Compute normalized file co-change scores from commit metadata."""

    def score_candidates(
        self,
        changed_paths: set[str],
        commits: Iterable[Any],
    ) -> dict[str, float]:
        changes: Counter[str] = Counter()
        joint: Counter[tuple[str, str]] = Counter()

        for commit in commits:
            files = self._changed_paths(commit)
            for path in files:
                changes[path] += 1
            for changed_path in changed_paths & files:
                for candidate in files - {changed_path}:
                    joint[(changed_path, candidate)] += 1

        scores: dict[str, float] = {}
        for (changed_path, candidate), count in joint.items():
            denominator = sqrt(changes[changed_path] * changes[candidate])
            score = count / denominator if denominator else 0.0
            scores[candidate] = max(scores.get(candidate, 0.0), min(score, 1.0))
        return scores

    def jaccard_scores(
        self,
        changed_paths: set[str],
        commits: Iterable[Any],
    ) -> dict[str, float]:
        touched_by_file: dict[str, set[str]] = {}
        for index, commit in enumerate(commits):
            commit_key = self._commit_key(commit, index)
            for path in self._changed_paths(commit):
                touched_by_file.setdefault(path, set()).add(commit_key)

        scores: dict[str, float] = {}
        for changed_path in changed_paths:
            changed_commits = touched_by_file.get(changed_path, set())
            for candidate, candidate_commits in touched_by_file.items():
                if candidate == changed_path:
                    continue
                union = changed_commits | candidate_commits
                if not union:
                    continue
                score = len(changed_commits & candidate_commits) / len(union)
                scores[candidate] = max(scores.get(candidate, 0.0), score)
        return scores

    def _changed_paths(self, commit: Any) -> set[str]:
        changed_files = getattr(commit, "changed_files", None)
        if changed_files is None and isinstance(commit, dict):
            changed_files = commit.get("changed_files")
        if not changed_files:
            return set()

        paths: set[str] = set()
        for item in changed_files:
            if isinstance(item, str):
                paths.add(item)
            elif isinstance(item, dict):
                path = item.get("path") or item.get("new_path") or item.get("old_path")
                if path:
                    paths.add(str(path))
        return paths

    def _commit_key(self, commit: Any, index: int) -> str:
        return str(getattr(commit, "sha", None) or commit.get("sha", index))
