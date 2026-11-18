from typing import List, Dict, Any
from pydantic import BaseModel
from knowledge_base.adapters.base_adapter import StandardDefectRecord


class DefectSemanticChunk(BaseModel):
    """Represents a discrete semantic chunk of defect knowledge for vector indexing."""
    chunk_id: str
    defect_id: str
    chunk_type: str  # title_description, stack_trace, comment, resolution
    text: str
    metadata: Dict[str, Any]


class SemanticChunker:
    """Splits standardized defect records into distinct semantic chunks with metadata."""

    @classmethod
    def chunk_defect(cls, defect: StandardDefectRecord) -> List[DefectSemanticChunk]:
        chunks: List[DefectSemanticChunk] = []

        base_meta = {
            "defect_id": defect.defect_id,
            "source": defect.source,
            "project": defect.project,
            "language": defect.language,
            "status": defect.status,
            "title": defect.title
        }

        # 1. Title + Description chunk
        desc_text = f"Title: {defect.title}\nDescription: {defect.description}"
        if defect.description.strip() or defect.title.strip():
            chunks.append(DefectSemanticChunk(
                chunk_id=f"{defect.defect_id}_desc",
                defect_id=defect.defect_id,
                chunk_type="title_description",
                text=desc_text.strip(),
                metadata={**base_meta, "chunk_type": "title_description"}
            ))

        # 2. Stack trace chunk
        if defect.stack_trace and defect.stack_trace.strip():
            chunks.append(DefectSemanticChunk(
                chunk_id=f"{defect.defect_id}_stack",
                defect_id=defect.defect_id,
                chunk_type="stack_trace",
                text=f"Defect {defect.defect_id} Stack Trace:\n{defect.stack_trace.strip()}",
                metadata={**base_meta, "chunk_type": "stack_trace"}
            ))

        # 3. Investigation Comments chunk (aggregated or top comments)
        if defect.comments:
            combined_comments = "\n---\n".join(defect.comments[:5])
            chunks.append(DefectSemanticChunk(
                chunk_id=f"{defect.defect_id}_comments",
                defect_id=defect.defect_id,
                chunk_type="comment",
                text=f"Developer Investigation Notes:\n{combined_comments}",
                metadata={**base_meta, "chunk_type": "comment"}
            ))

        # 4. Resolution chunk
        if defect.resolution and defect.resolution.strip():
            chunks.append(DefectSemanticChunk(
                chunk_id=f"{defect.defect_id}_resolution",
                defect_id=defect.defect_id,
                chunk_type="resolution",
                text=f"Resolution & Fix for {defect.title}:\n{defect.resolution.strip()}",
                metadata={**base_meta, "chunk_type": "resolution"}
            ))

        return chunks

    @classmethod
    def chunk_batch(cls, defects: List[StandardDefectRecord]) -> List[DefectSemanticChunk]:
        all_chunks = []
        for defect in defects:
            all_chunks.extend(cls.chunk_defect(defect))
        return all_chunks
