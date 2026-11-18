import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from config.config import Config
from knowledge_base.chunking import DefectSemanticChunk

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """Persistent ChromaDB vector store client for historical defect embeddings."""

    COLLECTION_NAME = "historical_defects"

    def __init__(self, persist_dir: str = str(Config.VECTOR_STORE_DIR)):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Historical Defect Knowledge Base Chunks (Mozilla, Apache, Eclipse)"}
        )

    def add_chunks(
        self,
        chunks: List[DefectSemanticChunk],
        embeddings: List[List[float]]
    ) -> int:
        """Insert semantic defect chunks and their corresponding embeddings into ChromaDB."""
        if not chunks or not embeddings:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = []

        for c in chunks:
            # Flatten metadata into primitives required by ChromaDB
            meta = {}
            for k, v in c.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                elif v is None:
                    meta[k] = ""
                else:
                    meta[k] = str(v)
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Upserted {len(chunks)} chunks into ChromaDB.")
        return len(chunks)

    def query_similarity(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query top-K similar chunks from ChromaDB."""
        if not query_embedding:
            return []

        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"]
        }

        if where_filter:
            kwargs["where"] = where_filter

        try:
            results = self.collection.query(**kwargs)
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []

        matched: List[Dict[str, Any]] = []

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0] if results["documents"] else [""] * len(ids)
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
        distances = results["distances"][0] if results["distances"] else [1.0] * len(ids)

        for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
            # ChromaDB cosine distance range is [0, 2]; similarity is 1 - (distance / 2) or 1 - distance depending on metric
            # We map distance to a normalized similarity score
            similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            matched.append({
                "chunk_id": chunk_id,
                "text": doc,
                "metadata": meta,
                "distance": dist,
                "similarity_score": round(similarity, 4)
            })

        return matched

    def count(self) -> int:
        """Count total vectors in collection."""
        return self.collection.count()

    def reset(self):
        """Reset the historical defects collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(name=self.COLLECTION_NAME)
