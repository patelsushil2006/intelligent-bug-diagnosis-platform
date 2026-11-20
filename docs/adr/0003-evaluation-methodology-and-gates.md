# ADR 0003: Evaluation Methodology and Gates

## Context
Evaluating AI diagnostic agents with synthetic 100% passing unit tests creates a false sense of reliability
and obscures real-world failure modes.
Real software defect reports contain noisy formatting, missing stack traces, multi-language snippets,
and ambiguous error logs that degrade parsing accuracy.

## Decision
We established an empirical 15-case ground-truth benchmark dataset spanning multiple languages, formats, and noisy logs.
The evaluation harness (`evaluation/run_eval.py`) scores exact-match accuracy against ground-truth labels
and gates CI builds with minimum score thresholds (e.g., minimum 30% severity accuracy).
We explicitly record and report true failure cases rather than gaming metrics.

## Consequences
- **Positive:** Transparent, honest accuracy metrics (e.g. 60% severity, 53.3% priority) that reveal genuine diagnostic challenges.
- **Positive:** Honest low numbers beat fake high ones by establishing an authentic engineering baseline for iterative improvements.
- **Negative:** Reported accuracy numbers appear lower than synthetic marketing benchmarks, requiring stakeholder education.
- **Negative:** CI builds fail if heuristic changes cause regressions below enforced threshold gates.
