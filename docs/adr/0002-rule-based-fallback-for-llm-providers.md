# ADR 0002: Rule-Based Fallback for LLM Providers

## Context
Production LLM APIs (such as Google Gemini and OpenAI) introduce network latency, API rate limits,
external financial cost, and require active internet connectivity.
In air-gapped enterprise environments, local development without API keys, or automated CI pipelines,
external LLM calls can fail and block software defect diagnosis.

## Decision
We implemented a provider-independent `LLMClient` with a strict, deterministic rule-based fallback mechanism.
When API keys are absent or calls fail, agents automatically switch to regex pattern matching
and heuristic classification, returning complete Pydantic-validated JSON structures.
Heuristic parsers cover syntax, dependency, memory, network, database, and logic errors.

## Consequences
- **Positive:** 100% operational availability offline with zero external credentials required.
- **Positive:** Test suites run quickly and reliably in CI without mocking network boundaries.
- **Negative:** Offline recommendations use predefined heuristic guidance rather than dynamically generated code diffs.
- **Negative:** Complex natural language explanations are less contextual than frontier LLM outputs.
