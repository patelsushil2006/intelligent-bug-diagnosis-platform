from backend.bug_classifier import classify_bug, get_bug_severity
from backend.bug_recommender import generate_recommendation


def diagnose_bug(bug, language="python"):
    """
    Add a category, severity, explanation, and recommendation
    to a detected bug.
    """

    if not isinstance(bug, dict):
        return {}

    diagnosed_bug = bug.copy()

    error_message = (
        diagnosed_bug.get("message")
        or diagnosed_bug.get("description")
        or diagnosed_bug.get("error")
        or ""
    )

    category = classify_bug(error_message)

    diagnosed_bug["category"] = category
    diagnosed_bug["severity"] = get_bug_severity(category)

    recommendation = generate_recommendation(diagnosed_bug, language)

    if isinstance(recommendation, dict):
        diagnosed_bug.update(recommendation)

    return diagnosed_bug


def diagnose_bugs(bugs, language="python"):
    """
    Diagnose a list of detected bugs.
    """

    if not bugs:
        return []

    return [
        diagnose_bug(bug, language)
        for bug in bugs
    ]
