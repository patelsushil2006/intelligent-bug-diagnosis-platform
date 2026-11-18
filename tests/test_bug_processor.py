import io
from werkzeug.datastructures import FileStorage
from backend.bug_processor import BugProcessor


def test_validate_submission():
    # Empty title
    ok, err = BugProcessor.validate_submission({"title": ""})
    assert not ok
    assert "Bug title is required" in err

    # Empty details
    ok, err = BugProcessor.validate_submission({"title": "Valid Title"})
    assert not ok
    assert "provide at least a description" in err

    # Valid
    ok, err = BugProcessor.validate_submission({
        "title": "Valid Title",
        "description": "Valid description"
    })
    assert ok
    assert err is None


def test_parse_python_stack_trace():
    trace = """Traceback (most recent call last):
  File "main.py", line 42, in process_data
    return items[10]
IndexError: list index out of range"""

    parsed = BugProcessor.parse_stack_trace(trace)
    assert parsed["has_trace"] is True
    assert parsed["exception_type"] == "IndexError"
    assert parsed["primary_location"] == "main.py"
    assert parsed["primary_line"] == 42


def test_parse_java_stack_trace():
    trace = """Exception in thread "main" java.lang.NullPointerException
\tat com.example.service.UserService.getUser(UserService.java:105)
\tat com.example.App.main(App.java:12)"""

    parsed = BugProcessor.parse_stack_trace(trace)
    assert parsed["has_trace"] is True
    assert "NullPointerException" in parsed["exception_type"]
    assert parsed["primary_location"] == "App.java"
    assert parsed["primary_line"] == 12


def test_detect_language():
    assert BugProcessor.detect_language("Traceback (most recent call last):") == "Python"
    assert BugProcessor.detect_language("at com.example.service(Service.java:10)") == "Java"
    assert BugProcessor.detect_language("at processTicksAndRejections (node:internal:10)") == "JavaScript"
    assert BugProcessor.detect_language("", hint="Go") == "Go"


def test_file_upload_validation():
    # Unsupported extension
    storage = FileStorage(
        stream=io.BytesIO(b"malicious executable"),
        filename="malware.exe"
    )
    ok, msg, _ = BugProcessor.handle_file_upload(storage)
    assert not ok
    assert "Unsupported file extension" in msg

    # Valid text file
    storage_ok = FileStorage(
        stream=io.BytesIO(b"ERROR 2026-11-12 Database connection lost"),
        filename="app_error.log"
    )
    ok, msg, data = BugProcessor.handle_file_upload(storage_ok)
    assert ok
    assert "app_error.log" in data["filename"]
    assert "Database connection lost" in data["content"]
