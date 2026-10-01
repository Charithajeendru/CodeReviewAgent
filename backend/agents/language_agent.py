from __future__ import annotations

import re
from pathlib import PurePosixPath

from backend.models.review import LanguageInfo
from backend.services.language_registry import LANGUAGES_BY_EXTENSION, LANGUAGES_BY_FILENAME, resolve_language


def detect_language(code: str, filename: str = "", user_language: str | None = None) -> LanguageInfo:
    if user_language and user_language.strip().casefold() not in {"auto", "auto detect"}:
        capability = resolve_language(user_language)
        if capability:
            return _language_info(capability, 100, "explicit", filename)
        return _unknown(filename, "explicit")

    path = PurePosixPath(filename.replace("\\", "/")) if filename else PurePosixPath("")
    file_name = path.name.casefold()
    extension = path.suffix.casefold()
    capability = LANGUAGES_BY_EXTENSION.get(extension)
    if capability:
        return _language_info(capability, 100, "extension", filename)

    capability = LANGUAGES_BY_FILENAME.get(file_name)
    if capability:
        return _language_info(capability, 95, "filename", filename)

    first_line = code.splitlines()[0].strip() if code.splitlines() else ""
    if first_line.startswith("#!"):
        shebang = first_line.casefold()
        if re.search(r"\b(python)(\d+(\.\d+)*)?\b", shebang):
            return _language_info(resolve_language("python"), 98, "shebang", filename)
        if re.search(r"\b(bash|sh|zsh|fish)\b", shebang):
            return _language_info(resolve_language("shell"), 98, "shebang", filename)
        if re.search(r"\bpwsh\b", shebang):
            return _language_info(resolve_language("powershell"), 98, "shebang", filename)

    code_lower = code.lower()
    candidates = (
        (r"^\s*(?:from\s+\w[\w.]*\s+import\s+|import\s+\w[\w.]*|def\s+\w+\s*\()", "python", 78),
        (r"^\s*interface\s+\w+|:\s*(?:string|number|boolean)\b|\btype\s+\w+\s*=", "typescript", 78),
        (r"\b(?:const|let|var)\s+\w+\s*=|\bfunction\s+\w+\s*\(|\bexport\s+default\b", "javascript", 75),
        (r"\bpublic\s+(?:static\s+)?class\s+\w+|\bimport\s+java\.", "java", 82),
        (r"^\s*package\s+main\s*$|\bfmt\.println\s*\(", "go", 82),
        (r"\bfn\s+\w+\s*\(|\bprintln!\s*\(", "rust", 82),
        (r"^\s*(?:select|insert\s+into|create\s+table)\b", "sql", 80),
        (r"<!doctype\s+html|<html(?:\s|>)", "html", 85),
    )
    matches = [
        (confidence, resolve_language(language_id))
        for pattern, language_id, confidence in candidates
        if re.search(pattern, code_lower, re.MULTILINE)
    ]
    matches = [(confidence, item) for confidence, item in matches if item is not None]
    if matches:
        matches.sort(key=lambda match: match[0], reverse=True)
        if len(matches) == 1 or matches[0][0] - matches[1][0] >= 10:
            return _language_info(matches[0][1], matches[0][0], "content", filename)

    return _unknown(filename, "unknown")


def _language_info(capability, confidence: float, method: str, filename: str) -> LanguageInfo:
    return LanguageInfo(
        language=capability.name,
        language_id=capability.id,
        confidence=confidence,
        detection_method=method,
        file_extension=PurePosixPath(filename.replace("\\", "/")).suffix or None,
        static_analysis_available=capability.static_analysis_available,
        notes="Language detection does not imply AI analysis or language-specific static analysis availability.",
    )


def _unknown(filename: str, method: str) -> LanguageInfo:
    return LanguageInfo(
        language="Unknown",
        language_id="unknown",
        confidence=0,
        detection_method=method,
        file_extension=PurePosixPath(filename.replace("\\", "/")).suffix or None,
        static_analysis_available=False,
        notes="Language could not be determined reliably.",
    )
