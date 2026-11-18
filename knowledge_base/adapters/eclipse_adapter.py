from typing import Dict, Any, List, Optional
from knowledge_base.adapters.base_adapter import BaseDatasetAdapter, StandardDefectRecord


class EclipseDatasetAdapter(BaseDatasetAdapter):
    """Adapter for Eclipse Bugzilla defect datasets."""

    def parse_record(self, raw: Dict[str, Any]) -> Optional[StandardDefectRecord]:
        defect_id = str(raw.get("bug_id") or raw.get("id") or "").strip()
        if not defect_id:
            return None

        if not defect_id.startswith("ECLIPSE-"):
            defect_id = f"ECLIPSE-{defect_id}"

        title = raw.get("short_desc") or raw.get("summary") or "Untitled Bug"
        description = raw.get("thetext") or raw.get("description") or ""
        resolution = raw.get("resolution") or "RESOLVED FIXED"
        project = raw.get("product") or raw.get("component") or "Eclipse Platform"
        status = raw.get("bug_status") or raw.get("status") or "CLOSED"

        comments = []
        raw_comments = raw.get("long_desc") or raw.get("comments") or []
        if isinstance(raw_comments, list):
            for c in raw_comments:
                if isinstance(c, dict):
                    comments.append(c.get("thetext") or c.get("text", ""))
                elif isinstance(c, str):
                    comments.append(c)

        return StandardDefectRecord(
            defect_id=defect_id,
            source="Eclipse",
            project=project,
            title=str(title).strip(),
            description=str(description).strip(),
            comments=[c.strip() for c in comments if c.strip()],
            resolution=str(resolution).strip(),
            status=str(status).strip(),
            language=raw.get("language") or "Java"
        )

    def parse_batch(self, raw_records: List[Dict[str, Any]]) -> List[StandardDefectRecord]:
        results = []
        for r in raw_records:
            record = self.parse_record(r)
            if record:
                results.append(record)
        return results
