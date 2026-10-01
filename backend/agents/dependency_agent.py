from __future__ import annotations

from backend.models.project import ProjectFile
from backend.services.dependency_analyzer import analyze_dependencies


def analyze_project_dependencies(files: list[ProjectFile]) -> dict:
    return analyze_dependencies(files)