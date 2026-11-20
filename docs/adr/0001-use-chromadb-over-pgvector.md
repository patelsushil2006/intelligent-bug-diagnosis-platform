# ADR 0001: Use ChromaDB Over pgvector

## Context
The platform requires an embedded vector database for semantic similarity matching of historical bug chunks.
Deploying PostgreSQL with the pgvector extension introduces external database server dependencies,
container networking overhead, and migration complexity during local development and automated CI testing.
We needed a lightweight solution that runs seamlessly without external service management.

## Decision
We chose ChromaDB (`chromadb.PersistentClient`) as our primary vector store.
Embeddings (384-dimensional dense vectors from `all-MiniLM-L6-v2`) and metadata are stored directly
on the local filesystem under `vector_store/data/` without requiring external database services.
The collection is initialized lazily and persisted across application restarts.

## Consequences
- **Positive:** Zero external infrastructure dependencies; developers can run the entire platform with `python app.py` or `docker compose up`. Fast startup and hermetic testing.
- **Positive:** Unit and integration tests run hermetically in memory or temporary directories in sub-second time.
- **Negative:** Limited horizontal scaling across distributed cluster nodes compared to managed PostgreSQL.
- **Negative:** Vector store persistence requires Docker volume mounts (`vector_store_data`) when deployed in containers.
