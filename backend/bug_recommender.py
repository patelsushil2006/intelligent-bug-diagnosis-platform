
def generate_recommendation(bug, language):

    message = bug.get("message", "")
    lower = message.lower()
    bug_type = bug.get("type", "")

    explanation = (
        "The language analyzer reported a problem in the source code."
    )

    recommendation = (
        "Read the analyzer message and inspect the reported line "
        "and the line before it."
    )

    if bug_type == "Analyzer Unavailable":

        explanation = "The required compiler or syntax checker could not be found."

        recommendation = (
            "Install the required tool and make sure it is available "
            "in your terminal PATH."
        )

    elif bug_type == "Analyzer Timeout":

        explanation = "The syntax checker did not finish within its time limit."

        recommendation = "Try a smaller source file and check the analyzer installation."

    elif bug_type == "Analyzer Error":

        explanation = "The analyzer could not run successfully."

        recommendation = "Check the analyzer installation and the error message."

    elif bug_type == "Unsupported Language":

        explanation = "This programming language is not configured."

        recommendation = "Select one of the nine supported languages."

    elif language == "python":

        if "was never closed" in lower:

            explanation = (
                "An opening bracket, parenthesis, or quotation mark "
                "has no matching closing character."
            )

            recommendation = (
                "Add the missing closing character and check nearby lines."
            )

        elif "expected ':'" in lower:

            explanation = "A Python block statement is missing its colon."

            recommendation = (
                "Add ':' after if, elif, else, for, while, def, or class."
            )

        elif "unexpected indent" in lower or "unindent does not match" in lower:

            explanation = "The Python indentation is inconsistent."

            recommendation = (
                "Correct the indentation and use consistent spaces."
            )

        elif "invalid syntax" in lower:

            explanation = "Python could not parse the statement."

            recommendation = (
                "Check the reported line and the previous line for "
                "missing operators, brackets, or keywords."
            )

    elif language in ("javascript", "typescript"):

        if (
            "unexpected end of input" in lower
            or "unexpected token" in lower
            or "expected" in lower
        ):

            explanation = (
                "The parser found incomplete or unexpected syntax."
            )

            recommendation = (
                "Check matching braces, parentheses, brackets, quotes, "
                "commas, and statement endings."
            )

        elif "cannot find name" in lower or "is not defined" in lower:

            explanation = "The code refers to an identifier that cannot be resolved."

            recommendation = (
                "Check the identifier spelling, declaration, and scope."
            )

    elif language in ("java", "csharp", "c", "cpp"):

        if "expected" in lower or "expecting" in lower:

            explanation = (
                "The compiler expected a syntax element that is missing "
                "or misplaced."
            )

            recommendation = (
                "Check the reported line for missing semicolons, "
                "parentheses, braces, or declarations."
            )

        elif (
            "undeclared" in lower
            or "does not exist" in lower
            or "not exist" in lower
        ):

            explanation = (
                "The code refers to a name that is not declared "
                "or is not in scope."
            )

            recommendation = (
                "Declare the variable or method, correct its spelling, "
                "or check its scope."
            )

        elif "cannot convert" in lower or "incompatible types" in lower:

            explanation = "The expression uses incompatible data types."

            recommendation = (
                "Use compatible data types or an appropriate conversion."
            )

    elif language == "php":

        if "unexpected" in lower or "parse error" in lower:

            explanation = (
                "PHP encountered an unexpected token while parsing the file."
            )

            recommendation = (
                "Check the reported line and previous line for missing "
                "semicolons, brackets, or quotes."
            )

    elif language == "go":

        if "expected" in lower or "syntax error" in lower:

            explanation = (
                "The Go parser found incomplete or misplaced syntax."
            )

            recommendation = (
                "Check the reported line for matching braces, "
                "parentheses, and valid Go syntax."
            )

    return {
        "explanation": explanation,
        "recommendation": recommendation
    }
