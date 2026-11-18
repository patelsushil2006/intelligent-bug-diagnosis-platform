from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class StandardDefectRecord(BaseModel):
    """Standardized software defect representation across Mozilla, Apache, and Eclipse."""
    defect_id: str
    source: str  # Mozilla, Apache, Eclipse
    project: Optional[str] = "Unknown"
    title: str
    description: Optional[str] = ""
    stack_trace: Optional[str] = ""
    comments: List[str] = Field(default_factory=list)
    resolution: Optional[str] = ""
    status: str = "RESOLVED"
    language: Optional[str] = "General"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BaseDatasetAdapter(ABC):
    """Abstract adapter for importing defect datasets."""

    @abstractmethod
    def parse_record(self, raw_data: Dict[str, Any]) -> Optional[StandardDefectRecord]:
        """Convert a raw dataset record into StandardDefectRecord."""
        pass

    @abstractmethod
    def parse_batch(self, raw_records: List[Dict[str, Any]]) -> List[StandardDefectRecord]:
        """Convert multiple raw dataset records."""
        pass
