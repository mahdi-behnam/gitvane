import math


class EvaluationMetrics:
    """Compute ranking metrics for historical impact evaluation."""

    def precision_at_k(
        self, predictions: list[str], ground_truth: set[str], k: int
    ) -> float:
        if k <= 0:
            return 0.0
        predicted = predictions[:k]
        if not predicted:
            return 0.0
        hits = sum(1 for path in predicted if path in ground_truth)
        return round(hits / len(predicted), 4)

    def recall_at_k(
        self, predictions: list[str], ground_truth: set[str], k: int
    ) -> float:
        if not ground_truth or k <= 0:
            return 0.0
        hits = sum(1 for path in predictions[:k] if path in ground_truth)
        return round(hits / len(ground_truth), 4)

    def f1_at_k(self, predictions: list[str], ground_truth: set[str], k: int) -> float:
        precision = self.precision_at_k(predictions, ground_truth, k)
        recall = self.recall_at_k(predictions, ground_truth, k)
        if precision + recall == 0:
            return 0.0
        return round(2 * precision * recall / (precision + recall), 4)

    def mrr(self, predictions: list[str], ground_truth: set[str]) -> float:
        for index, path in enumerate(predictions, start=1):
            if path in ground_truth:
                return round(1 / index, 4)
        return 0.0

    def average_precision_at_k(
        self, predictions: list[str], ground_truth: set[str], k: int
    ) -> float:
        if not ground_truth or k <= 0:
            return 0.0
        hits = 0
        precision_sum = 0.0
        for index, path in enumerate(predictions[:k], start=1):
            if path in ground_truth:
                hits += 1
                precision_sum += hits / index
        denominator = min(len(ground_truth), k)
        return round(precision_sum / denominator, 4) if denominator else 0.0

    def ndcg_at_k(self, predictions: list[str], ground_truth: set[str], k: int) -> float:
        if not ground_truth or k <= 0:
            return 0.0
        dcg = 0.0
        for index, path in enumerate(predictions[:k], start=1):
            if path in ground_truth:
                dcg += 1 / math.log2(index + 1)
        ideal_hits = min(len(ground_truth), k)
        ideal = sum(1 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
        return round(dcg / ideal, 4) if ideal else 0.0

    def all_at_k(
        self,
        predictions: list[str],
        ground_truth: set[str],
        k_values: list[int],
    ) -> dict[str, float]:
        metrics = {
            "mrr": self.mrr(predictions, ground_truth),
        }
        for k in k_values:
            metrics[f"precision_at_{k}"] = self.precision_at_k(
                predictions, ground_truth, k
            )
            metrics[f"recall_at_{k}"] = self.recall_at_k(predictions, ground_truth, k)
            metrics[f"f1_at_{k}"] = self.f1_at_k(predictions, ground_truth, k)
            metrics[f"map_at_{k}"] = self.average_precision_at_k(
                predictions, ground_truth, k
            )
            metrics[f"ndcg_at_{k}"] = self.ndcg_at_k(predictions, ground_truth, k)
        return metrics
