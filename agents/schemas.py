from typing import Literal, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    category: str
    severity: Literal["Critical", "High", "Medium", "Low"]
    priority: Literal["P1", "P2", "P3", "P4"]
    affected_component: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    language: str
    keywords: list[str] = []


class LogAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    exception_type: str
    error_message: str
    failure_point: str        # "file:line" or "class.method"
    code_path: list[str]      # ordered frames
    confidence_score: float = Field(ge=0.0, le=1.0)
    summary: str
