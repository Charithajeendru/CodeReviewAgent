from __future__ import annotations

from backend.models.finding import FindingSeverity


def build_report(
    language: str,
    framework: str | None,
    bugs: list,
    security: list,
    performance: list,
    code_quality: list,
    tests: list,
    fixes: list,
    static_analysis: dict | None = None,
) -> dict:
    all_findings = list(bugs) + list(security) + list(performance) + list(code_quality)
    highest = "LOW"
    if any(item.severity == FindingSeverity.CRITICAL for item in all_findings):
        highest = "CRITICAL"
    elif any(item.severity == FindingSeverity.HIGH for item in all_findings):
        highest = "HIGH"
    elif any(item.severity == FindingSeverity.MEDIUM for item in all_findings):
        highest = "MEDIUM"

    return {
        "summary": {
            "language": language,
            "framework": framework,
            "files_reviewed": ["single-file review"],
            "lines_reviewed": 0,
            "review_duration_seconds": 0.0,
            "overall_risk_level": highest,
        },
        "static_analysis": static_analysis or {},
        "findings": {
            "bugs": bugs,
            "security": security,
            "performance": performance,
            "code_quality": code_quality,
            "tests": tests,
            "fixes": fixes,
        },
        "overall_explanation": "The review completed successfully. The platform detected likely issues based on static pattern analysis and language heuristics, and it categorized them so the user can prioritize remediation.",
    }
