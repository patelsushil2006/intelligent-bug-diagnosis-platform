def classify_bug(error_message):
    """
    Classify a detected programming error into a bug category.
    """

    if not error_message:
        return "Unknown Error"

    message = error_message.lower()

    # Syntax errors
    if any(word in message for word in [
        "syntaxerror",
        "syntax error",
        "expected",
        "unexpected token",
        "missing )",
        "missing ;",
        "unclosed"
    ]):
        return "Syntax Error"

    # Name or variable errors
    if any(word in message for word in [
        "nameerror",
        "undefined variable",
        "undeclared",
        "not defined",
        "unknown identifier"
    ]):
        return "Variable Error"

    # Type errors
    if any(word in message for word in [
        "typeerror",
        "type error",
        "incompatible types",
        "cannot convert",
        "invalid conversion"
    ]):
        return "Type Error"

    # Import or library errors
    if any(word in message for word in [
        "importerror",
        "modulenotfounderror",
        "cannot find module",
        "package not found",
        "no module named"
    ]):
        return "Import Error"

    # Runtime errors
    if any(word in message for word in [
        "zerodivisionerror",
        "division by zero",
        "indexerror",
        "index out of range",
        "keyerror",
        "nullreferenceexception",
        "segmentation fault"
    ]):
        return "Runtime Error"

    # Indentation errors
    if any(word in message for word in [
        "indentationerror",
        "unexpected indent",
        "indentation"
    ]):
        return "Indentation Error"

    return "Other Error"


def get_bug_severity(category):
    """
    Return a severity level for a bug category.
    """

    severity_levels = {
        "Syntax Error": "High",
        "Variable Error": "Medium",
        "Type Error": "Medium",
        "Import Error": "Medium",
        "Runtime Error": "High",
        "Indentation Error": "Medium",
        "Other Error": "Low",
        "Unknown Error": "Low"
    }

    return severity_levels.get(category, "Low")
