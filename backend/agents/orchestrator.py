from __future__ import annotations

import time
import uuid
import logging

from backend.agents.bug_agent import analyze_bugs
from backend.agents.code_quality_agent import analyze_code_quality
from backend.agents.fix_agent import propose_fix
from backend.agents.language_agent import detect_language
from backend.agents.performance_agent import analyze_performance
from backend.agents.report_agent import build_report
from backend.agents.security_agent import analyze_security
from backend.agents.test_agent import generate_tests
from backend.models.review import ReviewResult, ReviewSummary
from backend.services.static_analysis import analyze_static

logger = logging.getLogger(__name__)


async def orchestrate_review(code: str, filename: str = "", user_language: str | None = None) -> ReviewResult:
    start = time.time()
    language_info = detect_language(code, filename, user_language)
    static_result = analyze_static(code, language_info.language, filename)

    bugs = analyze_bugs(code, filename, language_info.language)
    security = analyze_security(code, filename, language_info.language)
    performance = analyze_performance(code, filename, language_info.language)
    code_quality = analyze_code_quality(code, filename, language_info.language)
    tests = generate_tests(code, filename, language_info.language)
    fix = propose_fix(code, filename, language_info.language, bugs + security + performance + code_quality)

    report = build_report(
        language_info.language,
        language_info.framework,
        bugs,
        security,
        performance,
        code_quality,
        tests,
        [fix],
        static_analysis=static_result,
    )

    summary = ReviewSummary(
        language=language_info.language,
        framework=language_info.framework,
        files_reviewed=[filename or "input"],
        lines_reviewed=len(code.splitlines()),
        review_duration_seconds=round(time.time() - start, 3),
        overall_risk_level=report["summary"]["overall_risk_level"],
    )

    return ReviewResult(
        review_id=str(uuid.uuid4()),
        language=language_info,
        static_analysis=static_result,
        bugs=bugs,
        security=security,
        performance=performance,
        code_quality=code_quality,
        tests=tests,
        fixes=[fix],
        summary=summary,
    )


async def orchestrate_review_batch(files: list[dict]) -> dict:
    if not files:
        return {
            "review_id": str(uuid.uuid4()),
            "language": "unknown",
            "summary": {
                "language": "unknown",
                "framework": None,
                "files_reviewed": [],
                "lines_reviewed": 0,
                "overall_risk_level": "LOW",
            },
            "reviews": [],
            "bugs": [],
            "security": [],
            "performance": [],
            "code_quality": [],
            "tests": [],
            "fixes": [],
        }

    review_results = []
    flattened_bugs: list[dict] = []
    flattened_security: list[dict] = []
    flattened_performance: list[dict] = []
    flattened_quality: list[dict] = []
    flattened_tests: list[dict] = []
    flattened_fixes: list[dict] = []
    files_reviewed: list[str] = []
    detected_languages: list[str] = []
    file_errors: list[dict] = []
    total_lines = 0
    risk_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    for index, item in enumerate(files):
        source_index = item.get("source_index", index)
        filename = item.get("filename") or item.get("name") or "input"
        try:
            review = await orchestrate_review(
                item.get("code", ""),
                filename,
                item.get("language") or None,
            )
        except Exception as exc:
            logger.error("Review analysis failed for batch item %s (%s)", source_index, type(exc).__name__)
            file_errors.append({
                "index": source_index,
                "filename": filename,
                "message": "Analysis failed for this file.",
            })
            continue
        review_results.append(review.model_dump(mode="json"))
        if review.language:
            detected_languages.append(review.language.language)
        files_reviewed.append(review.summary.files_reviewed[0] if review.summary else (item.get("filename") or item.get("name") or "input"))
        total_lines += review.summary.lines_reviewed if review.summary else 0
        flattened_bugs.extend(review.bugs)
        flattened_security.extend(review.security)
        flattened_performance.extend(review.performance)
        flattened_quality.extend(review.code_quality)
        flattened_tests.extend(review.tests)
        flattened_fixes.extend(review.fixes)

    aggregate_risk = "LOW"
    for level in risk_levels:
        if any(
            item.severity == level if hasattr(item, "severity") else False
            for item in flattened_bugs + flattened_security + flattened_performance + flattened_quality
        ):
            aggregate_risk = level
            break

    unique_languages = set(detected_languages)
    batch_summary = {
        "language": "mixed" if len(unique_languages) > 1 else (detected_languages[0] if detected_languages else "unknown"),
        "framework": None,
        "files_reviewed": files_reviewed,
        "lines_reviewed": total_lines,
        "overall_risk_level": aggregate_risk,
    }

    return {
        "review_id": str(uuid.uuid4()),
        "language": batch_summary["language"],
        "summary": batch_summary,
        "reviews": review_results,
        "bugs": flattened_bugs,
        "security": flattened_security,
        "performance": flattened_performance,
        "code_quality": flattened_quality,
        "tests": flattened_tests,
        "fixes": flattened_fixes,
        "file_errors": file_errors,
        "partial": bool(file_errors),
    }
