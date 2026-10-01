from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from typing import Any

from backend.models.project import ProjectDependency, ProjectFile
from backend.services.project_scanner import classify_project_file


_FRAMEWORKS = {
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask", "starlette": "Starlette",
    "react": "React", "next": "Next.js", "vue": "Vue", "angular": "Angular", "express": "Express",
    "spring-boot-starter-web": "Spring", "org.springframework.boot": "Spring",
}


def analyze_dependencies(files: list[ProjectFile]) -> dict[str, Any]:
    dependencies: list[ProjectDependency] = []
    manifests: list[str] = []
    package_managers: set[str] = set()
    declared_names: set[str] = set()

    for project_file in files:
        basename = PurePosixPath(project_file.path).name.casefold()
        extension = PurePosixPath(project_file.path).suffix.casefold()
        content = project_file.content
        kind, ignored = classify_project_file(project_file.path)
        if ignored or kind != "dependency":
            continue
        parsed: list[tuple[str, str | None]] = []
        ecosystem = _manifest_ecosystem(basename, extension)
        if ecosystem is None:
            continue
        manifests.append(project_file.path)
        package_managers.add(ecosystem)
        try:
            parsed = _parse_manifest(basename, extension, content)
        except (ValueError, TypeError, json.JSONDecodeError, ET.ParseError, tomllib.TOMLDecodeError):
            continue
        for name, version in parsed:
            if not name:
                continue
            dependencies.append(ProjectDependency(
                ecosystem=ecosystem,
                name=name,
                version=version,
                manifest=project_file.path,
            ))
            declared_names.add(_normalize_package_name(name))

    unique: dict[tuple[str, str, str], ProjectDependency] = {}
    for dependency in dependencies:
        key = (dependency.ecosystem, dependency.name.casefold(), dependency.manifest)
        unique[key] = dependency
    frameworks = sorted({
        framework
        for dependency in unique.values()
        if (framework := _FRAMEWORKS.get(_normalize_package_name(dependency.name)))
    })
    return {
        "dependencies": [item.model_dump(mode="json") for item in unique.values()],
        "dependency_files": sorted(set(manifests)),
        "package_managers": sorted(package_managers),
        "frameworks": frameworks,
        "declared_names": sorted(declared_names),
        "vulnerability_intelligence": "unavailable",
    }


def _manifest_ecosystem(basename: str, extension: str) -> str | None:
    if basename in {"requirements.txt", "pyproject.toml", "pipfile", "pipfile.lock"}:
        return "python"
    if basename in {"package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml"}:
        return "npm"
    if basename == "pom.xml" or basename.startswith("build.gradle"):
        return "maven" if basename == "pom.xml" else "gradle"
    if basename in {"go.mod", "go.sum"}:
        return "go modules"
    if basename in {"cargo.toml", "cargo.lock"}:
        return "cargo"
    if basename in {"composer.json", "composer.lock"}:
        return "composer"
    if basename in {"gemfile", "gemfile.lock"}:
        return "bundler"
    if basename == "package.swift":
        return "swift package manager"
    if extension == ".csproj":
        return "nuget"
    return None


