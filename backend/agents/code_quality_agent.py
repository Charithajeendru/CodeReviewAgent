from __future__ import annotations

from backend.models.finding import Finding, FindingSeverity
from backend.models.project import AnalysisContext


def analyze_code_quality(code: str, filename: str = "", language: str = "generic", context: AnalysisContext | None = None) -> list[Finding]:
    findings: list[Finding] = []
    lines = [line for line in code.splitlines() if line.strip()]

    if len(lines) > 50:
        findings.append(
            Finding(
                agent="Code Quality Agent",
                severity=FindingSeverity.MEDIUM,
                confidence=0.74,
                title="Large function or file likely exceeds maintainability limits",
                description="The file is long and likely bundles multiple responsibilities into a single unit, which makes future changes riskier.",
                file=filename,
                line_start=1,
                line_end=len(lines),
                evidence=f"{len(lines)} non-empty lines detected",
                recommendation="Consider breaking the logic into smaller functions or modules to keep the code easier to test and maintain.",
            )
        )

    nested_if_blocks = sum(1 for line in lines if line.strip().startswith("if ") or line.strip().startswith("elif "))
    if nested_if_blocks > 8:
        findings.append(
            Finding(
                agent="Code Quality Agent",
                severity=FindingSeverity.LOW,
                confidence=0.68,
                title="Complex conditional structure",
                description="The code contains many conditional branches, which can reduce readability and make edge-case testing harder.",
                file=filename,
                line_start=1,
                line_end=len(lines),
                evidence=f"{nested_if_blocks} conditional blocks detected",
                recommendation="Simplify branching with helper functions, early returns, or a clearer decision structure.",
            )
        )

    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if "except:" in stripped or "except Exception" in stripped:
            findings.append(
                Finding(
                    agent="Code Quality Agent",
                    severity=FindingSeverity.INFO,
                    confidence=0.7,
                    title="Broad exception handling",
                    description="Catching all exceptions without context can hide real bugs and make troubleshooting harder.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Handle specific exception types and log enough context to diagnose the underlying problem.",
                )
            )
            break

    if context:
        for cycle in context.project_metadata.get("circular_dependencies", []):
            if filename in cycle:
                findings.append(Finding(
                    agent="Code Quality Agent",
                    severity=FindingSeverity.LOW,
                    confidence=0.85,
                    title="Circular project import relationship",
                    description="The detected internal import graph contains a cycle involving this file.",
                    file=filename,
                    evidence=" -> ".join(cycle),
                    recommendation="Review module ownership and consider extracting shared interfaces to reduce circular coupling.",
                ))
                break

    return findings
