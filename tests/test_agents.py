from agents.triage_agent import TriageAgent
from agents.log_analysis_agent import LogAnalysisAgent
from agents.duplicate_detection_agent import DuplicateDetectionAgent
from agents.root_cause_agent import RootCauseAgent
from agents.remediation_agent import RemediationAgent
from agents.orchestrator import AgentOrchestrator
from database.db import get_db_session
from database.repositories import BugReportRepository


def test_triage_schema_has_all_fields():
    from agents.triage_agent import TriageAgent
    from backend.bug_processor import BugProcessor
    out = TriageAgent().process("NullPointerException in auth.token.validate", "", "")
    for f in ["severity","priority","affected_component","confidence_score","reasoning"]:
        assert f in out and out[f] not in (None, "")


def test_triage_agent():
    agent = TriageAgent()
    context = {
        "title": "ModuleNotFoundError: No module named 'flask'",
        "description": "Fails on flask import in app.py",
        "stack_trace": "Traceback (most recent call last):\n  File 'app.py', line 1\nModuleNotFoundError: No module named 'flask'"
    }
    ok, output, _ = agent.execute(context)
    assert ok is True
    assert output["category"] == "Dependency Error"
    assert output["language"] == "Python"
    assert "flask" in [k.lower() for k in output["keywords"]]


def test_log_analysis_agent():
    agent = LogAnalysisAgent()
    context = {
        "stack_trace": 'File "app.py", line 14, in run\n    raise ValueError("Invalid configuration")\nValueError: Invalid configuration'
    }
    ok, output, _ = agent.execute(context)
    assert ok is True
    assert output["exception"] == "ValueError"
    assert output["error_location"] == "app.py"
    assert output["line_number"] == 14


def test_root_cause_agent():
    agent = RootCauseAgent()
    context = {
        "title": "Application failure",
        "triage": {"category": "Dependency Error"},
        "log_analysis": {"exception": "ModuleNotFoundError", "error_location": "app.py"},
        "duplicate_detection": {"similar_bugs": []}
    }
    ok, output, _ = agent.execute(context)
    assert ok is True
    assert "dependency" in output["root_cause"].lower()
    assert output["confidence"] in ("High", "Medium", "Low")


def test_remediation_agent():
    agent = RemediationAgent()
    context = {
        "triage": {"language": "Python", "keywords": ["flask"]},
        "root_cause": {"root_cause": "Missing dependency"},
        "duplicate_detection": {"similar_bugs": []}
    }
    ok, output, _ = agent.execute(context)
    assert ok is True
    assert "pip install" in " ".join(output["commands"])


def test_orchestrator_pipeline(app):
    with app.app_context():
        with get_db_session() as session:
            bug = BugReportRepository.create(
                session,
                title="NullPointerException in User.getName()",
                description="User object was null",
                stack_trace='Exception in thread "main" java.lang.NullPointerException\n\tat com.app.User.getName(User.java:25)',
                language="Java"
            )
            bug_id = bug.bug_id

        orchestrator = AgentOrchestrator()
        report = orchestrator.run_diagnosis(
            bug_id=bug_id,
            title="NullPointerException in User.getName()",
            stack_trace='Exception in thread "main" java.lang.NullPointerException\n\tat com.app.User.getName(User.java:25)',
            language="Java"
        )

        assert report["bug_id"] == bug_id
        assert report["language"] == "Java"
        assert report["root_cause"] is not None
        assert report["recommended_fix"] is not None
        assert "evidence" in report