def _parse_manifest(basename: str, extension: str, content: str) -> list[tuple[str, str | None]]:
    if basename == "requirements.txt":
        results = []
        for line in content.splitlines():
            stripped = line.split("#", 1)[0].strip()
            match = re.match(r"([A-Za-z0-9_.-]+)\s*(?:\[.*?\])?\s*(.*)$", stripped)
            if match and not stripped.startswith(("-", "http:", "https:")):
                results.append((match.group(1), match.group(2).strip() or None))
        return results
    if basename == "pyproject.toml":
        document = tomllib.loads(content)
        project = document.get("project", {})
        dependencies = list(project.get("dependencies", []))
        for optional in project.get("optional-dependencies", {}).values():
            dependencies.extend(optional)
        return [_split_requirement(value) for value in dependencies]
    if basename == "pipfile":
        results = []
        for line in content.splitlines():
            match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*=\s*[\"']([^\"']+)[\"']", line)
            if match:
                results.append((match.group(1), match.group(2)))
        return results
    if basename == "pipfile.lock":
        document = json.loads(content)
        results = []
        for section in ("default", "develop"):
            for name, value in document.get(section, {}).items():
                version = value.get("version") if isinstance(value, dict) else None
                results.append((name, version))
        return results
    if basename == "package.json":
        document = json.loads(content)
        results = []
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            results.extend((name, str(version)) for name, version in document.get(section, {}).items())
        return results
    if basename in {"package-lock.json", "npm-shrinkwrap.json"}:
        document = json.loads(content)
        results = []
        for path, details in document.get("packages", {}).items():
            if path.startswith("node_modules/"):
                results.append((path.removeprefix("node_modules/"), details.get("version")))
        if not results:
            for name, details in document.get("dependencies", {}).items():
                results.append((name, details.get("version") if isinstance(details, dict) else None))
        return results
    if basename == "yarn.lock":
        results = []
        for block in re.split(r"\n\s*\n", content):
            lines = block.splitlines()
            if not lines:
                continue
            version = next((match.group(1) for line in lines[1:] if (match := re.match(r"\s+version\s+[\"']?([^\"'\s]+)", line))), None)
            if not version:
                continue
            selectors = lines[0].rstrip(":").split(",")
            for selector in selectors:
                selector = selector.strip().strip("\"'")
                if "@" in selector:
                    name = selector.rsplit("@", 1)[0]
                    results.append((name, version))
        return results
    if basename == "pnpm-lock.yaml":
        return [
            (match.group(1), match.group(2))
            for match in re.finditer(r"(?m)^\s{2,}['\"]?/?(@?[^\s:'\"]+?)@([^\s:'\"]+)['\"]?:\s*$", content)
        ]
    if basename == "pom.xml":
        root = ET.fromstring(content)
        results = []
        for dependency in root.iter():
            if dependency.tag.rsplit("}", 1)[-1] != "dependency":
                continue
            fields = {child.tag.rsplit("}", 1)[-1]: (child.text or "").strip() for child in dependency}
            if fields.get("artifactId"):
                results.append((fields["artifactId"], fields.get("version") or None))
        return results
    if basename.startswith("build.gradle"):
        return [
            (match.group(1), match.group(2))
            for match in re.finditer(
                r"\b(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*\(?\s*[\"'][^:\"']+:([^:\"']+):([^\"']+)[\"']",
                content,
            )
        ]
    if basename == "go.mod":
        results = re.findall(r"(?m)^\s*([\w./-]+)\s+(v[\w.+-]+)", content)
        results.extend(re.findall(r"(?m)^\s*require\s+([\w./-]+)\s+(v[\w.+-]+)\s*$", content))
        return results
    if basename == "go.sum":
        return [(name, version.removesuffix("/go.mod")) for name, version in re.findall(r"(?m)^([^\s]+)\s+(v[^\s]+)\s+", content)]
    if basename == "cargo.toml":
        document = tomllib.loads(content)
        results = []
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            for name, value in document.get(section, {}).items():
                version = value if isinstance(value, str) else value.get("version") if isinstance(value, dict) else None
                results.append((name, version))
        return results
    if basename == "cargo.lock":
        document = tomllib.loads(content)
        return [(item.get("name", ""), item.get("version")) for item in document.get("package", [])]
    if basename == "composer.json":
        document = json.loads(content)
        results = []
        for section in ("require", "require-dev"):
            results.extend((name, str(version)) for name, version in document.get(section, {}).items() if name != "php")
        return results
    if basename == "composer.lock":
        document = json.loads(content)
        results = []
        for section in ("packages", "packages-dev"):
            results.extend((item.get("name", ""), item.get("version")) for item in document.get(section, []))
        return results
    if extension == ".csproj":
        root = ET.fromstring(content)
        results = []
        for item in root.iter():
            if item.tag.rsplit("}", 1)[-1] == "PackageReference":
                results.append((item.attrib.get("Include", ""), item.attrib.get("Version")))
        return results
    if basename == "gemfile":
        return re.findall(r"(?m)^\s*gem\s+[\"']([^\"']+)[\"'](?:,\s*[\"']([^\"']+)[\"'])?", content)
    if basename == "gemfile.lock":
        return re.findall(r"(?m)^\s{4}([A-Za-z0-9_.-]+) \(([^)]+)\)", content)
    if basename == "package.swift":
        return [(name, None) for name in re.findall(r"\.package\s*\(\s*(?:url:\s*)?[\"'][^\"']*/([^/\"']+?)(?:\.git)?[\"']", content)]
    return []


def _split_requirement(value: str) -> tuple[str, str | None]:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(.*)", value)
    return (match.group(1), match.group(2).strip() or None) if match else (value, None)


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()