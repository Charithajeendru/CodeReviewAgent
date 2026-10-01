from __future__ import annotations

from collections import defaultdict


def analyze_static(code: str, language: str, filename: str) -> dict:
    lines = code.splitlines()
    markers = defaultdict(list)

    checks = {
        "missing_braces": 0,
        "nested_loops": 0,
        "suspicious_null_check": 0,
        "hardcoded_secret_like": 0,
        "sql_string_concat": 0,
    }

    for index, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        if stripped.count("{") > stripped.count("}"):
            checks["missing_braces"] += 1
        if "for " in stripped and "for " in stripped and stripped.count("for") > 1:
            checks["nested_loops"] += 1
        if "== null" in stripped or "== None" in stripped or "=== undefined" in stripped:
            checks["suspicious_null_check"] += 1
        if any(token in stripped.lower() for token in ["password", "secret", "api_key", "token"]) and "=" in stripped:
            checks["hardcoded_secret_like"] += 1
        if "SELECT " in stripped.upper() and "+" in stripped:
            checks["sql_string_concat"] += 1

    return {
        "language": language,
        "filename": filename,
        "status": "ok",
        "checks": checks,
        "note": "Static-analysis layer operates without executing user code; it inspects syntax markers and common risk patterns.",
    }
