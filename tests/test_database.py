import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import (
    Base,
    BugReport,
    AnalysisRun,
    AgentResult,
    RetrievedDefect,
    HistoricalDefect,
    UserFeedback
)
from database.repositories import (
    BugReportRepository,
    AnalysisRunRepository,
    AgentResultRepository,
    HistoricalDefectRepository,
    UserFeedbackRepository
)


@pytest.fixture
def test_db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


def test_bug_report_crud(test_db_session):
    bug = BugReportRepository.create(
        session=test_db_session,
        title="IndexError in array parsing",
        description="List index out of range when array is empty",
        language="Python",
        severity="High"
    )
    test_db_session.commit()

    assert bug.bug_id is not None
    assert bug.title == "IndexError in array parsing"

    fetched = BugReportRepository.get_by_id(test_db_session, bug.bug_id)
    assert fetched is not None
    assert fetched.language == "Python"
    assert BugReportRepository.count(test_db_session) == 1


def test_analysis_run_relationships(test_db_session):
    bug = BugReportRepository.create(
        session=test_db_session,
        title="NullPointer in Java service"
    )
    test_db_session.commit()

    run = AnalysisRunRepository.create(test_db_session, bug.bug_id)
    test_db_session.commit()

    assert run.status == "PENDING"
    assert run.bug_id == bug.bug_id

    # Agent result
    res = AgentResultRepository.save_result(
        test_db_session, run.analysis_id, "triage", {"category": "Runtime Error"}
    )
    test_db_session.commit()

    results = AgentResultRepository.get_results_by_analysis_id(test_db_session, run.analysis_id)
    assert len(results) == 1
    assert results[0].agent_name == "triage"

    # Feedback
    fb = UserFeedbackRepository.add_feedback(test_db_session, run.analysis_id, "Great diagnosis!", True, 5.0)
    test_db_session.commit()
    assert fb.is_accurate is True


def test_historical_defect_upsert(test_db_session):
    defect = HistoricalDefectRepository.upsert(
        session=test_db_session,
        defect_id="APACHE-1234",
        source="Apache",
        title="Buffer overflow in request header parser",
        resolution="Added length check"
    )
    test_db_session.commit()

    assert defect.defect_id == "APACHE-1234"
    assert HistoricalDefectRepository.count(test_db_session) == 1
