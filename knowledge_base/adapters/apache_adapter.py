from typing import Dict, Any, List, Optional
from knowledge_base.adapters.base_adapter import BaseDatasetAdapter, StandardDefectRecord


class ApacheDatasetAdapter(BaseDatasetAdapter):
    """Adapter for Apache Jira / Bugzilla defect datasets."""

    def parse_record(self, raw: Dict[str, Any]) -> Optional[StandardDefectRecord]:
        defect_id = str(raw.get("key") or raw.get("issue_id") or raw.get("id") or "").strip()
        if not defect_id:
            return None

        if not defect_id.startswith("APACHE-") and "-" not in defect_id:
            defect_id = f"APACHE-{defect_id}"

        # Support both flat JSON and Jira nested structure
        fields = raw.get("fields", raw)

        title = fields.get("summary") or raw.get("title") or "Untitled Defect"
        description = fields.get("description") or raw.get("description") or ""

        resolution_field = fields.get("resolution") or raw.get("resolution") or "Fixed"
        if isinstance(resolution_field, dict):
            resolution = resolution_field.get("name", "Fixed")
        else:
            resolution = str(resolution_field)

        project_field = fields.get("project") or raw.get("project") or "Apache Commons"
        if isinstance(project_field, dict):
            project = project_field.get("name") or project_field.get("key", "Apache")
        else:
            project = str(project_field)

        status_field = fields.get("status") or raw.get("status") or "Closed"
        if isinstance(status_field, dict):
            status = status_field.get("name", "Closed")
        else:
            status = str(status_field)

        comments = []
        raw_comments = fields.get("comment", {}).get("comments", []) if isinstance(fields.get("comment"), dict) else raw.get("comments", [])
        if isinstance(raw_comments, list):
            for c in raw_comments:
                if isinstance(c, dict):
                    comments.append(c.get("body", ""))
                elif isinstance(c, str):
                    comments.append(c)

        return StandardDefectRecord(
            defect_id=defect_id,
            source="Apache",
            project=project,
            title=str(title).strip(),
            description=str(description).strip(),
            comments=[c.strip() for c in comments if c.strip()],
            resolution=resolution.strip(),
            status=status.strip(),
            language=raw.get("language") or "Java"
        )

    def parse_batch(self, raw_records: List[Dict[str, Any]]) -> List[StandardDefectRecord]:
        results = []
        for r in raw_records:
            record = self.parse_record(r)
            if record:
                results.append(record)
        return results
