import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def get_utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class BugReport(Base):
    """Stores incoming bug submissions, stack traces, and logs."""
    __tablename__ = "bug_reports"

    bug_id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    log_content = Column(Text, nullable=True)
    language = Column(String(50), nullable=True, default="Unknown")
    severity = Column(String(30), nullable=True, default="Medium")
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    analysis_runs = relationship(
        "AnalysisRun", back_populates="bug_report", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "bug_id": self.bug_id,
            "title": self.title,
            "description": self.description,
            "stack_trace": self.stack_trace,
            "log_content": self.log_content,
            "language": self.language,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AnalysisRun(Base):
    """Tracks each diagnostic execution of multi-agent analysis for a bug."""
    __tablename__ = "analysis_runs"

    analysis_id = Column(String(36), primary_key=True, default=generate_uuid)
    bug_id = Column(String(36), ForeignKey("bug_reports.bug_id"), nullable=False)
    status = Column(String(30), default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=get_utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    bug_report = relationship("BugReport", back_populates="analysis_runs")
    agent_results = relationship(
        "AgentResult", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    user_feedback = relationship(
        "UserFeedback", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    retrieved_defects = relationship(
        "RetrievedDefect", back_populates="analysis_run", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "analysis_id": self.analysis_id,
            "bug_id": self.bug_id,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AgentResult(Base):
    """Captures structured outputs from individual AI agents."""
    __tablename__ = "agent_results"

    result_id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.analysis_id"), nullable=False)
    agent_name = Column(String(50), nullable=False)  # triage, log_analysis, duplicate_detection, root_cause, remediation
    output_json = Column(Text, nullable=False)  # Serialized JSON
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    analysis_run = relationship("AnalysisRun", back_populates="agent_results")

    __table_args__ = (
        Index("idx_analysis_agent", "analysis_id", "agent_name"),
    )

    def to_dict(self):
        import json
        return {
            "result_id": self.result_id,
            "analysis_id": self.analysis_id,
            "agent_name": self.agent_name,
            "output": json.loads(self.output_json) if self.output_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserFeedback(Base):
    """User feedback for fix recommendations and diagnoses."""
    __tablename__ = "user_feedback"

    feedback_id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.analysis_id"), nullable=False)
    feedback = Column(Text, nullable=True)
    is_accurate = Column(Boolean, default=True)
    rating = Column(Float, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    analysis_run = relationship("AnalysisRun", back_populates="user_feedback")

    def to_dict(self):
        return {
            "feedback_id": self.feedback_id,
            "analysis_id": self.analysis_id,
            "feedback": self.feedback,
            "is_accurate": self.is_accurate,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RetrievedDefect(Base):
    """Stores defect references matched from the RAG vector store for an analysis."""
    __tablename__ = "retrieved_defects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.analysis_id"), nullable=False)
    defect_id = Column(String(100), nullable=False)
    similarity_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    analysis_run = relationship("AnalysisRun", back_populates="retrieved_defects")

    def to_dict(self):
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "defect_id": self.defect_id,
            "similarity_score": self.similarity_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HistoricalDefect(Base):
    """Historical software defect metadata from Mozilla, Apache, Eclipse."""
    __tablename__ = "historical_defects"

    defect_id = Column(String(100), primary_key=True)
    source = Column(String(50), nullable=False)  # Mozilla, Apache, Eclipse, Verified-User
    project = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    status = Column(String(50), default="RESOLVED")
    language = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    chunks = relationship("DefectChunk", back_populates="defect", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "defect_id": self.defect_id,
            "source": self.source,
            "project": self.project,
            "title": self.title,
            "description": self.description,
            "resolution": self.resolution,
            "status": self.status,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DefectChunk(Base):
    """Semantic text chunks mapped to vector embeddings in ChromaDB."""
    __tablename__ = "defect_chunks"

    chunk_id = Column(String(100), primary_key=True, default=generate_uuid)
    defect_id = Column(String(100), ForeignKey("historical_defects.defect_id"), nullable=False)
    chunk_type = Column(String(50), nullable=False)  # description, stack_trace, comment, resolution
    chunk_text = Column(Text, nullable=False)
    vector_id = Column(String(100), nullable=True)

    defect = relationship("HistoricalDefect", back_populates="chunks")

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "defect_id": self.defect_id,
            "chunk_type": self.chunk_type,
            "chunk_text": self.chunk_text,
            "vector_id": self.vector_id,
        }
