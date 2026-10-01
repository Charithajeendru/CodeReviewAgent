from __future__ import annotations

import re

from backend.models.finding import Finding, FindingSeverity
from backend.models.project import AnalysisContext


def analyze_performance(code: str, filename: str = "", language: str = "generic", context: AnalysisContext | None = None) -> list[Finding]:
    findings: list[Finding] = []
    lines = code.splitlines()

    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue

        lower = stripped.lower()
        if "for " in lower and "for " in lower and lower.count("for") >= 2:
            findings.append(
                Finding(
                    agent="Performance Agent",
                    severity=FindingSeverity.MEDIUM,
                    confidence=0.82,
                    title="Nested loops may cause quadratic or worse complexity",
                    description="Nested iteration over the same or related data can lead to O(n^2) or worse runtime depending on input size.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Consider reducing the number of iterations, precomputing indexes, or using a more efficient data structure for the workload.",
                )
            )
            continue

        if "append(" in lower and "for " in lower and "in range" in lower:
            findings.append(
                Finding(
                    agent="Performance Agent",
                    severity=FindingSeverity.LOW,
                    confidence=0.7,
                    title="Potential inefficient collection growth",
                    description="Repeated collection growth inside a loop may create unnecessary allocations and degrade throughput.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Use preallocated structures or a more efficient transformation strategy when the final size is known in advance.",
                )
            )
            continue

        if "sleep(" in lower or "time.sleep(" in lower:
            findings.append(
                Finding(
                    agent="Performance Agent",
                    severity=FindingSeverity.LOW,
                    confidence=0.75,
                    title="Blocking wait pattern",
                    description="A deliberate pause or blocking wait can slow down requests or processing and may indicate a poor pattern in a hot path.",
                    file=filename,
                    line_start=line_number,
                    line_end=line_number,
                    evidence=stripped,
                    recommendation="Use asynchronous patterns, queued jobs, or timeouts when the delay is part of a scheduled operation instead of a tight loop.",
                )
            )

    if context:
        database_call_pattern = re.compile(r"\.(?:execute|executemany|query|fetch|find)\s*\(", re.IGNORECASE)
        own_count = sum(bool(database_call_pattern.search(line)) for line in lines)
        related_count = sum(
            bool(database_call_pattern.search(line))
            for related in context.related_files
            for line in related["content"].splitlines()
        )
        if own_count and related_count and own_count + related_count >= 3:
            findings.append(Finding(
                agent="Performance Agent",
                severity=FindingSeverity.LOW,
                confidence=0.55,
                title="Repeated database-operation patterns across related files",
                description="Multiple database-like operations were found in directly related files; whether they form a hot-path bottleneck is not determined by this heuristic.",
                file=filename,
                evidence=f"{own_count} operation(s) in this file and {related_count} in directly related files",
                recommendation="Profile the connected call path and consider batching or caching only if measurements show repeated work.",
            ))

    return findings
