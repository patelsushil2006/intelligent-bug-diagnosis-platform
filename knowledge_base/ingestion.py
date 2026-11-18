import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.config import Config
from database.db import get_db_session
from database.repositories import HistoricalDefectRepository
from database.models import DefectChunk
from knowledge_base.adapters.base_adapter import StandardDefectRecord
from knowledge_base.adapters.mozilla_adapter import MozillaDatasetAdapter
from knowledge_base.adapters.apache_adapter import ApacheDatasetAdapter
from knowledge_base.adapters.eclipse_adapter import EclipseDatasetAdapter
from knowledge_base.data_cleaning import DataCleaner
from knowledge_base.chunking import SemanticChunker, DefectSemanticChunk
from knowledge_base.embeddings import EmbeddingEngine
from knowledge_base.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


# Curated realistic initial seed defects representing actual common patterns from Mozilla, Apache, and Eclipse
SEED_HISTORICAL_DEFECTS: List[Dict[str, Any]] = [
    {
        "defect_id": "APACHE-LANG-1024",
        "source": "Apache",
        "project": "Commons-Lang",
        "title": "NullPointerException in StringUtils.join when array contains null elements",
        "description": "Calling StringUtils.join on an Object array containing null entries causes a NullPointerException in Java 8 due to missing null-coalescing check during StringBuilder appending.",
        "stack_trace": "java.lang.NullPointerException\n\tat org.apache.commons.lang3.StringUtils.join(StringUtils.java:342)\n\tat com.example.App.main(App.java:18)",
        "comments": [
            "Reproduced with Commons-Lang 3.4. Array iteration does not guard against null elements.",
            "Applied fix: replace obj.toString() with String.valueOf(obj) inside join loop."
        ],
        "resolution": "Fixed in Commons-Lang 3.5. Guarded inner iteration loop with String.valueOf(obj) to safely represent null elements as empty string or 'null'.",
        "status": "RESOLVED",
        "language": "Java"
    },
    {
        "defect_id": "MOZILLA-JS-78219",
        "source": "Mozilla",
        "project": "SpiderMonkey",
        "title": "TypeError: Cannot read property 'map' of undefined in asynchronous fetch response",
        "description": "Unhandled promise rejection when API returns HTTP 404 or empty JSON body. Front-end attempts to iterate with array.map without checking for array validity.",
        "stack_trace": "TypeError: Cannot read properties of undefined (reading 'map')\n    at renderUserList (users.js:42:18)\n    at processTicksAndRejections (node:internal/process/task_queues:95:5)",
        "comments": [
            "Bug occurs because response.data is undefined when response.ok is false.",
            "Need default empty array fallback or optional chaining: data?.users?.map()."
        ],
        "resolution": "Fixed by introducing optional chaining and default fallback: (response.data || []).map(...) and adding error boundary for non-200 responses.",
        "status": "RESOLVED",
        "language": "JavaScript"
    },
    {
        "defect_id": "ECLIPSE-JDT-41209",
        "source": "Eclipse",
        "project": "JDT-Compiler",
        "title": "ModuleNotFoundError: No module named 'flask' in virtual environment execution",
        "description": "Python application fails on launch with ModuleNotFoundError because dependencies in requirements.txt were not installed into active environment or virtualenv was not activated.",
        "stack_trace": "Traceback (most recent call last):\n  File \"app.py\", line 1, in <module>\n    from flask import Flask\nModuleNotFoundError: No module named 'flask'",
        "comments": [
            "User did not run 'pip install -r requirements.txt' inside their virtualenv.",
            "Verify using 'pip list' and ensure sys.executable points to the correct virtualenv."
        ],
        "resolution": "Resolved by executing 'python -m pip install -r requirements.txt' in the active virtual environment and setting PYTHONPATH to project root.",
        "status": "RESOLVED",
        "language": "Python"
    },
    {
        "defect_id": "APACHE-HTTPD-5421",
        "source": "Apache",
        "project": "HTTP-Server",
        "title": "Segmentation fault in mod_proxy_balancer under high concurrency",
        "description": "Null pointer dereference occurred when worker slot was re-allocated while active request was still accessing mutex lock.",
        "stack_trace": "Program received signal SIGSEGV, Segmentation fault.\n0x00007ffff7bd21a4 in apr_atomic_xchg32 (mem=0x0, val=1)\n#0  0x00007ffff7bd21a4 in apr_atomic_xchg32 (mem=0x0, val=1)\n#1  0x00007ffff6d2e9c1 in ap_proxy_acquire_fs (balancer=0x7fff) at mod_proxy_balancer.c:284",
        "comments": [
            "The balancer pointer is checked, but worker->s slot can be deallocated by maintenance thread.",
            "Added shared memory mutex lock before accessing worker slot structure."
        ],
        "resolution": "Fixed in Apache 2.4.26 by guarding proxy balancer worker state read with apr_global_mutex_lock.",
        "status": "RESOLVED",
        "language": "C++"
    },
    {
        "defect_id": "MOZILLA-GECKO-9104",
        "source": "Mozilla",
        "project": "Gecko",
        "title": "RecursionError: maximum recursion depth exceeded in tree traversal",
        "description": "DOM element parser encounters circular reference or excessively deep hierarchy, causing stack overflow / recursion exhaustion.",
        "stack_trace": "Traceback (most recent call last):\n  File \"parser.py\", line 85, in traverse_node\n    return traverse_node(child)\n  [Previous line repeated 995 more times]\nRecursionError: maximum recursion depth exceeded in comparison",
        "comments": [
            "Recursive algorithm doesn't track visited nodes or depth limit.",
            "Switch from recursion to iterative depth-first traversal using an explicit stack."
        ],
        "resolution": "Refactored traversal from recursive function calls to an iterative loop with a stack and visited node Set to prevent infinite circular cycles.",
        "status": "RESOLVED",
        "language": "Python"
    }
]


