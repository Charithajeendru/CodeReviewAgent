from __future__ import annotations

import re

from backend.models.finding import Finding, FindingSeverity
from backend.models.project import AnalysisContext


def analyze_security(code: str, filename: str = "", language: str = "generic", context: AnalysisContext | None = None) -> list[Finding]:
    findings: list[Finding] = []
    lines = code.splitlines()

    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue

        lower = stripped.lower()
        if any(token in lower for token in ["password", "secret", "api_key", "token"]) and "=" in stripped:
            findings.append(
                Finding(
                    agent="Security Agent",
                    severity=FindingSeverity.HIGH,
                    confidence=0.8,
                    title="Potential hardcoded secret or credential",
                    description="A credential-like value appears to be assigned directly in source code instead of being resolved from secure configuration.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Load secrets from environment variables or a secure secret manager, and avoid embedding them in code.",
                )
            )
            continue

        if "query\" +" in stripped or "SELECT " in stripped.upper() and "+" in stripped:
            findings.append(
                Finding(
                    agent="Security Agent",
                    severity=FindingSeverity.HIGH,
                    confidence=0.87,
                    title="Possible SQL injection vector",
                    description="String concatenation is being used to build a database query, which can allow injection when user input is included.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Use parameterized queries and avoid concatenating user-controlled values into SQL statements.",
                )
            )
            continue

        if "eval(" in stripped or "exec(" in stripped or "compile(" in stripped:
            findings.append(
                Finding(
                    agent="Security Agent",
                    severity=FindingSeverity.CRITICAL,
                    confidence=0.9,
                    title="Code execution sink",
                    description="Dynamic evaluation or execution may allow remote code execution or sandbox escape when user-controlled data is used.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Avoid dynamic execution. If execution is required, validate the input strictly and isolate it in a secure sandbox.",
                )
            )

    if context and any(
        relationship.source == filename and relationship.resolution_status == "resolved_internal"
        for relationship in context.relationships
    ) and any(re.search(r"\b(?:request\.(?:args|query|json|form|params|body)|req\.(?:query|body|params)|input\s*\()", line) for line in lines):
        for related_file in context.related_files:
            for line_number, line in enumerate(related_file["content"].splitlines(), 1):
                stripped = line.strip()
                if re.search(r"\b(?:eval|exec)\s*\(", stripped):
                    findings.append(Finding(
                        agent="Security Agent",
                        severity=FindingSeverity.MEDIUM,
                        confidence=0.55,
                        title="Potential cross-file untrusted input and dynamic execution path",
                        description="A directly related file contains dynamic execution while this file references request-controlled input. The value flow is heuristic and requires manual confirmation.",
                        file=related_file["path"],
                        line_start=line_number,
                        line_end=line_number,
                        evidence=stripped,
                        recommendation="Trace the request value through the related modules and avoid passing untrusted data to dynamic execution.",
                    ))

    return findings
