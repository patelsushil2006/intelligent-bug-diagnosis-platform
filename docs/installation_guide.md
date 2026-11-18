# Installation and Execution Guide

## Prerequisites
- **Python:** 3.10 to 3.14
- **Operating System:** macOS, Linux, or Windows
- **Package Manager:** pip

---

## 1. Setup Virtual Environment

```bash
# Clone or navigate to the project directory
cd Intelligent-Bug-Diagnosis

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment variables:
- `FLASK_DEBUG`: Set to `True` for development reloading.
- `SECRET_KEY`: Random secret string for sessions.
- `DATABASE_URL`: Defaults to `sqlite:///bug_platform.db`.
- `LLM_PROVIDER`: Set to `offline` (default), `gemini`, or `openai`.
- `GEMINI_API_KEY` / `OPENAI_API_KEY`: Optional; if omitted, the platform runs in full deterministic rule-based mode.

---

## 4. Run the Application

```bash
python app.py
```

The application will start on:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 5. Run the Test Suite

```bash
pytest tests
```
