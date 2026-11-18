from flask import Blueprint, jsonify
from sqlalchemy import text
from database.db import get_db_session
from knowledge_base.vector_store import ChromaVectorStore
from agents.llm_client import LLMClient

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint reporting status of DB, ChromaDB, and agents."""
    db_status = "healthy"
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    chroma_count = 0
    chroma_status = "healthy"
    try:
        vs = ChromaVectorStore()
        chroma_count = vs.count()
    except Exception:
        chroma_status = "unhealthy"

    llm = LLMClient()

    return jsonify({
        "status": "healthy" if db_status == "healthy" and chroma_status == "healthy" else "degraded",
        "database": db_status,
        "vector_store": {
            "status": chroma_status,
            "indexed_chunks": chroma_count
        },
        "llm_service": {
            "mode": "llm-powered" if llm.is_llm_enabled() else "rule-based-fallback",
            "provider": llm.provider
        }
    }), 200
