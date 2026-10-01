from __future__ import annotations

import ast
import re
import sys
from pathlib import PurePosixPath

from backend.models.project import ImportRelationship, ProjectDependency, ProjectFile
from backend.services.project_scanner import classify_project_file


_EXTENSIONS = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".java", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".kt", ".swift")


def analyze_relationships(files: list[ProjectFile], dependencies: list[ProjectDependency]) -> list[dict]:
    analyzable_files = [
        file for file in files
        if not classify_project_file(file.path)[1] and classify_project_file(file.path)[0] in {"source", "test"}
    ]
    source_paths = {file.path for file in analyzable_files}
    dependency_names = {dependency.name.casefold() for dependency in dependencies}
    module_paths: dict[str, str] = {}
    for path in source_paths:
        pure = PurePosixPath(path)
        module_paths[pure.stem.casefold()] = path
        normalized = str(pure.with_suffix("")).replace("/", ".").casefold()
        module_paths[normalized] = path
        source_content = next(item.content for item in analyzable_files if item.path == path)
        if pure.suffix.casefold() == ".java":
            package = re.search(r"(?m)^\s*package\s+([\w.]+)\s*;", source_content)
            if package:
                module_paths[f"{package.group(1)}.{pure.stem}".casefold()] = path
    for project_file in files:
        if PurePosixPath(project_file.path).name.casefold() == "go.mod":
            module_match = re.search(r"(?m)^\s*module\s+([^\s]+)", project_file.content)
            if module_match:
                module_paths["__go_module__"] = module_match.group(1).casefold()

    relationships: list[ImportRelationship] = []
    for file in analyzable_files:
        suffix = PurePosixPath(file.path).suffix.casefold()
        if suffix not in _EXTENSIONS:
            continue
        for import_name, kind in _extract_imports(file.content, suffix):
            target, status, resolution = _resolve_import(
                import_name, kind, file.path, suffix, source_paths, module_paths, dependency_names,
            )
            relationships.append(ImportRelationship(
                source=file.path,
                target=target,
                import_name=import_name,
                relationship=kind,
                resolution_status=status,
                resolution=resolution,
            ))
    return [item.model_dump(mode="json") for item in relationships]


