from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.agents.bug_agent import analyze_bugs
from backend.agents.code_quality_agent import analyze_code_quality
from backend.agents.dependency_agent import analyze_project_dependencies
from backend.agents.language_agent import detect_language
from backend.agents.performance_agent import analyze_performance
from backend.agents.security_agent import analyze_security
from backend.models.agent_result import AgentResult
from backend.models.finding import Finding, FindingSeverity
from backend.models.project import ImportRelationship, ProjectDependency, ProjectFileRecord, ProjectReviewRequest
from backend.services.language_registry import get_language_capability
from backend.services.project_context import find_circular_dependencies, select_file_contexts
from backend.services.project_scanner import scan_project
from backend.services.relationship_analyzer import analyze_relationships
from backend.services.syntax_analysis import analyze_syntax

logger = logging.getLogger(__name__)


async def orchestrate_project_review(request: ProjectReviewRequest) -> dict[str, Any]:
    review_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    language_map: dict[str, dict[str, Any]] = {}
    for project_file in request.files:
        requested_language = project_file.language
        if requested_language == "auto":
            requested_language = request.language
        detection = detect_language(
            project_file.content,
            project_file.path,
            requested_language if requested_language != "auto" else None,
        )
        capability = get_language_capability(detection.language_id)
        language_map[project_file.path] = {
            "language": detection.language,
            "language_id": detection.language_id,
            "confidence": detection.confidence,
            "detection_method": detection.detection_method,
            "capabilities": capability and {
                "syntax_analysis_available": capability.syntax_analysis_available,
                "static_analysis_available": capability.static_analysis_available,
                "dependency_analysis_available": capability.dependency_analysis_available,
                "ai_analysis_available": capability.ai_analysis_available,
                "supported_agents": list(capability.supported_agents),
            } or {},
        }

    scan = scan_project(request.project_name, request.files, language_map, request.entry_file)
    dependency_report = analyze_project_dependencies(request.files)
    dependencies = dependency_report["dependencies"]
    relationships_payload = analyze_relationships(request.files, [
        ProjectDependency.model_validate(item) for item in dependencies
    ])
    relationships = [ImportRelationship.model_validate(item) for item in relationships_payload]
    metadata = {
        **scan["metadata"],
        "package_managers": dependency_report["package_managers"],
        "frameworks": dependency_report["frameworks"],
        "declared_dependency_count": len(dependencies),
    }
    metadata["circular_dependencies"] = find_circular_dependencies(relationships)
    framework = request.framework or (dependency_report["frameworks"][0] if dependency_report["frameworks"] else None)
    reviewable_paths = {
        item["path"] for item in scan["files"]
        if not item["ignored"] and item["kind"] in {"source", "test"}
    }
    selected_paths = request.selected_files or sorted(reviewable_paths)
    selected_paths = [path for path in selected_paths if path in reviewable_paths]
    contexts = select_file_contexts(
        review_id=review_id,
        project_id=project_id,
        project_name=request.project_name,
        files=request.files,
        file_records=[ProjectFileRecord.model_validate(item) for item in scan["files"]],
        file_tree=scan["file_tree"],
        language_map=language_map,
        metadata=metadata,
        dependencies=[ProjectDependency.model_validate(item) for item in dependencies],
        relationships=relationships,
        framework=framework,
        configuration=request.configuration,
        selected_files=selected_paths,
    )

    source_by_path = {item.path: item for item in request.files}
    findings: list[Finding] = []
    file_reviews: list[dict[str, Any]] = []
    file_errors: list[dict[str, Any]] = []
    syntax_tools: dict[str, dict[str, Any]] = {}
    failed_agents: set[str] = set()
    for path in selected_paths:
        project_file = source_by_path[path]
        context = contexts[path]
        language_info = language_map[path]
        per_file_findings: list[Finding] = []
        agent_functions = (
            ("Bug Agent", analyze_bugs),
            ("Security Agent", analyze_security),
            ("Performance Agent", analyze_performance),
            ("Code Quality Agent", analyze_code_quality),
        )
        file_agent_statuses = []
        for agent_name, agent_function in agent_functions:
            try:
                per_file_findings.extend(agent_function(project_file.content, path, language_info["language"], context))
                file_agent_statuses.append({"agent": agent_name, "status": "ok"})
            except Exception as exc:
                logger.error("%s failed for project file %s (%s)", agent_name, path, type(exc).__name__)
                failed_agents.add(agent_name)
                file_errors.append({
                    "file": path,
                    "agent": agent_name,
                    "message": "Agent analysis failed for this file.",
                })
                file_agent_statuses.append({"agent": agent_name, "status": "error"})
        try:
            syntax = analyze_syntax(path, project_file.content, language_info["language_id"])
            syntax_tools[syntax["tool"]] = {"tool": syntax["tool"], "status": syntax["status"]}
            for syntax_finding in syntax.get("findings", []):
                per_file_findings.append(Finding(
                    agent="Syntax Analyzer",
                    severity=FindingSeverity.HIGH,
                    confidence=1.0,
                    title="Syntax error",
                    description=syntax_finding["message"],
                    file=path,
                    line_start=syntax_finding.get("line"),
                    line_end=syntax_finding.get("line"),
                    evidence="Syntax parser rejected this source file.",
                    recommendation="Correct the syntax error and rerun the project review.",
                ))
        except Exception as exc:
            logger.error("Syntax analysis failed for project file %s (%s)", path, type(exc).__name__)
            file_errors.append({"file": path, "agent": "Syntax Analyzer", "message": "Syntax analysis failed for this file."})
            failed_agents.add("Syntax Analyzer")
        findings.extend(per_file_findings)
        file_reviews.append({
            "path": path,
            "language": language_info,
            "related_files": [item["path"] for item in context.related_files],
            "finding_count": len(per_file_findings),
            "agent_statuses": file_agent_statuses,
        })

    agent_results = [
        AgentResult(
            agent=name,
            status="warning" if name in failed_agents else "ok",
            message="Some file analyses failed." if name in failed_agents else "Deterministic heuristic analysis completed.",
        ).model_dump(mode="json")
        for name in ("Bug Agent", "Security Agent", "Performance Agent", "Code Quality Agent")
    ]
    agent_results.append(AgentResult(
        agent="Dependency Agent",
        status="ok",
        message="Supported manifests inspected; no vulnerability intelligence is configured.",
    ).model_dump(mode="json"))
    agent_results.append(AgentResult(
        agent="AI Analysis",
        status="unavailable",
        message="No AI provider is connected to project review.",
    ).model_dump(mode="json"))

    languages = sorted({item["language"] for path, item in language_map.items() if path in reviewable_paths and item["language_id"] != "unknown"})
    risk_levels = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    highest_risk = max(
        (item.severity.value for item in findings),
        key=lambda severity: risk_levels.get(severity, 0),
        default="LOW",
    )
    result = {
        "review_id": review_id,
        "project": {
            "project_id": project_id,
            "project_name": request.project_name,
            "framework": framework,
            "configuration": request.configuration,
        },
        "languages": [
            {
                "language": name,
                "language_id": next((item["language_id"] for item in language_map.values() if item["language"] == name), "unknown"),
                "files": [path for path in reviewable_paths if language_map[path]["language"] == name],
            }
            for name in languages
        ],
        "file_count": len(request.files),
        "agents": agent_results,
        "findings": [item.model_dump(mode="json") for item in findings],
        "summary": {
            "language": ", ".join(languages) if languages else "Unknown",
            "framework": framework,
            "files_reviewed": [item["path"] for item in file_reviews],
            "lines_reviewed": sum(len(source_by_path[path].content.splitlines()) for path in selected_paths),
            "overall_risk_level": highest_risk,
        },
        "relationships": relationships_payload,
        "dependencies": dependencies,
        "metadata": metadata,
        "file_tree": scan["file_tree"],
        "files": scan["files"],
        "file_reviews": file_reviews,
        "file_errors": file_errors,
        "partial": bool(file_errors),
        "analysis_capabilities": {
            "ai_analysis": "UNAVAILABLE",
            "heuristic_agents": "AVAILABLE",
            "static_analysis_tools": list(syntax_tools.values()),
            "syntax_analysis": "AVAILABLE_FOR_PYTHON_ONLY",
            "dependency_analysis": "SUPPORTED_MANIFESTS_ONLY",
        },
    }
    return result