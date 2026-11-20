import json
from flask import Blueprint, request, jsonify
from database.db import get_db_session
from database.repositories import (
    BugReportRepository,
    AnalysisRunRepository,
    AgentResultRepository,
    RetrievedDefectRepository,
    UserFeedbackRepository,
    HistoricalDefectRepository
)
from backend.bug_processor import BugProcessor
from agents.orchestrator import AgentOrchestrator

bug_bp = Blueprint("bugs", __name__, url_prefix="/api")
orchestrator = AgentOrchestrator()


@bug_bp.route("/bugs", methods=["POST"])
def submit_bug():
    """Create a new bug report via JSON payload."""
    data = request.get_json(silent=True) or {}
    is_valid, error = BugProcessor.validate_submission(data)
    if not is_valid:
        return jsonify({"error": error}), 400

    title = BugProcessor.normalize_text(data.get("title", ""))
    desc = BugProcessor.normalize_text(data.get("description", ""))
    stack = BugProcessor.normalize_text(data.get("stack_trace", ""))
    logs = BugProcessor.normalize_text(data.get("log_content", ""))
    lang = BugProcessor.detect_language(f"{stack}\n{desc}", data.get("language"))
    severity = data.get("severity", "Medium")

    with get_db_session() as session:
        bug = BugReportRepository.create(
            session=session,
            title=title,
            description=desc,
            stack_trace=stack,
            log_content=logs,
            language=lang,
            severity=severity
        )
        bug_dict = bug.to_dict()

    # Synchronously execute multi-agent diagnostic run
    try:
        report = orchestrator.run_diagnosis(
            bug_id=bug_dict["bug_id"],
            title=title,
            description=desc,
            stack_trace=stack,
            log_content=logs,
            language=lang
        )
    except Exception as e:
        report = {"error": f"Diagnosis execution failed: {str(e)}"}

    return jsonify({
        "message": "Bug report submitted successfully.",
        "bug": bug_dict,
        "analysis": report
    }), 201


@bug_bp.route("/bugs/upload", methods=["POST"])
def upload_bug_file():
    """Accept and parse an uploaded bug report, error log, or stack trace file."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    file_obj = request.files["file"]
    ok, msg, file_data = BugProcessor.handle_file_upload(file_obj)
    if not ok:
        return jsonify({"error": msg}), 400

    content = file_data["content"]
    title = request.form.get("title") or f"Uploaded Issue from {file_data['filename']}"
    user_desc = request.form.get("description") or f"Auto-extracted from {file_data['filename']}"

    parsed_trace = BugProcessor.parse_stack_trace(content)
    parsed_logs = BugProcessor.parse_error_log(content)

    stack_trace = content if parsed_trace["has_trace"] else ""
    log_content = content if parsed_logs["has_logs"] and not stack_trace else ""
    if not stack_trace and not log_content:
        user_desc += f"\n\nFile Content Preview:\n{content[:500]}"

    lang = BugProcessor.detect_language(content, request.form.get("language"))

    with get_db_session() as session:
        bug = BugReportRepository.create(
            session=session,
            title=BugProcessor.normalize_text(title),
            description=BugProcessor.normalize_text(user_desc),
            stack_trace=BugProcessor.normalize_text(stack_trace),
            log_content=BugProcessor.normalize_text(log_content),
            language=lang,
            severity=request.form.get("severity", "Medium")
        )
        bug_dict = bug.to_dict()

    return jsonify({
        "message": "File uploaded and parsed into bug report successfully.",
        "bug": bug_dict
    }), 201


@bug_bp.route("/bugs", methods=["GET"])
def list_bugs():
    """List recent submitted bug reports."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    with get_db_session() as session:
        bugs = BugReportRepository.list_all(session, limit=limit, offset=offset)
        total = BugReportRepository.count(session)
        bugs_list = [b.to_dict() for b in bugs]

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "bugs": bugs_list
    }), 200


@bug_bp.route("/bugs/<bug_id>", methods=["GET"])
def get_bug(bug_id: str):
    """Retrieve details of a specific bug report."""
    with get_db_session() as session:
        bug = BugReportRepository.get_by_id(session, bug_id)
        if not bug:
            return jsonify({"error": "Bug report not found."}), 404
        return jsonify(bug.to_dict()), 200


