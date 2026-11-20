from flask import Blueprint, render_template, redirect, url_for
from database.db import get_db_session
from database.repositories import (
    BugReportRepository,
    AnalysisRunRepository,
    HistoricalDefectRepository
)
from knowledge_base.vector_store import ChromaVectorStore
from knowledge_base.ingestion import DefectIngestionPipeline

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    """Platform overview dashboard."""
    with get_db_session() as session:
        total_bugs = BugReportRepository.count(session)
        total_runs = AnalysisRunRepository.count(session)
        total_historical = HistoricalDefectRepository.count(session)
        recent_bugs = [b.to_dict() for b in BugReportRepository.list_all(session, limit=5)]

    vs = ChromaVectorStore()
    vector_chunks = vs.count()

    return render_template(
        "index.html",
        total_bugs=total_bugs,
        total_runs=total_runs,
        total_historical=total_historical,
        vector_chunks=vector_chunks,
        recent_bugs=recent_bugs
    )


@web_bp.route("/submit")
def submit():
    """Bug submission page."""
    return render_template("submit.html")


@web_bp.route("/history")
def history():
    """Bug submission history with status and actions."""
    with get_db_session() as session:
        raw_bugs = BugReportRepository.list_all(session, limit=100)
        bugs = [b.to_dict() for b in raw_bugs]
        runs_map = {}
        for b in raw_bugs:
            run = AnalysisRunRepository.get_latest_for_bug(session, b.bug_id)
            runs_map[b.bug_id] = run.status if run else "UNANALYZED"

    return render_template("history.html", bugs=bugs, runs_map=runs_map)


@web_bp.route("/results/<bug_id>")
def results(bug_id: str):
    """Detailed diagnosis report and agent findings."""
    with get_db_session() as session:
        bug = BugReportRepository.get_by_id(session, bug_id)
        if not bug:
            return redirect(url_for("web.history"))
        bug_dict = bug.to_dict()

    return render_template(
        "results.html",
        bug=bug_dict
    )


@web_bp.route("/knowledge-base")
def knowledge_base():
    """Knowledge base explorer for Mozilla, Apache, Eclipse defect archives."""
    with get_db_session() as session:
        defects = [d.to_dict() for d in HistoricalDefectRepository.list_all(session, limit=50)]
        total_count = HistoricalDefectRepository.count(session)

    vs = ChromaVectorStore()
    vector_count = vs.count()

    return render_template(
        "knowledge_base.html",
        defects=defects,
        total_count=total_count,
        vector_count=vector_count
    )


@web_bp.route("/knowledge-base/seed", methods=["POST"])
def seed_knowledge_base():
    """One-click trigger to seed historical defects from Mozilla, Apache, and Eclipse."""
    pipeline = DefectIngestionPipeline()
    pipeline.seed_initial_knowledge_base()
    return redirect(url_for("web.knowledge_base"))
