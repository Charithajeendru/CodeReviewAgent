from backend.models.project import ProjectFile
from backend.services.dependency_analyzer import analyze_dependencies
from backend.services.project_scanner import scan_project
from backend.services.relationship_analyzer import analyze_relationships


def test_project_scanner_classifies_files_and_excludes_generated_paths():
    files = [
        ProjectFile(path="src/main.py", content="import util"),
        ProjectFile(path="tests/test_main.py", content="from src import main"),
        ProjectFile(path="requirements.txt", content="fastapi==0.115.0"),
        ProjectFile(path="pyproject.toml", content="[project]\ndependencies = []"),
        ProjectFile(path="README.md", content="docs"),
        ProjectFile(path=".gitignore", content=".venv"),
        ProjectFile(path="node_modules/pkg/index.js", content="bad()"),
        ProjectFile(path="dist/generated.pyc", content="binary"),
    ]
    language_map = {"src/main.py": {"language": "Python", "language_id": "python"}}

    scan = scan_project("sample", files, language_map)

    assert scan["metadata"]["languages_used"] == ["Python"]
    assert scan["metadata"]["test_files"] == ["tests/test_main.py"]
    assert scan["metadata"]["dependency_files"] == ["pyproject.toml", "requirements.txt"]
    assert scan["metadata"]["readme_files"] == ["README.md"]
    assert scan["metadata"]["configuration_files"] == [".gitignore"]
    ignored = {item["path"] for item in scan["files"] if item["ignored"]}
    assert ignored == {"node_modules/pkg/index.js", "dist/generated.pyc"}
    assert scan["file_tree"]["type"] == "directory"


def test_project_scanner_includes_confident_content_detected_extensionless_source():
    file = ProjectFile(path="scripts/launcher", content="#!/usr/bin/env python3\nprint('hello')")
    scan = scan_project("script project", [file], {
        "scripts/launcher": {
            "language": "Python",
            "language_id": "python",
            "confidence": 98,
            "detection_method": "shebang",
        },
    })

    assert scan["source_files"] == ["scripts/launcher"]
    assert scan["metadata"]["languages_used"] == ["Python"]


def test_dependency_analysis_extracts_declared_python_and_javascript_dependencies():
    files = [
        ProjectFile(path="requirements.txt", content="fastapi>=0.100\n# comment\nhttpx==0.27"),
        ProjectFile(path="package.json", content='{"dependencies":{"react":"^18.0.0"},"devDependencies":{"vite":"^5"}}'),
        ProjectFile(path="node_modules/pkg/package.json", content='{"dependencies":{"fake":"1"}}'),
    ]

    result = analyze_dependencies(files)

    names = {(item["name"], item["version"]) for item in result["dependencies"]}
    assert ("fastapi", ">=0.100") in names
    assert ("httpx", "==0.27") in names
    assert ("react", "^18.0.0") in names
    assert ("fake", "1") not in names
    assert "React" in result["frameworks"]
    assert result["vulnerability_intelligence"] == "unavailable"


def test_dependency_analysis_extracts_lockfile_versions():
    files = [
        ProjectFile(path="package-lock.json", content='{"packages":{"node_modules/react":{"version":"18.2.0"}}}'),
        ProjectFile(path="Cargo.lock", content='[[package]]\nname = "serde"\nversion = "1.0.1"'),
        ProjectFile(path="Gemfile.lock", content="    rack (2.2.8)\n"),
    ]

    result = analyze_dependencies(files)
    declared = {(item["name"], item["version"]) for item in result["dependencies"]}

    assert ("react", "18.2.0") in declared
    assert ("serde", "1.0.1") in declared
    assert ("rack", "2.2.8") in declared


