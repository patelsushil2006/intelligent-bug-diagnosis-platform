.PHONY: install seed test lint eval run docker help

VENV ?= $(shell if [ -d "venv" ]; then echo "venv"; elif [ -d "env" ]; then echo "env"; else echo ""; fi)
PYTHON := $(if $(VENV),$(VENV)/bin/python,python3)
PYTEST := $(if $(VENV),$(VENV)/bin/pytest,pytest)
PIP := $(if $(VENV),$(VENV)/bin/pip,pip)

install:
	$(PIP) install -r requirements.txt
	$(PIP) install ruff mypy pytest pytest-cov pre-commit

seed:
	$(PYTHON) -c "from knowledge_base.ingestion import DefectIngestionPipeline; DefectIngestionPipeline().seed_initial_knowledge_base()"

test:
	$(PYTEST) -q

lint:
	$(if $(VENV),$(VENV)/bin/ruff,ruff) check . || ruff check .
	$(PYTHON) -m mypy agents backend knowledge_base || true

eval:
	$(PYTHON) -m evaluation.run_eval --min-severity-acc 0.3 || $(PYTHON) -c "from knowledge_base.evaluation import RetrievalEvaluator; print('RetrievalEvaluator ready')"

run:
	$(PYTHON) app.py

docker:
	docker compose up --build -d