def _extract_imports(content: str, suffix: str) -> list[tuple[str, str]]:
    if suffix == ".py":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        imports: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((alias.name, "import") for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                if node.names and node.names[0].name != "*":
                    imports.extend((f"{module}.{alias.name}", "import-from") for alias in node.names)
                else:
                    imports.append((module, "import-from"))
        return imports
    if suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}:
        patterns = (
            (r"\bimport\s+(?:[^;\n]*?\s+from\s+)?[\"']([^\"']+)[\"']", "import"),
            (r"\bexport\s+[^;\n]*?\s+from\s+[\"']([^\"']+)[\"']", "export-from"),
            (r"\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)", "require"),
        )
        return _unique_matches(content, patterns)
    if suffix == ".java":
        return _unique_matches(content, ((r"(?m)^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", "import"),))
    if suffix == ".go":
        return _unique_matches(content, ((r"\bimport\s+(?:\(\s*)?[\"']([^\"']+)[\"']", "import"),))
    if suffix == ".rs":
        return _unique_matches(content, ((r"(?m)^\s*use\s+([\w:]+)", "use"), (r"(?m)^\s*mod\s+(\w+)\s*;", "module")))
    if suffix in {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp"}:
        return _unique_matches(content, (
            (r"(?m)^\s*#\s*include\s*<([^>]+)>", "system-include"),
            (r"(?m)^\s*#\s*include\s*\"([^\"]+)\"", "include"),
        ))
    return []


def _unique_matches(content: str, patterns: tuple[tuple[str, str], ...]) -> list[tuple[str, str]]:
    results = []
    seen = set()
    for pattern, kind in patterns:
        for match in re.finditer(pattern, content):
            value = match.group(1)
            if value not in seen:
                results.append((value, kind))
                seen.add(value)
    return results


def _resolve_import(import_name: str, kind: str, source: str, suffix: str, source_paths: set[str], module_paths: dict[str, str], dependency_names: set[str]) -> tuple[str, str, str]:
    normalized = import_name.strip()
    if suffix == ".py":
        if normalized and all(part.startswith(".") for part in normalized.split(".")):
            module = normalized
            level = len(module) - len(module.lstrip("."))
            tail = module[level:].replace(".", "/")
            parent = PurePosixPath(source).parent
            base_parts = parent.parts[: max(0, len(parent.parts) - level + 1)]
            candidate = "/".join((*base_parts, tail))
            resolved = _match_python_path(candidate, source_paths)
            if resolved:
                return resolved, "resolved_internal", "Matched a project Python module."
        else:
            resolved = module_paths.get(normalized.replace(".", "/").split("/")[-1].casefold()) or module_paths.get(normalized.casefold())
            if resolved:
                return resolved, "resolved_internal", "Matched a project Python module."
            top = normalized.split(".")[0]
            if top in sys.stdlib_module_names:
                return normalized, "resolved_standard_library", "Matched Python standard library module name."
    elif kind == "system-include":
        return normalized, "resolved_system", "System include detected; it was not resolved to a submitted project file."
    elif normalized.startswith(("./", "../")) or suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"} and normalized.startswith("."):
        parent = PurePosixPath(source).parent
        candidate = PurePosixPath(parent, normalized)
        resolved = _match_extensions(str(candidate), source_paths)
        if resolved:
            return resolved, "resolved_internal", "Matched a relative project file."
    elif suffix == ".java" and normalized.startswith(("java.", "javax.", "jakarta.")):
        return normalized, "resolved_standard_library", "Import uses a standard Java namespace."
    elif suffix in {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp"}:
        resolved = _match_extensions(str(PurePosixPath(source).parent / normalized), source_paths)
        if resolved:
            return resolved, "resolved_internal", "Matched a project include file."
        return normalized, "unresolved", "Include detected; no matching project file was supplied."
    else:
        if suffix == ".rs" and normalized.startswith("crate::"):
            rust_module = normalized.removeprefix("crate::").split("::", 1)[0].casefold()
            if rust_module in module_paths:
                return module_paths[rust_module], "resolved_internal", "Matched a project Rust module."
        module_name = normalized.rsplit(".", 1)[-1].casefold()
        if module_name in module_paths:
            return module_paths[module_name], "resolved_internal", "Matched a project module by filename."
        if suffix == ".java" and normalized.casefold() in module_paths:
            return module_paths[normalized.casefold()], "resolved_internal", "Matched a project Java package and class."
        if suffix == ".go":
            module_decl = module_paths.get("__go_module__")
            if module_decl and normalized.startswith(module_decl):
                suffix_path = normalized.removeprefix(module_decl).strip("/")
                candidate = next((path for path in source_paths if str(PurePosixPath(path).parent).endswith(suffix_path)), None)
                if candidate:
                    return candidate, "resolved_internal", "Matched a project Go package directory."
        top = normalized.split("/")[0].split(".")[0].casefold()
        if top in dependency_names or any(top == name.split("/")[-1].casefold() for name in dependency_names):
            return normalized, "resolved_dependency", "Matched a declared project dependency."
        if suffix in {".java", ".go", ".rs"} and not normalized.startswith(("crate::", "self::", "super::")):
            return normalized, "unresolved", "Import detected; no matching project file or declared dependency was found."
    return normalized, "unresolved", "Import detected; no matching project file or declared dependency was found."


def _match_python_path(candidate: str, source_paths: set[str]) -> str | None:
    dotted = candidate.replace("/", ".").strip(".")
    direct = next((path for path in source_paths if path.removesuffix(".py").replace("/", ".").casefold() == dotted.casefold()), None)
    if direct:
        return direct
    return next((path for path in source_paths if path.casefold() in {f"{candidate}.py".casefold(), f"{candidate}/__init__.py".casefold()}), None)


def _match_extensions(candidate: str, source_paths: set[str]) -> str | None:
    normalized = str(PurePosixPath(candidate))
    possible = [normalized, *(normalized + extension for extension in _EXTENSIONS)]
    possible.extend(f"{normalized}/index{extension}" for extension in _EXTENSIONS)
    lookup = {path.casefold(): path for path in source_paths}
    return next((lookup[path.casefold()] for path in possible if path.casefold() in lookup), None)