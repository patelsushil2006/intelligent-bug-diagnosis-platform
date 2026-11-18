from typing import Dict, Any, List, Optional
from knowledge_base.adapters.base_adapter import BaseDatasetAdapter, StandardDefectRecord


class MozillaDatasetAdapter(BaseDatasetAdapter):
    """Adapter for Mozilla Bugzilla datasets."""

    def parse_record(self, raw: Dict[str, Any]) -> Optional[StandardDefectRecord]:
        defect_id = str(
            raw.get("defect_id")
            or raw.get("bug_id")
            or raw.get("id")
            or ""
        ).strip()
        if not defect_id:
            return None

        # Format defect ID
        if not defect_id.startswith("MOZILLA-"):
            defect_id = f"MOZILLA-{defect_id}"

        title = raw.get("title") or raw.get("summary") or raw.get("short_desc") or "Untitled Bug"
        description = raw.get("description") or raw.get("thetext") or ""
        resolution = raw.get("resolution") or raw.get("resolution_text") or "FIXED"
        project = raw.get("product") or raw.get("component") or "Firefox"
        status = raw.get("status") or "RESOLVED"

        # Comments
        raw_comments = raw.get("comments") or []
        comments = []
        if isinstance(raw_comments, list):
            for c in raw_comments:
                if isinstance(c, dict):
                    comments.append(c.get("text", ""))
                elif isinstance(c, str):
                    comments.append(c)

        # Detect stack traces in description/comments
        stack_trace = ""
        combined = description + "\n" + "\n".join(comments)
        if "at " in combined or "traceback" in combined.lower():
            stack_trace = combined

        return StandardDefectRecord(
            defect_id=defect_id,
            source="Mozilla",
            project=project,
            title=str(title).strip(),
            description=str(description).strip(),
            stack_trace=stack_trace.strip(),
            comments=[c.strip() for c in comments if c.strip()],
            resolution=str(resolution).strip(),
            status=str(status).strip(),
            language=raw.get("language") or "C++/JavaScript"
        )

    def parse_batch(self, raw_records: List[Dict[str, Any]]) -> List[StandardDefectRecord]:
        results = []
        for r in raw_records:
            record = self.parse_record(r)
            if record:
                results.append(record)
        return results