def test_dependency_analysis_supports_java_go_dotnet_and_swift_manifests():
    files = [
        ProjectFile(path="pom.xml", content="<project><dependencies><dependency><groupId>org.sample</groupId><artifactId>sample-lib</artifactId><version>1.2.3</version></dependency></dependencies></project>"),
        ProjectFile(path="go.mod", content="module example.com/app\n\nrequire example.com/lib v1.4.0"),
        ProjectFile(path="App.csproj", content='<Project><ItemGroup><PackageReference Include="Newtonsoft.Json" Version="13.0.1" /></ItemGroup></Project>'),
        ProjectFile(path="Package.swift", content='.package(url: "https://example.test/swift-collections.git", from: "1.0.0")'),
    ]

    result = analyze_dependencies(files)
    declared = {(item["ecosystem"], item["name"], item["version"]) for item in result["dependencies"]}

    assert ("maven", "sample-lib", "1.2.3") in declared
    assert ("go modules", "example.com/lib", "v1.4.0") in declared
    assert ("nuget", "Newtonsoft.Json", "13.0.1") in declared
    assert ("swift package manager", "swift-collections", None) in declared
    assert "Package.swift" in result["dependency_files"]


def test_relationship_analyzer_reports_python_internal_stdlib_and_unresolved_imports():
    files = [
        ProjectFile(path="src/main.py", content="import json\nfrom src import database\nimport missing_package"),
        ProjectFile(path="src/database.py", content="def load(): pass"),
    ]

    relationships = analyze_relationships(files, [])
    by_import = {item["import_name"]: item for item in relationships}

    assert by_import["json"]["resolution_status"] == "resolved_standard_library"
    assert by_import["src.database"]["resolution_status"] == "resolved_internal"
    assert by_import["missing_package"]["resolution_status"] == "unresolved"


def test_relationship_analyzer_handles_javascript_java_go_rust_and_cpp_imports():
    files = [
        ProjectFile(path="web/main.js", content="import util from './util.js'; const x = require('lodash');"),
        ProjectFile(path="web/util.js", content="export default 1;"),
        ProjectFile(path="java/Main.java", content="import java.util.List;\nimport app.Helper;"),
        ProjectFile(path="java/Helper.java", content="package app; class Helper {}"),
        ProjectFile(path="go/main.go", content='package main\nimport "fmt"'),
        ProjectFile(path="rust/main.rs", content="use crate::module::Thing;"),
        ProjectFile(path="native/main.cpp", content="#include \"util.hpp\"\n#include <vector>"),
        ProjectFile(path="native/util.hpp", content="#pragma once"),
    ]
    dependencies = []
    relationships = analyze_relationships(files, dependencies)
    by_source_and_name = {(item["source"], item["import_name"]): item for item in relationships}

    assert by_source_and_name[("web/main.js", "./util.js")]["resolution_status"] == "resolved_internal"
    assert by_source_and_name[("java/Main.java", "java.util.List")]["resolution_status"] == "resolved_standard_library"
    assert by_source_and_name[("java/Main.java", "app.Helper")]["resolution_status"] == "resolved_internal"
    assert by_source_and_name[("native/main.cpp", "util.hpp")]["resolution_status"] == "resolved_internal"
    assert by_source_and_name[("native/main.cpp", "vector")]["resolution_status"] == "resolved_system"


def test_go_module_and_rust_crate_imports_resolve_to_project_files():
    files = [
        ProjectFile(path="go.mod", content="module example.com/app\n"),
        ProjectFile(path="cmd/main.go", content='package main\nimport "example.com/app/pkg/mathutil"'),
        ProjectFile(path="pkg/mathutil/math.go", content="package mathutil"),
        ProjectFile(path="src/main.rs", content="use crate::module::Thing;"),
        ProjectFile(path="src/module.rs", content="pub struct Thing;"),
    ]

    relationships = analyze_relationships(files, [])
    by_import = {item["import_name"]: item for item in relationships}

    assert by_import["example.com/app/pkg/mathutil"]["resolution_status"] == "resolved_internal"
    assert by_import["example.com/app/pkg/mathutil"]["target"] == "pkg/mathutil/math.go"
    assert by_import["crate::module::Thing"]["resolution_status"] == "resolved_internal"
    assert by_import["crate::module::Thing"]["target"] == "src/module.rs"