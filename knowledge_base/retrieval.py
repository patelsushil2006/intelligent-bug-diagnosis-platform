import logging
from typing import List, Dict, Any, Optional
from config.config import Config
from knowledge_base.embeddings import EmbeddingEngine
from knowledge_base.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class SemanticRetrievalEngine:
    """Retrieves relevant historical software defects and resolution evidence using RAG."""

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_engine: Optional[EmbeddingEngine] = None
    ):
        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_engine = embedding_engine or EmbeddingEngine()

    def retrieve_similar_defects(
        self,
        query_text: str,
        top_k: int = Config.TOP_K_RETRIEVAL,
        language_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve and rank historical defect chunks matching the query bug report."""
        if not query_text or not query_text.strip():
            return []

        # 1. Embed query
        query_vec = self.embedding_engine.embed_query(query_text.strip())

        # 2. Metadata filtering if specified
        where_filter = None
        if language_filter and language_filter.lower() not in ("unknown", "general", "auto", ""):
            where_filter = {"language": language_filter}

        # 3. Vector similarity search
        raw_matches = self.vector_store.query_similarity(
            query_embedding=query_vec,
            top_k=top_k * 2,  # Fetch slightly more to aggregate chunks by defect
            where_filter=where_filter
        )

        if not raw_matches and where_filter:
            # Fall back without language filter if strict filter returns 0 results
            raw_matches = self.vector_store.query_similarity(
                query_embedding=query_vec,
                top_k=top_k * 2
            )

        # 4. Aggregate chunks by defect_id to produce consolidated evidence
        defects_map: Dict[str, Dict[str, Any]] = {}

        for match in raw_matches:
            meta = match.get("metadata", {})
            defect_id = meta.get("defect_id") or match["chunk_id"]

            if defect_id not in defects_map:
                defects_map[defect_id] = {
                    "defect_id": defect_id,
                    "title": meta.get("title", "Untitled Defect"),
                    "source": meta.get("source", "Historical Archive"),
                    "project": meta.get("project", "Unknown Project"),
                    "language": meta.get("language", "General"),
                    "status": meta.get("status", "RESOLVED"),
                    "similarity_score": match["similarity_score"],
                    "matched_chunks": [],
                    "resolution": ""
                }

            # Update highest similarity score
            if match["similarity_score"] > defects_map[defect_id]["similarity_score"]:
                defects_map[defect_id]["similarity_score"] = match["similarity_score"]

            chunk_type = meta.get("chunk_type", "snippet")
            defects_map[defect_id]["matched_chunks"].append({
                "chunk_type": chunk_type,
                "text": match["text"],
                "score": match["similarity_score"]
            })

            if chunk_type == "resolution" and not defects_map[defect_id]["resolution"]:
                defects_map[defect_id]["resolution"] = match["text"]

        # Sort aggregated defects by similarity score
        ranked_defects = sorted(
            defects_map.values(),
            key=lambda d: d["similarity_score"],
            reverse=True
        )[:top_k]

        return ranked_defects
