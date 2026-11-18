from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient


class RootCauseAgent(BaseAgent):
    """Synthesizes triage, log parsing, and historical RAG evidence into an evidence-based root cause."""

    def __init__(self, llm_client: LLMClient = None):
        super().__init__(name="RootCauseAgent")
        self.llm_client = llm_client or LLMClient()

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        triage = context.get("triage", {})
        log_findings = context.get("log_analysis", {})
        historical_findings = context.get("duplicate_detection", {})

        title = context.get("title", "")
        description = context.get("description", "")
        category = triage.get("category", "Runtime Error")
        exception = log_findings.get("exception", "Unknown")
        location = log_findings.get("error_location", "Unknown")
        similar_bugs = historical_findings.get("similar_bugs", [])

        # Format historical context for LLM if available
        historical_summary = "\n".join([
            f"- {b['defect_id']} ({b['source']}): {b['title']} -> Fix: {b['resolution'][:150]}"
            for b in similar_bugs[:3]
        ])

        if self.llm_client.is_llm_enabled():
            prompt = (
                f"You are a Senior Root Cause Analysis Engineer. Synthesize the following findings into a clear root cause, "
                f"reasoned explanation, bulleted evidence list, and confidence (High, Medium, Low).\n\n"
                f"Bug Title: {title}\nDescription: {description}\nCategory: {category}\n"
                f"Exception: {exception} at {location}\n"
                f"Historical RAG Evidence:\n{historical_summary}\n\n"
                f"Return JSON: {{\"root_cause\": \"...\", \"explanation\": \"...\", \"evidence\": [...], \"confidence\": \"...\"}}"
            )
            llm_result, mode = self.llm_client.query_json(prompt)
            if llm_result and "root_cause" in llm_result:
                llm_result["analysis_mode"] = mode
                return llm_result

        # Deterministic evidence-based synthesis
        evidence: List[str] = []
        confidence = "Medium"

        if exception != "Unknown":
            evidence.append(f"Identified exception '{exception}' during execution.")
            confidence = "High"

        if location != "Unknown":
            line = log_findings.get("line_number")
            loc_str = f"Execution halted in '{location}'"
            if line:
                loc_str += f" at line {line}"
            evidence.append(loc_str)

        if similar_bugs:
            top_bug = similar_bugs[0]
            evidence.append(
                f"Historical similarity ({int(top_bug['similarity_score'] * 100)}%) with {top_bug['defect_id']} ({top_bug['source']}): {top_bug['title']}"
            )
            confidence = "High"

        root_cause = f"{category} triggered by {exception}"
        explanation = (
            f"The software failed with category '{category}'. "
            f"Analysis of the stack trace pinpoints execution failure at '{location}'. "
        )

        if "modulenotfound" in exception.lower() or "import" in category.lower():
            root_cause = "Missing or uninstalled dependency"
            explanation = "The interpreter or runtime cannot locate the specified package or module in the current environment path."
        elif "nullpointer" in exception.lower() or "typeerror" in exception.lower():
            root_cause = "Null / undefined dereference"
            explanation = "An expression attempted to read an attribute or invoke a method on a null, None, or undefined variable."
        elif "syntax" in category.lower():
            root_cause = "Invalid syntax or unclosed delimiters"
            explanation = "The code parser encountered unexpected tokens or missing closing brackets/parentheses."
        elif "memory" in category.lower() or "recursion" in exception.lower():
            root_cause = "Resource exhaustion or unbounded recursion"
            explanation = "Execution entered a recursive loop or exhausted heap memory limits."

        return {
            "root_cause": root_cause,
            "explanation": explanation,
            "evidence": evidence,
            "confidence": confidence,
            "analysis_mode": "rule-based-fallback"
        }
