from typing import List, Dict, Any


class RetrievalEvaluator:
    """Evaluates RAG retrieval quality using Precision@K, Recall@K, and MRR metrics."""

    @staticmethod
    def calculate_metrics(
        ground_truth_id: str,
        retrieved_defects: List[Dict[str, Any]],
        k: int = 5
    ) -> Dict[str, float]:
        """Compute evaluation metrics for a single query."""
        top_k = retrieved_defects[:k]
        retrieved_ids = [d.get("defect_id") for d in top_k]

        is_hit = ground_truth_id in retrieved_ids
        recall_at_k = 1.0 if is_hit else 0.0
        precision_at_k = (1.0 / len(top_k)) if is_hit and top_k else 0.0

        reciprocal_rank = 0.0
        if is_hit:
            rank = retrieved_ids.index(ground_truth_id) + 1
            reciprocal_rank = 1.0 / rank

        return {
            f"recall@{k}": recall_at_k,
            f"precision@{k}": round(precision_at_k, 4),
            "mrr": round(reciprocal_rank, 4)
        }
