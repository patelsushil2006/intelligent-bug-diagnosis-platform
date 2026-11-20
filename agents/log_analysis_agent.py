from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient
from agents.schemas import LogAnalysisResult
from backend.bug_processor import BugProcessor


class LogAnalysisAgent(BaseAgent):
    """Analyzes stack traces and execution logs to pinpoint error locations and patterns."""

    def __init__(self, llm_client: LLMClient = None):
        super().__init__(name="LogAnalysisAgent")
        self.llm_client = llm_client or LLMClient()

    @staticmethod
    def _extract_code_path(frames: List[Dict[str, Any]]) -> List[str]:
        """Return list of 'module.func' or 'file:line' strings in call order from outermost to innermost."""
        path = []
        for f in frames:
            func = f.get("function")
            file_path = f.get("file", "")
            line = f.get("line")
            if func and "." in func:
                path.append(func)
            elif file_path and func and func != "anonymous":
                mod = Path(file_path).stem
                path.append(f"{mod}.{func}")
            elif file_path and line:
                path.append(f"{file_path}:{line}")
            elif file_path:
                path.append(file_path)
        return path

    @staticmethod
    def _compute_confidence(frames: List[Dict[str, Any]], exception: str) -> float:
        """0.95 if >=3 clean frames; 0.7 if 1-2 frames; 0.4 if only regex on raw text."""
        if len(frames) >= 3:
            return 0.95
        if len(frames) >= 1:
            return 0.7
        return 0.4

    def process(
        self,
        context_or_trace: Union[Dict[str, Any], str] = "",
        log_content: str = ""
    ) -> Dict[str, Any]:
        if isinstance(context_or_trace, dict):
            context = context_or_trace
            stack_trace = context.get("stack_trace", "")
            log_content = context.get("log_content", "")
        else:
            stack_trace = str(context_or_trace or "")

        # 1. Deterministic stack parsing
        parsed_trace = BugProcessor.parse_stack_trace(stack_trace)
        parsed_logs = BugProcessor.parse_error_log(log_content)

        exception_type = parsed_trace.get("exception_type", "UnknownException")
        location = parsed_trace.get("primary_location") or "Unknown"
        line_num = parsed_trace.get("primary_line")
        frames = parsed_trace.get("frames", [])
        frames_count = len(frames)

        # Extract ordered code path
        code_path = self._extract_code_path(frames)
        confidence = self._compute_confidence(frames, exception_type)

        # Determine failure point string
        if location != "Unknown" and line_num:
            failure_point = f"{location}:{line_num}"
        elif location != "Unknown":
            failure_point = location
        elif frames:
            target = frames[-1]
            failure_point = f"{target.get('file', 'unknown')}:{target.get('line', 0)}"
        else:
            failure_point = "unknown:0"

        # Check if LLM can enrich summary
        if self.llm_client.is_llm_enabled() and (stack_trace or log_content):
            prompt = (
                f"Analyze this stack trace and log to summarize the failure.\n\n"
                f"Stack: {stack_trace}\nLogs: {log_content}\n\n"
                f"Return JSON format: {{\"exception_type\": \"...\", \"error_message\": \"...\", \"failure_point\": \"...\", \"summary\": \"...\"}}"
            )
            llm_result, mode = self.llm_client.query_json(prompt)
            if llm_result and "summary" in llm_result:
                try:
                    result = LogAnalysisResult(
                        exception_type=llm_result.get("exception_type") or exception_type,
                        error_message=llm_result.get("error_message") or parsed_trace.get("exception_message", ""),
                        failure_point=llm_result.get("failure_point") or failure_point,
                        code_path=code_path,
                        confidence_score=confidence,
                        summary=llm_result.get("summary"),
                        exception=llm_result.get("exception_type") or exception_type,
                        error_location=location,
                        line_number=line_num,
                        call_depth=frames_count,
                        critical_log_entries=parsed_logs.get("critical_entries", []),
                        analysis_mode=mode
                    )
                    return result.model_dump()
                except Exception:
                    pass

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

        error_msg = parsed_trace.get("exception_message") or (
            parsed_logs.get("critical_entries", [""])[0] if parsed_logs.get("critical_entries") else ""
        )

        result = LogAnalysisResult(
            exception_type=exception_type,
            error_message=error_msg,
            failure_point=failure_point,
            code_path=code_path,
            confidence_score=confidence,
            summary=summary,
            exception=exception_type,
            error_location=location,
            line_number=line_num,
            error_summary=summary,
            call_depth=frames_count,
            critical_log_entries=parsed_logs.get("critical_entries", []),
            analysis_mode="rule-based-fallback"
        )
        return result.model_dump()
