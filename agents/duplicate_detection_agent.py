from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from knowledge_base.retrieval import SemanticRetrievalEngine


class DuplicateDetectionAgent(BaseAgent):
    """Retrieves and ranks semantically similar historical defects from Mozilla, Apache, Eclipse."""

    def __init__(self, retrieval_engine: SemanticRetrievalEngine = None):
        super().__init__(name="DuplicateDetectionAgent")
        self.retrieval_engine = retrieval_engine or SemanticRetrievalEngine()

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        title = context.get("title", "")
        description = context.get("description", "")
        stack_trace = context.get("stack_trace", "")
        language = context.get("language")

        # Formulate query text combining title, description, and stack trace
        query_text = f"{title}\n{description}"
        if stack_trace:
            query_text += f"\n{stack_trace[:500]}"

        # Retrieve top 5 matching defects from ChromaDB
        matches = self.retrieval_engine.retrieve_similar_defects(
            query_text=query_text,
            top_k=5,
            language_filter=language
        )

        similar_bugs: List[Dict[str, Any]] = []
        for m in matches:
            similar_bugs.append({
                "defect_id": m["defect_id"],
                "similarity_score": m["similarity_score"],
                "source": m["source"],
                "project": m.get("project", "General"),
                "title": m["title"],
                "resolution": m.get("resolution", "No verified fix logged.")
            })

        return {
            "similar_bugs": similar_bugs,
            "retrieved_count": len(similar_bugs),
            "analysis_mode": "rag-retrieval"
        }
