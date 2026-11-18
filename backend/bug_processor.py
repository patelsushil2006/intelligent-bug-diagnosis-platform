import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.utils import secure_filename
from config.config import Config


class BugProcessor:
    """Intake, validation, parsing, and normalization for bug reports and error logs."""

    PYTHON_TRACE_PATTERN = re.compile(
        r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\w+)\n(?P<code>(?:\s{4}.*\n)*)',
        re.MULTILINE
    )
    JAVA_TRACE_PATTERN = re.compile(
        r'at (?P<class>[\w\.$]+)\.(?P<method>[\w<>$]+)\((?P<file>[\w\.]+):(?P<line>\d+)\)'
    )
    JS_TRACE_PATTERN = re.compile(
        r'at (?P<func>[^\s(]+)?\s*\(?(?P<file>[^:()]+):(?P<line>\d+):(?P<col>\d+)\)?'
    )

    EXCEPTION_PATTERNS = [
        re.compile(r'^(?P<type>[A-Za-z_][\w\.]*(?:Exception|Error|Failure|Fault)):\s*(?P<msg>.*)$', re.MULTILINE),
        re.compile(r'^(?P<type>panic):\s*(?P<msg>.*)$', re.MULTILINE),
        re.compile(r'^(?P<type>FATAL|CRITICAL|ERROR):\s*(?P<msg>.*)$', re.MULTILINE),
    ]

    @classmethod
    def validate_submission(cls, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate submitted bug report data."""
        title = data.get("title", "").strip()
        if not title:
            return False, "Bug title is required."
        if len(title) > 255:
            return False, "Bug title must not exceed 255 characters."

        # Require at least some diagnostic information
        desc = data.get("description", "").strip()
        stack = data.get("stack_trace", "").strip()
        logs = data.get("log_content", "").strip()

        if not (desc or stack or logs):
            return False, "Please provide at least a description, stack trace, or error log."

        return True, None

    @classmethod
    def parse_stack_trace(cls, raw_trace: str) -> Dict[str, Any]:
        """Parse stack trace to extract exception type, message, frames, and root cause frame."""
        if not raw_trace or not raw_trace.strip():
            return {
                "has_trace": False,
                "exception_type": "Unknown",
                "exception_message": "",
                "frames": [],
                "primary_location": None,
                "primary_line": None
            }

        text = raw_trace.strip()
        exception_type = "UnknownError"
        exception_message = ""

        # Find exception headers / footers
        for pattern in cls.EXCEPTION_PATTERNS:
            matches = list(pattern.finditer(text))
            if matches:
                last_match = matches[-1]
                exception_type = last_match.group("type").strip()
                exception_message = last_match.group("msg").strip()
                break

        # If no regex match, inspect first/last line
        if exception_type == "UnknownError":
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for line in reversed(lines):
                if any(k in line for k in ["Error", "Exception", "panic", "Failed"]):
                    parts = line.split(":", 1)
                    exception_type = parts[0].strip()
                    exception_message = parts[1].strip() if len(parts) > 1 else ""
                    break

        frames: List[Dict[str, Any]] = []

        # Parse Python frames
        py_matches = list(cls.PYTHON_TRACE_PATTERN.finditer(text))
        if py_matches:
            for m in py_matches:
                frames.append({
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "function": m.group("func"),
                    "language": "python"
                })

        # Parse Java frames
        if not frames:
            java_matches = list(cls.JAVA_TRACE_PATTERN.finditer(text))
            if java_matches:
                for m in java_matches:
                    frames.append({
                        "file": m.group("file"),
                        "line": int(m.group("line")),
                        "function": f"{m.group('class')}.{m.group('method')}",
                        "language": "java"
                    })

        # Parse JavaScript frames
        if not frames:
            js_matches = list(cls.JS_TRACE_PATTERN.finditer(text))
            if js_matches:
                for m in js_matches:
                    frames.append({
                        "file": m.group("file").strip(),
                        "line": int(m.group("line")),
                        "function": m.group("func") or "anonymous",
                        "language": "javascript"
                    })

        # Determine primary user code location (last relevant frame)
        primary_location = None
        primary_line = None
        if frames:
            # Filter standard library or framework internals if possible
            user_frames = [f for f in frames if not any(
                p in f["file"] for p in ["site-packages", "node_modules", "jdk", "internal/"]
            )]
            target_frame = user_frames[-1] if user_frames else frames[-1]
            primary_location = target_frame["file"]
            primary_line = target_frame["line"]

        return {
            "has_trace": True,
            "exception_type": exception_type,
            "exception_message": exception_message,
            "frames": frames,
            "primary_location": primary_location,
            "primary_line": primary_line
        }

    @classmethod
    def parse_error_log(cls, raw_log: str) -> Dict[str, Any]:
        """Extract log entries, error levels, timestamps, and error frequencies."""
        if not raw_log or not raw_log.strip():
            return {
                "has_logs": False,
                "error_count": 0,
                "warning_count": 0,
                "critical_entries": []
            }

        lines = raw_log.strip().splitlines()
        error_count = 0
        warning_count = 0
        critical_entries = []

        for line in lines:
            line_upper = line.upper()
            if "ERROR" in line_upper or "FATAL" in line_upper or "CRITICAL" in line_upper:
                error_count += 1
                if len(critical_entries) < 10:
                    critical_entries.append(line.strip())
            elif "WARN" in line_upper:
                warning_count += 1

        return {
            "has_logs": True,
            "error_count": error_count,
            "warning_count": warning_count,
            "critical_entries": critical_entries
        }

    @classmethod
    def detect_language(
        cls,
        code_or_trace: str,
        hint: Optional[str] = None
    ) -> str:
        """Detect programming language using traces, syntax markers, or explicit hint."""
        if hint and hint.lower() not in ("unknown", "auto", ""):
            return hint.capitalize()

        text = code_or_trace.lower()

        # Trace signatures
        if "traceback (most recent call last)" in text or ".py" in text:
            return "Python"
        if "at java." in text or ".java:" in text or "exception in thread" in text:
            return "Java"
        if "at async " in text or ".js:" in text or ".ts:" in text or "node:internal" in text:
            return "JavaScript"
        if "fatal error:" in text or "panic:" in text or ".go:" in text:
            return "Go"
        if ".cpp:" in text or "std::" in text or "segmentation fault" in text:
            return "C++"
        if ".php:" in text or "fatal error: uncaught" in text:
            return "PHP"

        # Code keywords
        if "def " in text and ":" in text and ("import " in text or "print(" in text):
            return "Python"
        if "public class " in text or "system.out.println" in text:
            return "Java"
        if "const " in text or "let " in text or "console.log" in text:
            return "JavaScript"

        return "General/Unknown"

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Normalize text: strip trailing whitespace, normalize line endings, remove sensitive tokens."""
        if not text:
            return ""
        # Normalize newlines
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        # Mask obvious auth tokens or passwords
        normalized = re.sub(r'(bearer\s+)[a-zA-Z0-9_\-\.]{20,}', r'\1[REDACTED]', normalized, flags=re.I)
        normalized = re.sub(r'(api[-_]?key["\'\s:=]+)[a-zA-Z0-9_\-]{16,}', r'\1[REDACTED]', normalized, flags=re.I)
        normalized = re.sub(r'(password["\'\s:=]+)[^\s,;"]+', r'\1[REDACTED]', normalized, flags=re.I)
        return normalized.strip()

    @classmethod
    def handle_file_upload(cls, file_storage) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate and securely process uploaded bug report / log file."""
        if not file_storage or not file_storage.filename:
            return False, "No file uploaded.", {}

        filename = secure_filename(file_storage.filename)
        if not filename:
            return False, "Invalid filename.", {}

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in Config.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file extension '.{ext}'. Allowed: {', '.join(sorted(Config.ALLOWED_EXTENSIONS))}", {}

        try:
            content_bytes = file_storage.read()
            if len(content_bytes) > Config.MAX_CONTENT_LENGTH:
                return False, f"File exceeds maximum size of {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB.", {}

            text_content = content_bytes.decode("utf-8", errors="replace")

            # Save a pristine copy in controlled uploads directory
            safe_save_path = Config.UPLOAD_FOLDER / filename
            # Add salt to filename if already exists
            if safe_save_path.exists():
                import uuid
                safe_save_path = Config.UPLOAD_FOLDER / f"{uuid.uuid4().hex[:8]}_{filename}"

            with open(safe_save_path, "w", encoding="utf-8") as f:
                f.write(text_content)

            return True, "File processed successfully.", {
                "filename": filename,
                "saved_path": str(safe_save_path),
                "content": text_content,
                "extension": ext
            }
        except Exception as e:
            return False, f"File reading error: {str(e)}", {}
