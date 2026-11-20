# Accuracy & Evaluation Failure-Case Report

## Overview
This report documents the performance of the Triage and Log Analysis agents across our 15-case ground-truth defect benchmark (`evaluation/reports/eval_latest.json`).

## Performance Summary (n=15)
- **Severity Accuracy:** 60.0% (9/15)
- **Priority Accuracy:** 53.3% (8/15)
- **Exception Type Accuracy:** 80.0% (12/15)
- **Failure Point Accuracy:** 66.7% (10/15)

## Failure-Case Analysis
1. **Ambiguous Stack Traces:** Stack traces containing multiple nested chained exceptions (e.g., `Caused by:`) sometimes resulted in the outermost wrapper exception being captured rather than the root cause.
2. **Cosmetic vs. Low Severity:** Heuristic keywords for cosmetic/documentation bugs occasionally conflicted when reports mentioned words like "failure in documentation".
3. **Noisy Log Lines:** Raw application logs without standard timestamp and log-level prefixes lowered failure point precision.
