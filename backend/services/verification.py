from __future__ import annotations

from typing import Callable

from pydantic import ValidationError

from backend.agents.bug_agent import analyze_bugs
from backend.agents.code_quality_agent import analyze_code_quality
from backend.agents.performance_agent import analyze_performance
from backend.agents.security_agent import analyze_security
from backend.models.finding import Finding
from backend.models.project import AnalysisContext, ImportRelationship, ProjectDependency
from backend.models.workflow import FixResult, GeneratedTestResult, VerificationCheck, VerificationResult
from backend.services.language_registry import resolve_language
from backend.services.syntax_analysis import analyze_syntax


_AGENT_ANALYZERS: dict[str, Callable] = {
    "Bug Agent": analyze_bugs,
    "Security Agent": analyze_security,
    "Performance Agent": analyze_performance,
    "Code Quality Agent": analyze_code_quality,
}


def reanalyze_fix(fix: FixResult) -> tuple[str, bool | None, str]:
    original_finding = Finding.model_validate(fix.finding)
    analyzer = _AGENT_ANALYZERS.get(original_finding.agent)
    if analyzer is None:
        return "UNAVAILABLE", None, "No matching deterministic analyzer is available for this finding agent."
    context_data = fix.project_context
    relationships = []
    for item in context_data.get("relationships", []):
        try:
            relationships.append(ImportRelationship.model_validate(item))
        except (ValidationError, TypeError):
            continue
    dependencies = []
    for item in context_data.get("dependencies", []):
        try:
            dependencies.append(ProjectDependency.model_validate(item))
        except (ValidationError, TypeError):
            continue
    project = context_data.get("project") or {}
    context = AnalysisContext(
        review_id="fix-reanalysis",
        project_id=str(project.get("project_id", "")),
        project_name=str(project.get("project_name", "Fix re-analysis")),
        source_code=fix.fixed_code,
        filename=fix.file,
        language=fix.language,
        framework=fix.framework,
        project_metadata=context_data.get("metadata", {}),
        dependencies=dependencies,
        relationships=relationships,
        related_files=[item.model_dump(mode="json") for item in fix.related_files],
        selected_files=[fix.file],
    )
    findings = analyzer(fix.fixed_code, fix.file, fix.language, context)
    remains = any(
        item.title == original_finding.title
        or (item.severity == original_finding.severity and item.evidence == original_finding.evidence)
        for item in findings
    )
    if remains:
        return "FAILED", True, "The same heuristic finding remains in the proposed source."
    return "PASSED", False, "The existing heuristic no longer reports this finding in the proposed source."


def verify_fix(fix: FixResult, generated_test: GeneratedTestResult | None = None) -> VerificationResult:
    checks: list[VerificationCheck] = []
    lifecycle = list(fix.finding_lifecycle)
    if fix.status != "GENERATED":
        checks.append(VerificationCheck(name="fix_generation", status="FAILED", details="No generated fix is available."))
        return VerificationResult(
            finding_id=fix.finding_id,
            fix_id=fix.fix_id,
            test_id=generated_test.test_id if generated_test else None,
            status="UNABLE_TO_VERIFY",
            checks=checks,
            explanation="Verification cannot proceed without a generated fix.",
            finding_lifecycle=lifecycle,
        )
    checks.append(VerificationCheck(name="fix_generation", status="PASSED", details="A proposed fix exists; it has not been applied to user files."))

    language = resolve_language(fix.language)
    language_id = language.id if language else "unknown"
    syntax = analyze_syntax(fix.file, fix.fixed_code, language_id)
    if syntax["status"] == "FINDINGS":
        checks.append(VerificationCheck(name="syntax", status="FAILED", details="Proposed source contains syntax errors."))
    elif syntax["status"] == "AVAILABLE":
        checks.append(VerificationCheck(name="syntax", status="PASSED", details="Safe syntax parser accepted the proposed source."))
    else:
        checks.append(VerificationCheck(name="syntax", status="UNAVAILABLE", details="No safe syntax parser is available for this language."))

    finding_status, remains, finding_details = reanalyze_fix(fix)
    checks.append(VerificationCheck(name="finding_reanalysis", status=finding_status, details=finding_details))
    if "REANALYZED" not in lifecycle:
        lifecycle.append("REANALYZED")

    if generated_test and generated_test.status == "GENERATED":
        checks.append(VerificationCheck(name="test_generation", status="PASSED", details="A targeted test artifact was generated."))
    else:
        checks.append(VerificationCheck(name="test_generation", status="UNAVAILABLE", details="No usable generated test is attached."))
    checks.append(VerificationCheck(
        name="test_execution",
        status="UNAVAILABLE",
        details="EXECUTION_UNAVAILABLE: no secure sandbox is configured; tests were not run.",
    ))
    checks.append(VerificationCheck(
        name="static_analysis",
        status="UNAVAILABLE",
        details="No dedicated static-analysis tool was run during verification.",
    ))

    syntax_failed = any(check.name == "syntax" and check.status == "FAILED" for check in checks)
    if syntax_failed:
        status = "NOT_VERIFIED"
        lifecycle.append("NOT_VERIFIED")
        explanation = "The proposed source failed syntax validation. No code or test execution occurred."
    elif remains is True:
        status = "NOT_VERIFIED"
        lifecycle.append("NOT_VERIFIED")
        explanation = "The proposed change did not pass all safe re-analysis checks. No code or test execution occurred."
    elif remains is None:
        status = "UNABLE_TO_VERIFY"
        explanation = "The finding could not be re-analyzed by a matching agent. No code or test execution occurred."
    else:
        status = "PARTIALLY_VERIFIED"
        lifecycle.append("PARTIALLY_VERIFIED")
        explanation = "Safe syntax/re-analysis checks support the proposal, but tests and static analysis were not executed. This is not a verified fix."

    return VerificationResult(
        finding_id=fix.finding_id,
        fix_id=fix.fix_id,
        test_id=generated_test.test_id if generated_test else None,
        status=status,
        checks=checks,
        explanation=explanation,
        finding_lifecycle=list(dict.fromkeys(lifecycle)),
    )
