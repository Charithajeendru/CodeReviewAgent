from __future__ import annotations

from typing import Any

from backend.config import settings
from backend.models.project import AnalysisContext, ImportRelationship, ProjectDependency, ProjectFile, ProjectFileRecord


def select_file_contexts(
    *,
    review_id: str,
    project_id: str,
    project_name: str,
    files: list[ProjectFile],
    file_records: list[ProjectFileRecord],
    file_tree: dict[str, Any],
    language_map: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
    dependencies: list[ProjectDependency],
    relationships: list[ImportRelationship],
    framework: str | None,
    configuration: dict[str, Any],
    selected_files: list[str],
) -> dict[str, AnalysisContext]:
    source_by_path = {item.path: item.content for item in files}
    outgoing: dict[str, list[ImportRelationship]] = {}
    incoming: dict[str, list[ImportRelationship]] = {}
    for relationship in relationships:
        if relationship.resolution_status != "resolved_internal":
            continue
        outgoing.setdefault(relationship.source, []).append(relationship)
        incoming.setdefault(relationship.target, []).append(relationship)

    contexts = {}
    maximum_context_chars = settings.max_project_context_chars
    for path in selected_files:
        capability = language_map.get(path, {})
        candidates: dict[str, str] = {}
        target_edges = [edge for edge in relationships if edge.source == path or edge.target == path]
        for edge in outgoing.get(path, []) + incoming.get(path, []):
            related_path = edge.target if edge.source == path else edge.source
            if related_path in source_by_path and related_path != path:
                candidates[related_path] = source_by_path[related_path]
        imported_names = {
            edge.import_name.casefold()
            for edge in target_edges
            if edge.resolution_status in {"resolved_dependency", "unresolved"}
        }
        related_dependencies = [
            dependency for dependency in dependencies
            if _dependency_matches_import(dependency.name, imported_names)
        ]
        related_files = []
        consumed = 0
        for related_path in sorted(candidates):
            content = candidates[related_path]
            remaining = maximum_context_chars - consumed
            if remaining <= 0:
                break
            selected_content = content[: min(settings.max_project_related_file_chars, remaining)]
            related_files.append({"path": related_path, "content": selected_content})
            consumed += len(selected_content)

        language = capability.get("language", "Unknown")
        contexts[path] = AnalysisContext(
            review_id=review_id,
            project_id=project_id,
            project_name=project_name,
            source_code=source_by_path[path],
            filename=path,
            language=language,
            framework=framework,
            project_metadata=metadata,
            files=file_records,
            file_tree=file_tree,
            language_map=language_map,
            dependencies=related_dependencies,
            relationships=target_edges,
            related_files=related_files,
            selected_files=selected_files,
            configuration=configuration,
            entry_points=metadata.get("entry_points", []),
            test_files=metadata.get("test_files", []),
        )
    return contexts


def _dependency_matches_import(name: str, imports: set[str]) -> bool:
    normalized_name = name.casefold().replace("_", "-")
    for imported_name in imports:
        normalized_import = imported_name.replace("_", "-")
        if normalized_import == normalized_name or normalized_import.startswith(f"{normalized_name}/"):
            return True
        top_level_name = normalized_import.split(".", 1)[0].split("/", 1)[0]
        if top_level_name == normalized_name:
            return True
        if normalized_name.startswith("@") and normalized_name in normalized_import:
            return True
    return False


def find_circular_dependencies(relationships: list[ImportRelationship]) -> list[list[str]]:
    graph: dict[str, set[str]] = {}
    for item in relationships:
        if item.resolution_status == "resolved_internal":
            graph.setdefault(item.source, set()).add(item.target)

    cycles: set[tuple[str, ...]] = set()
    for start in graph:
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack:
            current, path = stack.pop()
            for target in graph.get(current, set()):
                if target == start and len(path) > 1:
                    cycle = path[:]
                    rotations = [tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle))]
                    cycles.add(min(rotations))
                elif target not in path and len(path) < len(graph):
                    stack.append((target, path + [target]))
    return [list(cycle) for cycle in sorted(cycles)]