@bug_bp.route("/bugs/<bug_id>/analyze", methods=["POST"])
def analyze_bug(bug_id: str):
    """Trigger multi-agent diagnostic run for a bug report."""
    with get_db_session() as session:
        bug = BugReportRepository.get_by_id(session, bug_id)
        if not bug:
            return jsonify({"error": "Bug report not found."}), 404

        bug_title = bug.title
        bug_desc = bug.description
        bug_stack = bug.stack_trace
        bug_logs = bug.log_content
        bug_lang = bug.language

    try:
        report = orchestrator.run_diagnosis(
            bug_id=bug_id,
            title=bug_title,
            description=bug_desc,
            stack_trace=bug_stack,
            log_content=bug_logs,
            language=bug_lang
        )
        return jsonify({
            "message": "Diagnosis completed successfully.",
            "report": report
        }), 200
    except Exception as e:
        return jsonify({"error": f"Diagnosis execution failed: {str(e)}"}), 500


@bug_bp.route("/bugs/<bug_id>/results", methods=["GET"])
def get_bug_results(bug_id: str):
    """Retrieve the latest diagnosis report and agent findings for a bug."""
    with get_db_session() as session:
        bug = BugReportRepository.get_by_id(session, bug_id)
        if not bug:
            return jsonify({"error": "Bug report not found."}), 404

        latest_run = AnalysisRunRepository.get_latest_for_bug(session, bug_id)
        if not latest_run:
            return jsonify({
                "bug_id": bug_id,
                "status": "NOT_ANALYZED",
                "message": "This bug has not been analyzed yet. Run POST /api/bugs/<bug_id>/analyze."
            }), 200

        results = AgentResultRepository.get_results_by_analysis_id(session, latest_run.analysis_id)
        retrieved_defects = RetrievedDefectRepository.get_by_analysis_id(session, latest_run.analysis_id)

        # Look up historical defects from database
        defect_details = []
        for rd in retrieved_defects:
            hd = HistoricalDefectRepository.get_by_id(session, rd.defect_id)
            defect_details.append({
                "defect_id": rd.defect_id,
                "similarity_score": rd.similarity_score,
                "title": hd.title if hd else "Historical defect",
                "source": hd.source if hd else "Archive",
                "resolution": hd.resolution if hd else ""
            })

        agent_data = {}
        for r in results:
            agent_data[r.agent_name] = json.loads(r.output_json) if r.output_json else {}

        triage = agent_data.get("triage", {})
        log_a = agent_data.get("log_analysis", {})
        root_c = agent_data.get("root_cause", {})
        remed = agent_data.get("remediation", {})

        report = {
            "bug_id": bug_id,
            "analysis_id": latest_run.analysis_id,
            "status": latest_run.status,
            "title": bug.title,
            "description": bug.description,
            "language": bug.language,
            "category": triage.get("category", "Runtime Error"),
            "severity": triage.get("severity", "Medium"),
            "keywords": triage.get("keywords", []),
            "extracted_exception": log_a.get("exception"),
            "error_location": log_a.get("error_location"),
            "line_number": log_a.get("line_number"),
            "root_cause": root_c.get("root_cause"),
            "explanation": root_c.get("explanation"),
            "evidence": root_c.get("evidence", []),
            "confidence": root_c.get("confidence", "Medium"),
            "similar_historical_bugs": defect_details,
            "recommended_fix": remed.get("recommended_fix"),
            "execution_commands": remed.get("commands", []),
            "verification_steps": remed.get("verification"),
            "risks": remed.get("risks"),
            "analysis_mode": root_c.get("analysis_mode", "rule-based-fallback"),
            "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
            "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
            "raw_agent_results": agent_data
        }

        return jsonify(report), 200


@bug_bp.route("/bugs/<bug_id>/feedback", methods=["POST"])
def submit_feedback(bug_id: str):
    """Submit user rating and feedback on a diagnosis."""
    data = request.get_json(silent=True) or {}
    with get_db_session() as session:
        latest_run = AnalysisRunRepository.get_latest_for_bug(session, bug_id)
        if not latest_run:
            return jsonify({"error": "No analysis run exists to submit feedback for."}), 400

        fb = UserFeedbackRepository.add_feedback(
            session=session,
            analysis_id=latest_run.analysis_id,
            feedback=data.get("feedback", ""),
            is_accurate=bool(data.get("is_accurate", True)),
            rating=float(data.get("rating", 5.0))
        )
        fb_dict = fb.to_dict()

    return jsonify({
        "message": "Feedback recorded successfully. Thank you for helping improve the knowledge base.",
        "feedback": fb_dict
    }), 201
