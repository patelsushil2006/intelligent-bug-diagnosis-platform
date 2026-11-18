from knowledge_base.retrieval import SemanticRetrievalEngine
from knowledge_base.evaluation import RetrievalEvaluator


def test_retrieval_and_ranking():
    retrieval = SemanticRetrievalEngine()
    results = retrieval.retrieve_similar_defects(
        query_text="No module named 'flask' in app.py execution",
        top_k=3
    )
    assert isinstance(results, list)
    if results:
        top_match = results[0]
        assert "defect_id" in top_match
        assert "similarity_score" in top_match
        assert 0.0 <= top_match["similarity_score"] <= 1.0


def test_retrieval_evaluator_metrics():
    retrieved = [
        {"defect_id": "APACHE-100", "similarity_score": 0.95},
        {"defect_id": "MOZILLA-200", "similarity_score": 0.85},
        {"defect_id": "ECLIPSE-300", "similarity_score": 0.75}
    ]

    metrics = RetrievalEvaluator.calculate_metrics(
        ground_truth_id="APACHE-100",
        retrieved_defects=retrieved,
        k=3
    )

    assert metrics["recall@3"] == 1.0
    assert metrics["mrr"] == 1.0
