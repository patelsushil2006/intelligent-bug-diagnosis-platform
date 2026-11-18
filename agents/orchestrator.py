import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from database.db import get_db_session
from database.repositories import (
    AnalysisRunRepository,
    AgentResultRepository,
    RetrievedDefectRepository
)
from agents.triage_agent import TriageAgent
from agents.log_analysis_agent import LogAnalysisAgent
from agents.duplicate_detection_agent import DuplicateDetectionAgent
from agents.root_cause_agent import RootCauseAgent
from agents.remediation_agent import RemediationAgent
from agents.llm_client import LLMClient

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates the hybrid sequential/parallel multi-agent bug diagnosis pipeline."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
        self.triage_agent = TriageAgent(self.llm_client)
        self.log_analysis_agent = LogAnalysisAgent(self.llm_client)
        self.duplicate_agent = DuplicateDetectionAgent()
        self.root_cause_agent = RootCauseAgent(self.llm_client)
        self.remediation_agent = RemediationAgent(self.llm_client)

    def run_diagnosis(
        self,
        bug_id: str,
        title: str,
        description: Optional[str] = None,
        stack_trace: Optional[str] = None,
        log_content: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute the multi-agent diagnostic pipeline for a submitted bug report."""
        logger.info(f"Initiating diagnosis run for Bug ID: {bug_id}")

        # 1. Initialize Analysis Run in Database
        with get_db_session() as session:
            analysis_run = AnalysisRunRepository.create(session, bug_id=bug_id)
            analysis_id = analysis_run.analysis_id
            AnalysisRunRepository.update_status(session, analysis_id, "PROCESSING")

        base_context = {
            "bug_id": bug_id,
            "analysis_id": analysis_id,
            "title": title,
            "description": description or "",
            "stack_trace": stack_trace or "",
            "log_content": log_content or "",
            "language": language
        }

        try:
            # Step 1: Sequential Triage Agent
            ok_triage, triage_output, err = self.triage_agent.execute(base_context)
            if not ok_triage:
                triage_output = {"category": "Runtime Error", "severity": "Medium", "language": "Unknown", "keywords": []}

            # Update context with triage results
            base_context["triage"] = triage_output
            if not base_context["language"] or base_context["language"] == "Unknown":
                base_context["language"] = triage_output.get("language")

            # Step 2: Parallel Analysis (Log Analysis Agent & Duplicate Detection Agent)
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_logs = executor.submit(self.log_analysis_agent.execute, base_context)
                future_duplicates = executor.submit(self.duplicate_agent.execute, base_context)

                ok_log, log_output, _ = future_logs.result()
                ok_dup, dup_output, _ = future_duplicates.result()

            base_context["log_analysis"] = log_output if ok_log else {}
            base_context["duplicate_detection"] = dup_output if ok_dup else {"similar_bugs": []}

            # Step 3: Sequential Root Cause Agent
            ok_rc, rc_output, _ = self.root_cause_agent.execute(base_context)
            base_context["root_cause"] = rc_output if ok_rc else {
                "root_cause": "Unidentified software failure",
                "explanation": "Could not determine precise root cause from inputs.",
                "evidence": [],
                "confidence": "Low"
            }

            # Step 4: Sequential Remediation Agent
            ok_fix, fix_output, _ = self.remediation_agent.execute(base_context)
            base_context["remediation"] = fix_output if ok_fix else {
                "recommended_fix": "Inspect the failure line in your debugger.",
                "commands": [],
                "explanation": "No specific automated remediation available.",
                "verification": "Run regression tests."
            }

            # 5. Persist all agent outputs into Database
            with get_db_session() as session:
                AgentResultRepository.save_result(session, analysis_id, "triage", triage_output)
                AgentResultRepository.save_result(session, analysis_id, "log_analysis", base_context["log_analysis"])
                AgentResultRepository.save_result(session, analysis_id, "duplicate_detection", base_context["duplicate_detection"])
                AgentResultRepository.save_result(session, analysis_id, "root_cause", base_context["root_cause"])
                AgentResultRepository.save_result(session, analysis_id, "remediation", base_context["remediation"])

                # Persist RAG references
                similar_bugs = base_context["duplicate_detection"].get("similar_bugs", [])
                if similar_bugs:
                    RetrievedDefectRepository.save_retrievals(session, analysis_id, similar_bugs)

                # Mark run as COMPLETED
                AnalysisRunRepository.update_status(session, analysis_id, "COMPLETED")

            # 6. Assemble Final Diagnosis Report
            diagnosis_report = {
                "bug_id": bug_id,
                "analysis_id": analysis_id,
                "title": title,
                "description": description,
                "language": base_context["language"],
                "category": triage_output.get("category", "Runtime Error"),
                "severity": triage_output.get("severity", "Medium"),
                "keywords": triage_output.get("keywords", []),
                "extracted_exception": base_context["log_analysis"].get("exception"),
                "error_location": base_context["log_analysis"].get("error_location"),
                "line_number": base_context["log_analysis"].get("line_number"),
                "root_cause": base_context["root_cause"].get("root_cause"),
                "explanation": base_context["root_cause"].get("explanation"),
                "evidence": base_context["root_cause"].get("evidence", []),
                "confidence": base_context["root_cause"].get("confidence", "Medium"),
                "similar_historical_bugs": similar_bugs,
                "recommended_fix": base_context["remediation"].get("recommended_fix"),
                "execution_commands": base_context["remediation"].get("commands", []),
                "verification_steps": base_context["remediation"].get("verification"),
                "risks": base_context["remediation"].get("risks"),
                "analysis_mode": base_context["root_cause"].get("analysis_mode", "rule-based-fallback"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return diagnosis_report

        except Exception as e:
            logger.error(f"Critical error during diagnosis run for {bug_id}: {e}", exc_info=True)
            with get_db_session() as session:
                AnalysisRunRepository.update_status(session, analysis_id, "FAILED", error_message=str(e))
            raise
