
import ast
import esprima
import javalang
import os
import re
import shutil
import subprocess
import tempfile


def get_error_line(message):

    patterns = [
        r":(\d+):\d+:",
        r"\((\d+),\d+\)",
        r"line\s+(\d+)",
        r":(\d+):"
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)

        if match:
            return int(match.group(1))

    return 1


def analyzer_issue(kind, message, severity="Info"):

    return [{
        "type": kind,
        "line": get_error_line(message),
        "message": message.strip() or kind,
        "severity": severity
    }]


def run_checker(command_builder, filename, timeout=20):

    try:
        result = subprocess.run(
            command_builder(filename),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:

            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Syntax checking failed."
            )

            return analyzer_issue(
                "Syntax Error",
                message,
                "High"
            )

        return []

    except subprocess.TimeoutExpired:

        return analyzer_issue(
            "Analyzer Timeout",
            "Syntax checker exceeded its time limit."
        )

    except OSError as error:

        return analyzer_issue(
            "Analyzer Error",
            str(error)
        )


def check_compiler(code, suffix, compiler, arguments):

    compiler_path = shutil.which(compiler)

    if not compiler_path:
        return analyzer_issue(
            "Analyzer Unavailable",
            f"{compiler} is not installed or available in PATH."
        )

    filename = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            encoding="utf-8",
            delete=False
        ) as source:

            source.write(code)
            filename = source.name

        return run_checker(
            lambda path: [compiler_path] + arguments(path),
            filename
        )

    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


# PYTHON

def detect_python_bugs(code):

    try:
        ast.parse(code)
        return []

    except SyntaxError as error:

        return [{
            "type": "Syntax Error",
            "line": error.lineno or 1,
            "message": error.msg,
            "severity": "High"
        }]


# JAVASCRIPT

def detect_javascript_bugs(code):

    try:
        esprima.parseScript(code)
        return []

    except Exception as error:

        return [{
            "type": "Syntax Error",
            "line": getattr(error, "lineNumber", 1) or 1,
            "message": str(error),
            "severity": "High"
        }]


# JAVA

def detect_java_bugs(code):

    try:
        javalang.parse.parse(code)
        return []

    except (
        javalang.parser.JavaSyntaxError,
        javalang.tokenizer.LexerError
    ) as error:

        position = getattr(error, "position", None)

        return [{
            "type": "Syntax Error",
            "line": position.line if position else 1,
            "message": str(error),
            "severity": "High"
        }]


# TYPESCRIPT

def detect_typescript_bugs(code):

    return check_compiler(
        code,
        ".ts",
        "tsc",
        lambda path: [
            "--noEmit",
            "--skipLibCheck",
            "--pretty",
            "false",
            path
        ]
    )


# C

def detect_c_bugs(code):

    return check_compiler(
        code,
        ".c",
        "clang",
        lambda path: [
            "-fsyntax-only",
            "-x",
            "c",
            path
        ]
    )


# C++

def detect_cpp_bugs(code):

    return check_compiler(
        code,
        ".cpp",
        "clang++",
        lambda path: [
            "-fsyntax-only",
            "-x",
            "c++",
            path
        ]
    )


# C#

def detect_csharp_bugs(code):

    dotnet = shutil.which("dotnet")

    if not dotnet:
        return analyzer_issue(
            "Analyzer Unavailable",
            "Install the .NET SDK to analyze C# code."
        )

    try:
        with tempfile.TemporaryDirectory() as directory:

            project_file = os.path.join(
                directory,
                "BugCheck.csproj"
            )

            source_file = os.path.join(
                directory,
                "Program.cs"
            )

            with open(project_file, "w", encoding="utf-8") as project:

                project.write(
                    '<Project Sdk="Microsoft.NET.Sdk">'
                    '<PropertyGroup>'
                    '<TargetFramework>net8.0</TargetFramework>'
                    '<OutputType>Library</OutputType>'
                    '<ImplicitUsings>disable</ImplicitUsings>'
                    '<Nullable>disable</Nullable>'
                    '</PropertyGroup>'
                    '</Project>'
                )

            with open(source_file, "w", encoding="utf-8") as source:
                source.write(code)

            result = subprocess.run(
                [
                    dotnet,
                    "build",
                    project_file,
                    "--nologo",
                    "-v:q"
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=directory
            )

            if result.returncode == 0:
                return []

            output = result.stdout + "\n" + result.stderr

            errors = []

            for line in output.splitlines():

                if "error CS" in line:

                    errors.append({
                        "type": "Compilation Error",
                        "line": get_error_line(line),
                        "message": line.strip(),
                        "severity": "High"
                    })

            return errors or analyzer_issue(
                "Compilation Error",
                output[-2000:],
                "High"
            )

    except subprocess.TimeoutExpired:

        return analyzer_issue(
            "Analyzer Timeout",
            ".NET compilation exceeded the time limit."
        )

    except OSError as error:

        return analyzer_issue(
            "Analyzer Error",
            str(error)
        )


# PHP

def detect_php_bugs(code):

    php = shutil.which("php")

    if not php:
        return analyzer_issue(
            "Analyzer Unavailable",
            "PHP is not installed or available in PATH."
        )

    filename = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".php",
            encoding="utf-8",
            delete=False
        ) as source:

            source.write(code)
            filename = source.name

        result = subprocess.run(
            [php, "-l", filename],
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.returncode == 0:
            return []

        message = result.stderr.strip() or result.stdout.strip()

        return analyzer_issue(
            "Syntax Error",
            message,
            "High"
        )

    except subprocess.TimeoutExpired:

        return analyzer_issue(
            "Analyzer Timeout",
            "PHP syntax checking exceeded the time limit."
        )

    except OSError as error:

        return analyzer_issue(
            "Analyzer Error",
            str(error)
        )

    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


# GO

def detect_go_bugs(code):

    return check_compiler(
        code,
        ".go",
        "gofmt",
        lambda path: [
            "-e",
            "-d",
            path
        ]
    )


# MAIN DETECTOR

def detect_bugs(code, language):

    analyzers = {
        "python": detect_python_bugs,
        "javascript": detect_javascript_bugs,
        "typescript": detect_typescript_bugs,
        "java": detect_java_bugs,
        "c": detect_c_bugs,
        "cpp": detect_cpp_bugs,
        "csharp": detect_csharp_bugs,
        "php": detect_php_bugs,
        "go": detect_go_bugs
    }

    analyzer = analyzers.get(language.lower().strip())

    if analyzer is None:
        return analyzer_issue(
            "Unsupported Language",
            "No analyzer is configured for this language."
        )

    return analyzer(code)
