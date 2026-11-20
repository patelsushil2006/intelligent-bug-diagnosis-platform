
import re


# Function calls that can be safely recognized
SUPPORTED_CALLS = (
    "printf",
    "fprintf",
    "sprintf",
    "console.log",
    "console.error",
    "console.warn",
    "print",
    "println",
    "System.out.println",
    "System.out.print",
    "Console.WriteLine",
    "Console.Write",
)


def remove_strings_and_comments(line):
    """Mask quoted strings and simple comments before counting brackets."""

    result = []
    quote = None
    escaped = False
    i = 0

    while i < len(line):
        char = line[i]
        next_char = line[i + 1] if i + 1 < len(line) else ""

        if quote:
            result.append(" ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            i += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            result.append(" ")
            i += 1
            continue

        if char == "/" and next_char == "/":
            break

        if char == "#":
            break

        result.append(char)
        i += 1

    return "".join(result)


def auto_fix_code(code, language):
    """
    Apply only a narrow, recognizable fix:
    add one missing ')' before a statement-ending semicolon
    for a known print/output function call.
    
    Return corrected source if changed, otherwise None.
    """

    language = language.lower().strip()

    supported_languages = {
        "c", "cpp", "java", "csharp",
        "javascript", "typescript", "php"
    }

    if language not in supported_languages:
        return None

    lines = code.splitlines()
    fixed_lines = []
    changed = False

    for line in lines:
        stripped = line.strip()
        masked = remove_strings_and_comments(stripped)

        is_known_call = any(
            re.search(r"\b" + re.escape(call) + r"\s*\(", masked)
            for call in SUPPORTED_CALLS
        )

        if is_known_call and stripped.endswith(";"):
            open_count = masked.count("(")
            close_count = masked.count(")")

            # Only fix exactly one missing closing parenthesis.
            if open_count - close_count == 1:
                semicolon_index = line.rfind(";")

                if semicolon_index != -1:
                    line = (
                        line[:semicolon_index]
                        + ")"
                        + line[semicolon_index:]
                    )
                    changed = True

        fixed_lines.append(line)

    if changed:
        return "\n".join(fixed_lines)

    return None
