from typing import Dict, Any
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient
from backend.bug_processor import BugProcessor


class LogAnalysisAgent(BaseAgent):
    """Analyzes stack traces and execution logs to pinpoint error locations and patterns."""

    def __init__(self, llm_client: LLMClient = None):
        super().__init__(name="LogAnalysisAgent")
        self.llm_client = llm_client or LLMClient()

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        stack_trace = context.get("stack_trace", "")
        log_content = context.get("log_content", "")

        # 1. Deterministic stack parsing
        parsed_trace = BugProcessor.parse_stack_trace(stack_trace)
        parsed_logs = BugProcessor.parse_error_log(log_content)

        exception_type = parsed_trace.get("exception_type", "UnknownException")
        location = parsed_trace.get("primary_location") or "Unknown"
        line_num = parsed_trace.get("primary_line")
        frames_count = len(parsed_trace.get("frames", []))

        # Check if LLM can enrich summary
        if self.llm_client.is_llm_enabled() and (stack_trace or log_content):
            prompt = (
                f"Analyze this stack trace and log to summarize the failure.\n\n"
                f"Stack: {stack_trace}\nLogs: {log_content}\n\n"
                f"Return JSON format: {{\"exception\": \"...\", \"error_location\": \"...\", \"line_number\": 0, \"error_summary\": \"...\"}}"
            )
            llm_result, mode = self.llm_client.query_json(prompt)
            if llm_result and "error_summary" in llm_result:
                llm_result["analysis_mode"] = mode
                llm_result["call_depth"] = frames_count
                return llm_result

        # Deterministic summary generation
        summary = f"Exception '{exception_type}' raised"
        if location != "Unknown":
            summary += f" in file {location}"
            if line_num:
                summary += f" at line {line_num}"

        if parsed_trace.get("exception_message"):
            summary += f": {parsed_trace['exception_message']}"
        elif parsed_logs.get("critical_entries"):
            summary += f". Critical log: {parsed_logs['critical_entries'][0]}"

        return {
            "exception": exception_type,
            "error_location": location,
            "line_number": line_num,
            "error_summary": summary,
            "call_depth": frames_count,
            "critical_log_entries": parsed_logs.get("critical_entries", []),
            "analysis_mode": "rule-based-fallback"
        }
