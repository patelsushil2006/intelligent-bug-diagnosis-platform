from knowledge_base.adapters.mozilla_adapter import MozillaDatasetAdapter
from knowledge_base.adapters.apache_adapter import ApacheDatasetAdapter
from knowledge_base.adapters.eclipse_adapter import EclipseDatasetAdapter
from knowledge_base.data_cleaning import DataCleaner
from knowledge_base.chunking import SemanticChunker


def test_mozilla_adapter():
    adapter = MozillaDatasetAdapter()
    raw = {
        "bug_id": "100201",
        "summary": "Crash in TabChild::RecvUpdate",
        "description": "Browser crashes when tab is dragged.",
        "resolution": "FIXED",
        "product": "Firefox"
    }
    record = adapter.parse_record(raw)
    assert record is not None
    assert record.defect_id == "MOZILLA-100201"
    assert record.source == "Mozilla"
    assert record.project == "Firefox"


def test_apache_adapter():
    adapter = ApacheDatasetAdapter()
    raw = {
        "key": "LANG-555",
        "fields": {
            "summary": "StringUtils.split produces empty token",
            "description": "Splitting with adjacent delimiters yields empty string.",
            "resolution": {"name": "Resolved"}
        }
    }
    record = adapter.parse_record(raw)
    assert record is not None
    assert record.defect_id == "LANG-555"
    assert record.source == "Apache"


def test_data_cleaning_and_deduplication():
    adapter = MozillaDatasetAdapter()
    r1 = adapter.parse_record({"bug_id": "1", "summary": "Bug <b>one</b>", "description": "desc"})
    r2 = adapter.parse_record({"bug_id": "1", "summary": "Bug one", "description": "desc"})

    unique = DataCleaner.deduplicate([r1, r2])
    assert len(unique) == 1
    assert "<b>" not in unique[0].title


def test_semantic_chunking():
    adapter = EclipseDatasetAdapter()
    record = adapter.parse_record({
        "id": "500",
        "short_desc": "Classpath collision",
        "thetext": "Two jars export the same package.",
        "resolution": "Use modular export"
    })
    chunks = SemanticChunker.chunk_defect(record)
    assert len(chunks) >= 2  # Description + Resolution
    types = [c.chunk_type for c in chunks]
    assert "title_description" in types
    assert "resolution" in types
