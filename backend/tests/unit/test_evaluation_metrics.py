from app.analysis.evaluation_metrics import EvaluationMetrics


def test_precision_recall_and_f1_at_k() -> None:
    metrics = EvaluationMetrics()
    predictions = ["a.py", "b.py", "c.py"]
    ground_truth = {"b.py", "c.py", "d.py"}

    assert metrics.precision_at_k(predictions, ground_truth, 2) == 0.5
    assert metrics.recall_at_k(predictions, ground_truth, 2) == 0.3333
    assert metrics.f1_at_k(predictions, ground_truth, 2) == 0.4


def test_mrr_map_and_ndcg_at_k() -> None:
    metrics = EvaluationMetrics()
    predictions = ["a.py", "b.py", "c.py"]
    ground_truth = {"b.py", "c.py"}

    assert metrics.mrr(predictions, ground_truth) == 0.5
    assert metrics.average_precision_at_k(predictions, ground_truth, 3) == 0.5833
    assert metrics.ndcg_at_k(predictions, ground_truth, 3) == 0.6934


def test_metrics_handle_empty_inputs() -> None:
    metrics = EvaluationMetrics()

    assert metrics.precision_at_k([], {"a.py"}, 5) == 0.0
    assert metrics.recall_at_k(["a.py"], set(), 5) == 0.0
    assert metrics.mrr(["a.py"], {"b.py"}) == 0.0