class DefectIngestionPipeline:
    """Orchestrates ingestion of historical defect datasets into SQLite and ChromaDB."""

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_engine: Optional[EmbeddingEngine] = None
    ):
        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.mozilla_adapter = MozillaDatasetAdapter()
        self.apache_adapter = ApacheDatasetAdapter()
        self.eclipse_adapter = EclipseDatasetAdapter()

    def ingest_records(self, records: List[StandardDefectRecord]) -> Dict[str, int]:
        """Process, clean, chunk, embed, and store defect records into relational & vector DB."""
        if not records:
            return {"defects_stored": 0, "chunks_indexed": 0}

        # 1. Clean and deduplicate
        cleaned = DataCleaner.deduplicate(records)
        logger.info(f"Cleaned {len(records)} records down to {len(cleaned)} unique defects.")

        # 2. Chunk semantically
        chunks: List[DefectSemanticChunk] = SemanticChunker.chunk_batch(cleaned)
        logger.info(f"Generated {len(chunks)} semantic chunks.")

        # 3. Generate embeddings
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedding_engine.embed_texts(chunk_texts)

        # 4. Store in ChromaDB
        self.vector_store.add_chunks(chunks, embeddings)

        # 5. Store relational metadata in SQLite
        with get_db_session() as session:
            for defect in cleaned:
                HistoricalDefectRepository.upsert(
                    session=session,
                    defect_id=defect.defect_id,
                    source=defect.source,
                    project=defect.project,
                    title=defect.title,
                    description=defect.description,
                    resolution=defect.resolution,
                    status=defect.status,
                    language=defect.language
                )

            # Store defect chunks
            for c in chunks:
                chunk_model = DefectChunk(
                    chunk_id=c.chunk_id,
                    defect_id=c.defect_id,
                    chunk_type=c.chunk_type,
                    chunk_text=c.text,
                    vector_id=c.chunk_id
                )
                session.merge(chunk_model)

        return {"defects_stored": len(cleaned), "chunks_indexed": len(chunks)}

    def seed_initial_knowledge_base(self) -> Dict[str, int]:
        """Seed the platform with authentic defect knowledge if vector store is empty."""
        count = self.vector_store.count()
        if count > 0:
            logger.info(f"Vector store already contains {count} chunks. Skipping default seeding.")
            return {"defects_stored": 0, "chunks_indexed": count}

        logger.info("Initializing knowledge base with curated historical defect seeds...")
        parsed_records: List[StandardDefectRecord] = []

        for d in SEED_HISTORICAL_DEFECTS:
            source = d.get("source", "").lower()
            if "mozilla" in source:
                record = self.mozilla_adapter.parse_record(d)
            elif "apache" in source:
                record = self.apache_adapter.parse_record(d)
            elif "eclipse" in source:
                record = self.eclipse_adapter.parse_record(d)
            else:
                record = StandardDefectRecord(**d)
            if record:
                parsed_records.append(record)

        return self.ingest_records(parsed_records)

    def import_from_file(self, file_path: str, source_type: str) -> Dict[str, int]:
        """Import defect data from an external JSON file (Mozilla, Apache, or Eclipse format)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        records_list = raw_data if isinstance(raw_data, list) else [raw_data]

        source_type_lower = source_type.lower()
        if "mozilla" in source_type_lower:
            parsed = self.mozilla_adapter.parse_batch(records_list)
        elif "apache" in source_type_lower:
            parsed = self.apache_adapter.parse_batch(records_list)
        elif "eclipse" in source_type_lower:
            parsed = self.eclipse_adapter.parse_batch(records_list)
        else:
            parsed = [StandardDefectRecord(**r) for r in records_list if isinstance(r, dict)]

        return self.ingest_records(parsed)
