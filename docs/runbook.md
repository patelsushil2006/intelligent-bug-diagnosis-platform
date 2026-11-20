# Operational Runbook

## 1. Seed Knowledge Base
Run `make seed` or:
```bash
python -c "from knowledge_base.ingestion import DefectIngestionPipeline; DefectIngestionPipeline().seed_initial_knowledge_base()"
```

## 2. Re-run Evaluation Suite
Run `make eval` or:
```bash
python -m evaluation.run_eval --min-severity-acc 0.3
```

## 3. View Evaluation Reports
Inspect generated evaluation metrics and failure analyses:
```bash
cat evaluation/reports/eval_latest.json
cat docs/accuracy_report.md
```

## 4. Rotate LLM API Keys
Update `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`, set `LLM_PROVIDER`, and restart the service (`python app.py` or `docker compose restart app`).

## 5. Recover from ChromaDB Corruption
If `vector_store/data/` becomes corrupt, reset and re-seed:
```bash
rm -rf vector_store/data/ && make seed
```
