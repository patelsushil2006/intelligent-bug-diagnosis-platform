from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient


class RemediationAgent(BaseAgent):
    """Produces actionable, evidence-based fix recommendations, terminal commands, and verification steps."""

    def __init__(self, llm_client: LLMClient = None):
        super().__init__(name="RemediationAgent")
        self.llm_client = llm_client or LLMClient()

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        root_cause_info = context.get("root_cause", {})
        historical_findings = context.get("duplicate_detection", {})
        triage = context.get("triage", {})
        language = triage.get("language", "General")

        root_cause = root_cause_info.get("root_cause", "General software defect")
        similar_bugs = historical_findings.get("similar_bugs", [])

        # Try LLM
        if self.llm_client.is_llm_enabled():
            prompt = (
                f"You are a Senior Remediation Engineer. Recommend an actionable fix for this software defect.\n\n"
                f"Root Cause: {root_cause}\n"
                f"Language: {language}\n"
                f"Historical Resolutions from Knowledge Base:\n" +
                "\n".join([f"- {b['defect_id']}: {b['resolution']}" for b in similar_bugs[:3]]) +
                "\n\nReturn JSON: {\"recommended_fix\": \"...\", \"commands\": [\"...\"], \"explanation\": \"...\", \"verification\": \"...\", \"risks\": \"...\"}"
            )
            llm_result, mode = self.llm_client.query_json(prompt)
            if llm_result and "recommended_fix" in llm_result:
                llm_result["analysis_mode"] = mode
                return llm_result

        # Deterministic evidence-based recommendations
        recommended_fix = "Review code at the reported error location and ensure variables are properly initialized."
        commands: List[str] = []
        explanation = "Applying appropriate boundary checks and type validation prevents the runtime failure."
        verification = "Re-run test suite or execute application with reproducing parameters."
        risks = "Verify that changing data representations does not break dependent consumers."

        root_lower = root_cause.lower()

        if "dependency" in root_lower or "modulenotfound" in root_lower:
            # Extract missing module from keywords or log
            keywords = triage.get("keywords", [])
            module_name = keywords[0] if keywords else "required_package"
            recommended_fix = f"Install missing dependency '{module_name}' into the active environment."
            commands = [f"python -m pip install {module_name}"]
            explanation = "Installs the missing library into the active Python environment so the import statement resolves."
            verification = f"python -m pip show {module_name}"
            risks = "Confirm that version constraints in requirements.txt or pyproject.toml are satisfied."

        elif "null" in root_lower or "undefined" in root_lower:
            recommended_fix = "Introduce defensive null-coalescing or validation checks before accessing object members."
            if language == "JavaScript":
                explanation = "Use optional chaining (?.) or logical OR (||) fallback to guard against accessing properties on undefined variables."
                verification = "Run unit tests covering empty / null API response payloads."
            else:
                explanation = "Add null-check guards: if (obj != null) { ... } or use Optional/coalescing patterns."
                verification = "Execute regression tests with null inputs."

        elif "syntax" in root_lower:
            recommended_fix = "Inspect unclosed brackets, missing colons, or statement terminators."
            explanation = "Correct the syntax structure to conform to language grammar specifications."
            verification = "Run language syntax checker or compiler."

        elif "memory" in root_lower or "recursion" in root_lower:
            recommended_fix = "Refactor recursive calls to use iterative loops with explicit stack, or increase recursion limit."
            explanation = "Prevents stack overflow and excessive memory allocation during tree or nested data processing."
            verification = "Benchmark processing with large or deep nested datasets."

        # If a historical defect has a verified resolution, reference it
        if similar_bugs and similar_bugs[0].get("resolution"):
            top = similar_bugs[0]
            explanation += f" (Supported by historical defect {top['defect_id']} in {top['source']})."

        return {
            "recommended_fix": recommended_fix,
            "commands": commands,
            "explanation": explanation,
            "verification": verification,
            "risks": risks,
            "analysis_mode": "rule-based-fallback"
        }
