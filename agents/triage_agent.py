import re
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient
from backend.bug_processor import BugProcessor


class TriageAgent(BaseAgent):
    """Classifies bug category, estimates severity, identifies programming language, and extracts keywords."""

    CATEGORIES = [
        "Syntax Error",
        "Runtime Error",
        "Dependency Error",
        "Database Error",
        "Memory Error",
        "Performance Issue",
        "Configuration Error",
        "Logic Error",
        "Network Error"
    ]

    def __init__(self, llm_client: LLMClient = None):
        super().__init__(name="TriageAgent")
        self.llm_client = llm_client or LLMClient()

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        title = context.get("title", "")
        description = context.get("description", "")
        stack_trace = context.get("stack_trace", "")
        log_content = context.get("log_content", "")
        user_language = context.get("language")

        combined_text = f"{title}\n{description}\n{stack_trace}\n{log_content}".lower()

        # Try LLM if configured
        if self.llm_client.is_llm_enabled():
            prompt = (
                f"Classify this bug report into one of {self.CATEGORIES}, "
                f"determine severity (Critical, High, Medium, Low), detect language, "
                f"and extract 3-5 keywords.\n\n"
                f"Title: {title}\nDescription: {description}\nStack: {stack_trace}\nLogs: {log_content}\n\n"
                f"Return JSON format: {{\"category\": \"...\", \"severity\": \"...\", \"language\": \"...\", \"keywords\": [...]}}"
            )
            llm_result, mode = self.llm_client.query_json(prompt)
            if llm_result and "category" in llm_result:
                llm_result["analysis_mode"] = mode
                return llm_result

        # Robust Deterministic / Rule-Based Triage
        category = "Runtime Error"
        severity = "Medium"

        if any(w in combined_text for w in ["modulenotfounderror", "importerror", "no module named", "cannot find module", "classnotfoundexception"]):
            category = "Dependency Error"
            severity = "High"
        elif any(w in combined_text for w in ["syntaxerror", "unexpected token", "expected ';'", "parse error", "invalid syntax"]):
            category = "Syntax Error"
            severity = "High"
        elif any(w in combined_text for w in ["sqlite", "database", "sql", "table", "foreign key", "connection refused", "deadlock"]):
            category = "Database Error"
            severity = "High"
        elif any(w in combined_text for w in ["out of memory", "outofmemoryerror", "segmentation fault", "sigsegv", "memory leak", "heap dump"]):
            category = "Memory Error"
            severity = "Critical"
        elif any(w in combined_text for w in ["timeout", "slow", "latency", "recursionerror", "infinite loop"]):
            category = "Performance Issue"
            severity = "Medium"
        elif any(w in combined_text for w in ["connection refused", "econnrefused", "httperror", "socket", "network"]):
            category = "Network Error"
            severity = "High"
        elif any(w in combined_text for w in ["filenotfounderror", "permissionerror", "eacces", "configuration", "config"]):
            category = "Configuration Error"
            severity = "Medium"

        language = BugProcessor.detect_language(
            f"{stack_trace}\n{description}", hint=user_language
        )

        # Keyword extraction
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', f"{title} {stack_trace}")
        keywords = list(dict.fromkeys([
            t for t in tokens if t.lower() not in (
                "error", "file", "line", "line", "most", "recent", "call", "last", "traceback", "that", "this", "from", "with"
            )
        ]))[:5]

        return {
            "category": category,
            "severity": severity,
            "language": language,
            "keywords": keywords,
            "analysis_mode": "rule-based-fallback"
        }
