# Data Model & Storage Specifications

The platform uses two independent, synchronized data stores:
1. **SQLite (Relational Storage):** Manages structured entities, analysis runs, agent outputs, and user feedback.
2. **ChromaDB (Vector Storage):** Manages high-dimensional embeddings and metadata for semantic defect retrieval.

---

## 1. Relational Database Schema (SQLAlchemy / SQLite)

```mermaid
erDiagram
    BUG_REPORT ||--o{ ANALYSIS_RUN : "triggers"
    ANALYSIS_RUN ||--o{ AGENT_RESULT : "produces"
    ANALYSIS_RUN ||--o{ USER_FEEDBACK : "receives"
    ANALYSIS_RUN ||--o{ RETRIEVED_DEFECT : "retrieves"
    HISTORICAL_DEFECT ||--o{ DEFECT_CHUNK : "contains"

    BUG_REPORT {
        string bug_id PK
        string title
        text description
        text stack_trace
        text log_content
        string language
        string severity
        datetime created_at
    }

    ANALYSIS_RUN {
        string analysis_id PK
        string bug_id FK
        string status
        text error_message
        datetime started_at
        datetime completed_at
    }

    AGENT_RESULT {
        string result_id PK
        string analysis_id FK
        string agent_name
        text output_json
        datetime created_at
    }

    RETRIEVED_DEFECT {
        string id PK
        string analysis_id FK
        string defect_id
        float similarity_score
        datetime created_at
    }

    USER_FEEDBACK {
        string feedback_id PK
        string analysis_id FK
        text feedback
        boolean is_accurate
        float rating
        datetime created_at
    }

    HISTORICAL_DEFECT {
        string defect_id PK
        string source
        string project
        string title
        text description
        text resolution
        string status
        string language
        datetime created_at
    }

    DEFECT_CHUNK {
        string chunk_id PK
        string defect_id FK
        string chunk_type
        text chunk_text
        string vector_id
    }
```

---

## 2. Vector Database Schema (ChromaDB)

- **Collection:** `historical_defects`
- **Embedding Dimensions:** 384 (`sentence-transformers/all-MiniLM-L6-v2`)
- **Distance Metric:** Cosine Distance ($D_{cosine} \in [0, 2]$)
- **Calculated Similarity Score:** $\text{Similarity} = \max(0.0, \min(1.0, 1.0 - \frac{D_{cosine}}{2.0}))$

### Chunk Metadata Structure:
```json
{
    "defect_id": "APACHE-LANG-1024",
    "source": "Apache",
    "project": "Commons-Lang",
    "chunk_type": "resolution",
    "language": "Java",
    "status": "RESOLVED",
    "title": "NullPointerException in StringUtils.join when array contains null elements"
}
```
