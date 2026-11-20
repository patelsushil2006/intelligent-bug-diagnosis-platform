import re
from typing import List, Set
from knowledge_base.adapters.base_adapter import StandardDefectRecord


class DataCleaner:
    """Cleans, normalizes, and deduplicates historical defect records."""

    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Strip HTML tags, clean URLs, and normalize whitespace."""
        if not text:
            return ""
        # Remove HTML
        cleaned = cls.HTML_TAG_PATTERN.sub(' ', text)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @classmethod
    def clean_record(cls, record: StandardDefectRecord) -> StandardDefectRecord:
        """Clean an individual defect record."""
        return StandardDefectRecord(
            defect_id=record.defect_id.strip(),
            source=record.source.strip(),
            project=cls.clean_text(record.project) or "General",
            title=cls.clean_text(record.title),
            description=cls.clean_text(record.description),
            stack_trace=record.stack_trace.strip() if record.stack_trace else "",
            comments=[cls.clean_text(c) for c in record.comments if cls.clean_text(c)],
            resolution=cls.clean_text(record.resolution) or "Fixed in codebase",
            status=record.status.strip() or "RESOLVED",
            language=record.language or "General"
        )

    @classmethod
    def deduplicate(cls, records: List[StandardDefectRecord]) -> List[StandardDefectRecord]:
        """Remove duplicates by defect_id and normalized title."""
        seen_ids: Set[str] = set()
        seen_titles: Set[str] = set()
        unique_records: List[StandardDefectRecord] = []

        for record in records:
            clean = cls.clean_record(record)
            if not clean.title:
                continue

            id_key = clean.defect_id.lower()
            title_key = clean.title.lower()

            if id_key in seen_ids or title_key in seen_titles:
                continue

            seen_ids.add(id_key)
            seen_titles.add(title_key)
            unique_records.append(clean)

        return unique_records
