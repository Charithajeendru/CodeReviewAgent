from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from backend.models.project import ProjectFile, ProjectFileRecord
from backend.services.language_registry import LANGUAGES_BY_EXTENSION


IGNORED_DIRECTORIES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "target", "build", "dist",
}
DEPENDENCY_FILES = {
    "requirements.txt", "pipfile", "pipfile.lock", "pyproject.toml", "package.json",
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "pom.xml",
    "build.gradle", "build.gradle.kts", "go.mod", "go.sum", "cargo.toml", "cargo.lock",
    "composer.json", "composer.lock", "gemfile", "gemfile.lock", "package.swift",
}
CONFIG_FILES = {
    "tsconfig.json", ".gitignore", ".dockerignore", "dockerfile", "makefile",
}
SOURCE_DIR_NAMES = {"src", "source", "app", "lib"}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs"}
ENTRY_POINT_NAMES = {
    "main.py", "__main__.py", "app.py", "manage.py", "index.js", "index.ts", "main.js",
    "main.ts", "main.go", "main.rs", "program.cs", "main.c", "main.cpp",
}
GENERATED_SUFFIXES = {".pyc", ".class", ".o", ".obj", ".dll", ".exe", ".so", ".dylib", ".map"}


def classify_project_file(path: str) -> tuple[str, bool]:
    posix_path = PurePosixPath(path)
    lowered_parts = {part.casefold() for part in posix_path.parts}
    basename = posix_path.name.casefold()
    suffix = posix_path.suffix.casefold()

    if lowered_parts & IGNORED_DIRECTORIES or suffix in GENERATED_SUFFIXES or basename.endswith(".min.js"):
        return "generated", True
    if basename in DEPENDENCY_FILES or basename.endswith(".csproj"):
        return "dependency", False
    if basename.startswith("readme") or suffix in {".md", ".rst", ".adoc"}:
        return "documentation", False
    if any(part in TEST_DIR_NAMES for part in lowered_parts) or _looks_like_test_file(basename):
        return "test", False
    if basename in CONFIG_FILES or suffix in {".toml", ".yaml", ".yml", ".ini", ".cfg", ".json", ".xml"}:
        return "configuration", False
    if suffix in LANGUAGES_BY_EXTENSION:
        return "source", False
    return "other", False


def _looks_like_test_file(basename: str) -> bool:
    return (
        basename.startswith("test_")
        or basename.endswith("_test.py")
        or ".test." in basename
        or ".spec." in basename
    )


def scan_project(
    project_name: str,
    files: list[ProjectFile],
    language_map: dict[str, dict[str, Any]],
    entry_file: str | None = None,
) -> dict[str, Any]:
    records: list[ProjectFileRecord] = []
    source_files: list[str] = []
    test_files: list[str] = []
    dependency_files: list[str] = []
    configuration_files: list[str] = []
    documentation_files: list[str] = []
    readme_files: list[str] = []
    entry_points: list[str] = []
    source_directories: set[str] = set()
    languages: set[str] = set()
    tree: dict[str, Any] = {"name": project_name, "type": "directory", "children": {}}

    for project_file in files:
        path = project_file.path
        kind, ignored = classify_project_file(path)
        language = language_map.get(path, {}).get("language", "Unknown")
        language_id = language_map.get(path, {}).get("language_id", "unknown")
        if kind == "other" and language_id != "unknown":
            kind = "source"
        if ignored:
            language, language_id = "Unknown", "unknown"
        record = ProjectFileRecord(path=path, language=language, language_id=language_id, kind=kind, ignored=ignored)
        records.append(record)
        if not ignored:
            if kind == "source":
                source_files.append(path)
                languages.add(language)
                if len(PurePosixPath(path).parts) > 1:
                    first_part = PurePosixPath(path).parts[0]
                    if first_part.casefold() in SOURCE_DIR_NAMES:
                        source_directories.add(first_part)
            elif kind == "test":
                test_files.append(path)
            elif kind == "dependency":
                dependency_files.append(path)
            elif kind == "configuration":
                configuration_files.append(path)
            elif kind == "documentation":
                documentation_files.append(path)
                if PurePosixPath(path).name.casefold().startswith("readme"):
                    readme_files.append(path)
        if not ignored and PurePosixPath(path).name.casefold() in ENTRY_POINT_NAMES:
            entry_points.append(path)

        cursor = tree
        parts = PurePosixPath(path).parts
        for part in parts[:-1]:
            cursor = cursor["children"].setdefault(part, {"name": part, "type": "directory", "children": {}})
        cursor["children"][parts[-1]] = {
            "name": parts[-1],
            "type": "file",
            "path": path,
            "kind": kind,
            "ignored": ignored,
        }

    def freeze(node: dict[str, Any]) -> dict[str, Any]:
        if node["type"] == "directory":
            node["children"] = [freeze(child) for _, child in sorted(node["children"].items(), key=lambda item: item[0].casefold())]
        return node

    selected_entry_points = [entry_file] if entry_file else sorted(entry_points)
    metadata = {
        "languages_used": sorted(languages),
        "language_map": {path: language_map[path] for path in source_files},
        "dependency_files": sorted(dependency_files),
        "entry_points": selected_entry_points,
        "entry_point_detection": "explicit" if entry_file else "filename_convention",
        "test_files": sorted(test_files),
        "source_directories": sorted(source_directories),
        "configuration_files": sorted(configuration_files),
        "documentation_files": sorted(documentation_files),
        "readme_files": sorted(readme_files),
        "file_count": len(files),
        "source_file_count": len(source_files),
        "ignored_file_count": sum(record.ignored for record in records),
    }
    return {
        "file_tree": freeze(tree),
        "files": [record.model_dump(mode="json") for record in records],
        "source_files": source_files,
        "metadata": metadata,
    }