# Intelligent Bug Diagnosis Platform with Fix Recommendation Assistance

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/framework-Flask%203.1-black.svg)](https://flask.palletsprojects.com/)
[![ChromaDB](https://img.shields.io/badge/vector%20db-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![Pytest](https://img.shields.io/badge/tests-25%20passed-brightgreen.svg)](https://pytest.org/)

An enterprise-grade, modular, intelligent bug diagnosis platform that accepts software defect reports, parses error logs and stack traces, retrieves relevant historical defects from **Mozilla**, **Apache**, and **Eclipse** defect datasets using **Retrieval-Augmented Generation (RAG)**, isolates root causes through 5 specialized AI agents, and delivers actionable, evidence-based fix recommendations.

---

## 🚀 Key Features

- **Multi-Source Intake & Parsing:** Handles bug titles, markdown descriptions, stack traces, and correlated log excerpts. Supports direct uploads (`.txt`, `.log`, `.json`, `.csv`, `.py`, `.java`, `.js`, `.ts`, `.cpp`).
- **Automated Stack & Log Parsing:** Extracts exception types, message bodies, file paths, line numbers, and execution call depth for Python, Java, JavaScript, C++, and Go.
- **RAG Defect Knowledge Base:** Ingests historical software defect datasets (Mozilla Bugzilla, Apache Jira, Eclipse Bugzilla) with schema normalization, semantic chunking, and 384-dimensional dense vector embeddings (`sentence-transformers/all-MiniLM-L6-v2`).
- **ChromaDB Persistent Vector Store:** Provides sub-millisecond semantic search, metadata filtering (language, status, component), and cosine similarity ranking.
- **5 Specialized Diagnostic AI Agents:**
  1. **Triage Agent:** Categorizes errors into 9 classes and estimates severity.
  2. **Log Analysis Agent:** Pinpoints exact failure locations and isolates user code from framework frames.
  3. **Duplicate Detection Agent:** Matches incoming defects against historical defect records via RAG.
  4. **Root Cause Agent:** Synthesizes triage, log frames, and historical resolutions into an evidence-based diagnosis with confidence scoring.
  5. **Remediation Agent:** Generates actionable code fixes, terminal commands, and verification tests.
- **Provider-Independent LLM Engine:** Supports live cloud LLMs (Google Gemini, OpenAI) with a **deterministic offline rule-based fallback mode** ensuring 100% functionality without internet access or API keys.
- **Modern Presentation Layer:** Responsive developer dashboard with real-time analysis polling, agent breakdown cards, historical evidence explorer, and feedback collection.
- **Comprehensive Test Suite:** 25 automated unit and integration tests across all modules.

---

## 🏛️ System Architecture

```
Bug Submission (Web / REST API)
               │
               ▼
   Bug Intake & Processing Layer
(Input Validation ➔ Stack Parser ➔ Log Parser ➔ Sanitizer)
               │
               ▼
       Agent Orchestrator
               │
               ▼
         Triage Agent
               │
        ┌──────┴──────┐
        ▼             ▼
   Log Analysis   Duplicate Detection (RAG)
      Agent             Agent ◄──► ChromaDB Vector Store
        └──────┬──────┘
               ▼
       Root Cause Agent
               │
               ▼
       Remediation Agent
               │
               ▼
    Complete Diagnosis Report
               │
        ┌──────┴──────┐
        ▼             ▼
Relational Storage  Interactive Web Dashboard
   (SQLite)            & Feedback Loop
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Presentation** | HTML5, CSS3, JavaScript (Fetch API), JetBrains Mono, Plus Jakarta Sans |
| **Backend & API** | Python 3.14 / 3.10+, Flask 3.1, Werkzeug |
| **Relational DB** | SQLite via SQLAlchemy 2.0 ORM (7 relational entities) |
| **Vector DB** | ChromaDB 1.5+ |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`, 384 dimensions) |
| **Testing** | Pytest 9.2 (25 unit & integration tests) |
| **AI / Multi-Agent** | 5 Specialized Agents, ThreadPoolExecutor parallel pipeline, Hybrid LLM/Deterministic Fallback |

---

## 📦 Quick Start & Installation

### 1. Clone & Set Up Virtual Environment

```bash
cd Intelligent-Bug-Diagnosis
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

*(Optional)* To enable live Gemini or OpenAI models, set `LLM_PROVIDER=gemini` and provide `GEMINI_API_KEY=...` in `.env`. By default, the application runs in high-performance **offline deterministic fallback mode** without any external keys required.

### 4. Run the Platform

```bash
python app.py
```

Open your browser at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.

---

## 🧪 Running Tests

Execute the comprehensive test suite:

```bash
pytest tests
```

Output:
```
============================= test session starts ==============================
collected 25 items

tests/test_agents.py .....                                               [ 20%]
tests/test_app.py ....                                                   [ 36%]
tests/test_bug_processor.py .....                                        [ 56%]
tests/test_database.py ...                                               [ 68%]
tests/test_embeddings.py ..                                              [ 76%]
tests/test_ingestion.py ....                                             [ 92%]
tests/test_retrieval.py ..                                               [100%]

======================== 25 passed in 3.13s =========================
```

---

## 🌐 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health, ChromaDB chunk count, LLM status |
| `POST` | `/api/bugs` | Submit bug report (JSON payload) |
| `POST` | `/api/bugs/upload` | Upload log or trace file (`multipart/form-data`) |
| `GET` | `/api/bugs` | List all submitted bugs (supports pagination) |
| `GET` | `/api/bugs/<bug_id>` | Fetch bug report details |
| `POST` | `/api/bugs/<bug_id>/analyze` | Execute 5-agent diagnosis pipeline |
| `GET` | `/api/bugs/<bug_id>/results` | Fetch complete diagnosis report and evidence |
| `POST` | `/api/bugs/<bug_id>/feedback` | Submit user accuracy rating and notes |

---

## 📚 Technical Documentation

- [Research & Defect Analysis](docs/research.md)
- [System Architecture](docs/system_architecture.md)
- [Data Model & Database Specifications](docs/data_model.md)
- [RAG Pipeline & Semantic Retrieval](docs/rag_pipeline.md)
- [Installation & Execution Guide](docs/installation_guide.md)

---

## 🔒 Security & Privacy

- **Sanitization:** Passwords, API tokens, and authorization headers are automatically redacted from error logs before storage or analysis.
- **Secure File Storage:** Uploaded files are verified for size (16 MB cap), extension whitelisting, and stored with sanitized filenames to prevent path traversal attacks.
- **Safe Command Guidance:** Generated terminal commands are explicitly displayed for manual developer review and are **never executed automatically**.
