import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import (
    BugReport,
    AnalysisRun,
    AgentResult,
    UserFeedback,
    RetrievedDefect,
    HistoricalDefect,
    DefectChunk
)


class BugReportRepository:
    """CRUD operations for submitted bug reports."""

    @staticmethod
    def create(
        session: Session,
        title: str,
        description: Optional[str] = None,
        stack_trace: Optional[str] = None,
        log_content: Optional[str] = None,
        language: Optional[str] = "Unknown",
        severity: Optional[str] = "Medium"
    ) -> BugReport:
        bug = BugReport(
            title=title.strip(),
            description=description.strip() if description else None,
            stack_trace=stack_trace.strip() if stack_trace else None,
            log_content=log_content.strip() if log_content else None,
            language=language or "Unknown",
            severity=severity or "Medium"
        )
        session.add(bug)
        session.flush()
        return bug

    @staticmethod
    def get_by_id(session: Session, bug_id: str) -> Optional[BugReport]:
        return session.query(BugReport).filter(BugReport.bug_id == bug_id).first()

    @staticmethod
    def list_all(session: Session, limit: int = 50, offset: int = 0) -> List[BugReport]:
        return (
            session.query(BugReport)
            .order_by(BugReport.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count(session: Session) -> int:
        return session.query(BugReport).count()


class AnalysisRunRepository:
    """CRUD operations for diagnostic analysis runs."""

    @staticmethod
    def create(session: Session, bug_id: str) -> AnalysisRun:
        run = AnalysisRun(bug_id=bug_id, status="PENDING")
        session.add(run)
        session.flush()
        return run

    @staticmethod
    def get_by_id(session: Session, analysis_id: str) -> Optional[AnalysisRun]:
        return session.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()

    @staticmethod
    def get_latest_for_bug(session: Session, bug_id: str) -> Optional[AnalysisRun]:
        return (
            session.query(AnalysisRun)
            .filter(AnalysisRun.bug_id == bug_id)
            .order_by(AnalysisRun.started_at.desc())
            .first()
        )

    @staticmethod
    def update_status(
        session: Session,
        analysis_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[AnalysisRun]:
        run = session.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()
        if run:
            run.status = status
            if error_message:
                run.error_message = error_message
            if status in ("COMPLETED", "FAILED"):
                run.completed_at = datetime.now(timezone.utc)
            session.flush()
        return run

    @staticmethod
    def count(session: Session) -> int:
        return session.query(AnalysisRun).count()


class AgentResultRepository:
    """CRUD operations for agent outputs."""

    @staticmethod
    def save_result(
        session: Session,
        analysis_id: str,
        agent_name: str,
        output_data: Dict[str, Any]
    ) -> AgentResult:
        result = AgentResult(
            analysis_id=analysis_id,
            agent_name=agent_name,
            output_json=json.dumps(output_data)
        )
        session.add(result)
        session.flush()
        return result

    @staticmethod
    def get_results_by_analysis_id(
        session: Session, analysis_id: str
    ) -> List[AgentResult]:
        return (
            session.query(AgentResult)
            .filter(AgentResult.analysis_id == analysis_id)
            .order_by(AgentResult.created_at.asc())
            .all()
        )


class RetrievedDefectRepository:
    """CRUD operations for RAG retrieved defects associated with an analysis."""

    @staticmethod
    def save_retrievals(
        session: Session,
        analysis_id: str,
        retrievals: List[Dict[str, Any]]
    ) -> List[RetrievedDefect]:
        saved = []
        for r in retrievals:
            rd = RetrievedDefect(
                analysis_id=analysis_id,
                defect_id=r["defect_id"],
                similarity_score=float(r.get("similarity_score", 0.0))
            )
            session.add(rd)
            saved.append(rd)
        session.flush()
        return saved

    @staticmethod
    def get_by_analysis_id(session: Session, analysis_id: str) -> List[RetrievedDefect]:
        return (
            session.query(RetrievedDefect)
            .filter(RetrievedDefect.analysis_id == analysis_id)
            .all()
        )


class HistoricalDefectRepository:
    """CRUD operations for historical defect knowledge base in relational storage."""

    @staticmethod
    def upsert(
        session: Session,
        defect_id: str,
        source: str,
        title: str,
        description: Optional[str] = None,
        resolution: Optional[str] = None,
        project: Optional[str] = None,
        status: str = "RESOLVED",
        language: Optional[str] = None
    ) -> HistoricalDefect:
        existing = session.query(HistoricalDefect).filter(HistoricalDefect.defect_id == defect_id).first()
        if existing:
            existing.source = source
            existing.title = title
            existing.description = description
            existing.resolution = resolution
            existing.project = project
            existing.status = status
            existing.language = language
            session.flush()
            return existing

        defect = HistoricalDefect(
            defect_id=defect_id,
            source=source,
            project=project,
            title=title,
            description=description,
            resolution=resolution,
            status=status,
            language=language
        )
        session.add(defect)
        session.flush()
        return defect

    @staticmethod
    def get_by_id(session: Session, defect_id: str) -> Optional[HistoricalDefect]:
        return session.query(HistoricalDefect).filter(HistoricalDefect.defect_id == defect_id).first()

    @staticmethod
    def list_all(session: Session, limit: int = 50, offset: int = 0) -> List[HistoricalDefect]:
        return session.query(HistoricalDefect).offset(offset).limit(limit).all()

    @staticmethod
    def count(session: Session) -> int:
        return session.query(HistoricalDefect).count()


class UserFeedbackRepository:
    """CRUD operations for user feedback."""

    @staticmethod
    def add_feedback(
        session: Session,
        analysis_id: str,
        feedback: str,
        is_accurate: bool = True,
        rating: Optional[float] = None
    ) -> UserFeedback:
        fb = UserFeedback(
            analysis_id=analysis_id,
            feedback=feedback,
            is_accurate=is_accurate,
            rating=rating
        )
        session.add(fb)
        session.flush()
        return fb

    @staticmethod
    def get_by_analysis_id(session: Session, analysis_id: str) -> List[UserFeedback]:
        return (
            session.query(UserFeedback)
            .filter(UserFeedback.analysis_id == analysis_id)
            .all()
        )
