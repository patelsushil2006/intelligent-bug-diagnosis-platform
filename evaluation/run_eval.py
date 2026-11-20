import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from agents.triage_agent import TriageAgent
from agents.log_analysis_agent import LogAnalysisAgent


def run_evaluation(min_severity_acc: float = 0.0) -> int:
    base_dir = Path(__file__).resolve().parent.parent
    dataset_path = base_dir / "evaluation" / "datasets" / "ground_truth.jsonl"
    reports_dir = base_dir / "evaluation" / "reports"
    docs_dir = base_dir / "docs"

    if not dataset_path.exists():
        print(f"Error: dataset file not found at {dataset_path}", file=sys.stderr)
        return 1

    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    n = len(records)
    if n == 0:
        print("Error: empty dataset", file=sys.stderr)
        return 1

    triage_agent = TriageAgent()
    log_agent = LogAnalysisAgent()

    severity_hits = 0
    priority_hits = 0
    exception_hits = 0
    failure_point_hits = 0

    mismatches = []

    for item in records:
        case_id = item.get("id", "unknown")
        inp = item.get("input", {})
        exp = item.get("expected", {})

        desc = inp.get("description", "")
        stack = inp.get("stack_trace", "")
        logs = inp.get("logs", "")
        lang = inp.get("language", "")

        # Safe execution of TriageAgent
        try:
            triage_out = triage_agent.process(
                context_or_title={"title": desc, "description": desc, "stack_trace": stack, "log_content": logs, "language": lang}
            )
        except Exception as e:
            triage_out = {"error": str(e), "severity": "Error", "priority": "Error", "affected_component": "error"}

        # Safe execution of LogAnalysisAgent
        try:
            log_out = log_agent.process(
                context_or_trace={"stack_trace": stack, "log_content": logs}
            )
        except Exception as e:
            log_out = {"error": str(e), "exception_type": "Error", "failure_point": "error"}

        pred_sev = triage_out.get("severity", "")
        pred_prio = triage_out.get("priority", "")
        pred_exc = str(log_out.get("exception_type", "")).strip().lower()
        pred_fp = str(log_out.get("failure_point", "")).strip().lower()

        exp_sev = exp.get("severity", "")
        exp_prio = exp.get("priority", "")
        exp_exc = str(exp.get("exception_type", "")).strip().lower()
        exp_fp = str(exp.get("failure_point", "")).strip().lower()

        is_sev_match = (pred_sev == exp_sev)
        is_prio_match = (pred_prio == exp_prio)
        is_exc_match = (pred_exc == exp_exc or (exp_exc in pred_exc) or (pred_exc in exp_exc))
        is_fp_match = (exp_fp in pred_fp or pred_fp in exp_fp) if (exp_fp and pred_fp) else False

        if is_sev_match:
            severity_hits += 1
        if is_prio_match:
            priority_hits += 1
        if is_exc_match:
            exception_hits += 1
        if is_fp_match:
            failure_point_hits += 1

        case_errors = []
        if not is_sev_match:
            case_errors.append(f"Severity mismatch (got: {pred_sev}, expected: {exp_sev})")
        if not is_prio_match:
            case_errors.append(f"Priority mismatch (got: {pred_prio}, expected: {exp_prio})")
        if not is_exc_match:
            case_errors.append(f"Exception mismatch (got: {pred_exc}, expected: {exp_exc})")
        if not is_fp_match:
            case_errors.append(f"Failure point mismatch (got: {pred_fp}, expected: {exp_fp})")

        if case_errors:
            mismatches.append({
                "id": case_id,
                "description": desc,
                "errors": case_errors
            })

    severity_accuracy = severity_hits / n
    priority_accuracy = priority_hits / n
    exception_accuracy = exception_hits / n
    failure_point_accuracy = failure_point_hits / n

    # Format Markdown Table
    table_lines = [
        "| Field | Accuracy | n |",
        "| :--- | :--- | :--- |",
        f"| Severity Accuracy | {severity_accuracy * 100:.1f}% | {n} |",
        f"| Priority Accuracy | {priority_accuracy * 100:.1f}% | {n} |",
        f"| Exception Accuracy | {exception_accuracy * 100:.1f}% | {n} |",
        f"| Failure Point Accuracy | {failure_point_accuracy * 100:.1f}% | {n} |",
    ]
    markdown_table = "\n".join(table_lines)

    # Print markdown table to stdout
    print(markdown_table)

    # Write evaluation/reports/eval_latest.json
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_data = {
        "n": n,
        "total_cases": n,
        "severity_accuracy": round(severity_accuracy, 4),
        "priority_accuracy": round(priority_accuracy, 4),
        "exception_accuracy": round(exception_accuracy, 4),
        "failure_point_accuracy": round(failure_point_accuracy, 4),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(reports_dir / "eval_latest.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Write docs/accuracy_report.md
    docs_dir.mkdir(parents=True, exist_ok=True)
    doc_lines = [
        "# Accuracy & Evaluation Report",
        "",
        "## Summary Results",
        "",
        markdown_table,
        "",
        "## Failure Cases",
        ""
    ]
    if mismatches:
        for m in mismatches:
            doc_lines.append(f"- **{m['id']}**: {m['description']}")
            for err in m["errors"]:
                doc_lines.append(f"  - {err}")
    else:
        doc_lines.append("No mismatches detected across test cases.")

    with open(docs_dir / "accuracy_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(doc_lines) + "\n")

    if severity_accuracy < min_severity_acc:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Evaluate Bug Diagnosis agents against ground truth dataset.")
    parser.add_argument("--min-severity-acc", type=float, default=0.0, help="Minimum severity accuracy threshold to pass.")
    args = parser.parse_args()

    exit_code = run_evaluation(min_severity_acc=args.min_severity_acc)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
