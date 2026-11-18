
from backend.bug_detector import detect_bugs


def test_python_syntax_error():

    bugs = detect_bugs(
        "print('hello'",
        "python"
    )

    assert bugs
    assert bugs[0]["type"] == "Syntax Error"


def test_valid_python():

    bugs = detect_bugs(
        "print('hello')",
        "python"
    )

    assert bugs == []


def test_javascript_syntax_error():

    bugs = detect_bugs(
        "function test( {",
        "javascript"
    )

    assert bugs
    assert bugs[0]["type"] == "Syntax Error"


def test_unsupported_language():

    bugs = detect_bugs(
        "some code",
        "unknown"
    )

    assert bugs[0]["type"] == "Unsupported Language"
