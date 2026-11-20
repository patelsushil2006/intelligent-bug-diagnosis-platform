import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient
from agents.schemas import TriageResult
from backend.bug_processor import BugProcessor


class TriageAgent(BaseAgent):
    """Classifies bug category, estimates severity & priority, isolates component, and scores confidence."""

    CATEGORIES = [
        "Syntax Error",
        "Runtime Error",
        "Dependency Error",
        "Database Error",
        "Memory Error",
        "Performance Issue",
        "Configuration Error",
        "Logic Error",
        "Network Error",
        "Documentation / Cosmetic"
    ]

    HIGH_IMPACT_KEYWORDS = {"crash", "data loss", "security", "production", "outage"}
    LOW_SEVERITY_KEYWORDS = {"cosmetic", "typo", "docs", "documentation", "lint", "comment"}

    def __init__(self, llm_client: LLMClient = None):
        super().__init__(name="TriageAgent")
        self.llm_client = llm_client or LLMClient()

    @staticmethod
    def _compute_priority(severity: str, keywords: List[str]) -> str:
        """Map severity to priority and upgrade one level if high-impact terms are present."""
        mapping = {
            "Critical": "P1",
            "High": "P2",
            "Medium": "P3",
            "Low": "P4"
        }
        base_p = mapping.get(severity, "P3")
        upgrades = {"P4": "P3", "P3": "P2", "P2": "P1", "P1": "P1"}

        lower_kws = {k.lower() for k in keywords}
        has_high_impact = any(
            any(hik in kw for hik in TriageAgent.HIGH_IMPACT_KEYWORDS)
            for kw in lower_kws
        )
        if has_high_impact:
            return upgrades[base_p]
        return base_p

    @staticmethod
    def _extract_component(text: str, stack: str, keywords: Optional[List[str]] = None) -> str:
        """Extract top-level package or module from stack trace frames or fallback to keywords."""
        combined = f"{text}\n{stack}".strip()

        # 1. Dotted expressions in text or stack like "auth.token.validate" -> "auth"
        dotted_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)(?:\.[a-zA-Z_][a-zA-Z0-9_]+)+', combined)
        for m in dotted_matches:
            if m.lower() not in ("org", "com", "net", "java", "javax", "node", "src", "main"):
                return m.lower()
            parts = re.search(rf'\b{m}\.([a-zA-Z0-9_]+)', combined)
            if parts and parts.group(1).lower() not in ("example", "app"):
                return parts.group(1).lower()

        # 2. File path frames like File "auth/login.py" or at .../service/UserService.java
        file_matches = re.findall(r'(?:File "|\bat )([^":\(\s]+)', stack)
        for fm in file_matches:
            parts = [p for p in fm.replace("\\", "/").split("/") if p and p not in (".", "..", "src", "app")]
            if parts:
                stem = parts[0].replace(".py", "").replace(".java", "").replace(".js", "").replace(".ts", "")
                if stem:
                    return stem.lower()

        # 3. Fallback to first non-generic keyword
        if keywords:
            for kw in keywords:
                if len(kw) > 2 and kw.lower() not in ("error", "exception", "failed", "failure", "null", "none"):
                    return kw.lower()

        # 4. Fallback to token scan
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}', text)
        for t in tokens:
            if t.lower() not in ("error", "exception", "nullpointerexception", "in", "the", "when", "with", "null"):
                return t.lower()

        return "core"

    @staticmethod
    def _compute_confidence(llm_agreed: bool = False, has_rule_match: bool = True, has_strong_keywords: bool = True) -> float:
        """Compute confidence score: 0.9 if LLM and rules agree, 0.6 if rules, 0.4 if weak keywords."""
        if llm_agreed:
            return 0.9
        if has_rule_match and has_strong_keywords:
            return 0.6
        return 0.4

    @staticmethod
    def _reasoning(severity: str, priority: str, category: str, keywords: List[str], component: str, stack_frame_count: int = 0) -> str:
        """Generate a one-sentence reasoning explanation for triage decision."""
        kw_sample = keywords[0] if keywords else category
        if stack_frame_count > 0:
            return f"Severity set to {severity} ({priority}) due to exception keywords '{kw_sample}' and {stack_frame_count} stack frames in {component} module."
        return f"Severity set to {severity} ({priority}) based on {category} pattern and keywords '{kw_sample}' in {component} module."

    def process(
        self,
        context_or_title: Union[Dict[str, Any], str],
        description: str = "",
        stack_trace: str = "",
        log_content: str = "",
        user_language: Optional[str] = None
    ) -> Dict[str, Any]:
        if isinstance(context_or_title, dict):
            context = context_or_title
            title = context.get("title", "")
            description = context.get("description", "")
            stack_trace = context.get("stack_trace", "")
            log_content = context.get("log_content", "")
            user_language = context.get("language")
        else:
            title = str(context_or_title or "")

        combined_text = f"{title}\n{description}\n{stack_trace}\n{log_content}".lower()

        # Extract tokens/keywords first
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', f"{title} {stack_trace}")
        keywords = list(dict.fromkeys([
            t for t in tokens if t.lower() not in (
                "error", "file", "line", "most", "recent", "call", "last", "traceback", "that", "this", "from", "with"
            )
        ]))[:5]

        component = self._extract_component(f"{title} {description}", stack_trace, keywords)
        language = BugProcessor.detect_language(f"{stack_trace}\n{description}", hint=user_language)

        # 1. Try LLM if configured
        if self.llm_client.is_llm_enabled():
            prompt = (
                f"Classify this bug report into category (one of {self.CATEGORIES}), "
                f"severity (Critical, High, Medium, Low), priority (P1, P2, P3, P4), "
                f"affected_component (single word or module), confidence_score (0.0 to 1.0), "
                f"reasoning (single sentence explanation), language, and keywords (3-5 strings).\n\n"
                f"Title: {title}\nDescription: {description}\nStack: {stack_trace}\nLogs: {log_content}\n\n"
                f"Return JSON format: {{\"category\": \"...\", \"severity\": \"...\", \"priority\": \"...\", \"affected_component\": \"...\", \"confidence_score\": 0.9, \"reasoning\": \"...\", \"language\": \"...\", \"keywords\": [...]}}"
            )
            llm_result, mode = self.llm_client.query_json(prompt)
            if llm_result and "category" in llm_result and "severity" in llm_result:
                try:
                    result = TriageResult(
                        category=llm_result.get("category", "Runtime Error"),
                        severity=llm_result.get("severity", "Medium"),
                        priority=llm_result.get("priority") or self._compute_priority(llm_result.get("severity", "Medium"), keywords),
                        affected_component=llm_result.get("affected_component") or component,
                        confidence_score=float(llm_result.get("confidence_score", 0.9)),
                        reasoning=llm_result.get("reasoning") or self._reasoning(llm_result.get("severity", "Medium"), "P2", llm_result.get("category", "Runtime Error"), keywords, component),
                        language=llm_result.get("language") or language,
                        keywords=llm_result.get("keywords") or keywords,
                        analysis_mode=mode
                    )
                    return result.model_dump()
                except Exception:
                    pass

        # 2. Robust Deterministic / Rule-Based Triage
        category = "Runtime Error"
        severity = "Medium"
        has_rule_match = True

        # Explicit Low branch
        if any(w in combined_text for w in self.LOW_SEVERITY_KEYWORDS):
            category = "Documentation / Cosmetic"
            severity = "Low"
        elif any(w in combined_text for w in ["modulenotfounderror", "importerror", "no module named", "cannot find module", "classnotfoundexception"]):
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
        else:
            has_rule_match = False

        priority = self._compute_priority(severity, keywords)
        confidence = self._compute_confidence(
            llm_agreed=False,
            has_rule_match=has_rule_match,
            has_strong_keywords=len(keywords) > 0
        )

        stack_frames = BugProcessor.parse_stack_trace(stack_trace).get("frames", [])
        reasoning = self._reasoning(
            severity=severity,
            priority=priority,
            category=category,
            keywords=keywords,
            component=component,
            stack_frame_count=len(stack_frames)
        )

        result = TriageResult(
            category=category,
            severity=severity,
            priority=priority,
            affected_component=component,
            confidence_score=confidence,
            reasoning=reasoning,
            language=language,
            keywords=keywords,
            analysis_mode="rule-based-fallback"
        )
        return result.model_dump()
