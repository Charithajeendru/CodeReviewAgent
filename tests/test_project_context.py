from backend.agents.bug_agent import analyze_bugs
from backend.agents.code_quality_agent import analyze_code_quality
from backend.agents.performance_agent import analyze_performance
from backend.agents.security_agent import analyze_security
from backend.config import settings
from backend.models.project import AnalysisContext, ImportRelationship, ProjectFile, ProjectFileRecord
from backend.models.project import ProjectDependency
from backend.services.project_context import find_circular_dependencies, select_file_contexts
from backend.services.syntax_analysis import analyze_syntax


def test_context_selection_includes_only_direct_files_and_respects_character_limits(monkeypatch):
    monkeypatch.setattr(settings, "max_project_context_chars", 8)
    monkeypatch.setattr(settings, "max_project_related_file_chars", 8)
    files = [
        ProjectFile(path="src/a.py", content="import b"),
        ProjectFile(path="src/b.py", content="b" * 20),
        ProjectFile(path="src/c.py", content="c" * 20),
    ]
    languages = {path: {"language": "Python", "language_id": "python"} for path in ("src/a.py", "src/b.py", "src/c.py")}
    relationship = ImportRelationship(
        source="src/a.py", target="src/b.py", import_name="b", relationship="import",
        resolution_status="resolved_internal", resolution="test",
    )
    contexts = select_file_contexts(
        review_id="review", project_id="project", project_name="sample", files=files,
        file_records=[ProjectFileRecord(path=path, kind="source", language="Python", language_id="python") for path in languages],
        file_tree={}, language_map=languages, metadata={}, dependencies=[], relationships=[relationship],
        framework=None, configuration={}, selected_files=["src/a.py"],
    )

    assert [item["path"] for item in contexts["src/a.py"].related_files] == ["src/b.py"]
    assert len(contexts["src/a.py"].related_files[0]["content"]) == 8


def test_context_selection_scopes_relationships_and_dependencies_to_target_imports():
    files = [ProjectFile(path="main.js", content="import 'lodash'"), ProjectFile(path="lib.js", content="export const x = 1")]
    relationships = [
        ImportRelationship(source="main.js", target="lodash", import_name="lodash", relationship="import", resolution_status="resolved_dependency", resolution="manifest"),
        ImportRelationship(source="lib.js", target="unknown", import_name="unknown", relationship="require", resolution_status="unresolved", resolution="not in manifest"),
    ]
    dependencies = [
        ProjectDependency(ecosystem="npm", name="lodash", version="4.17.21", manifest="package.json"),
        ProjectDependency(ecosystem="npm", name="axios", version="1.0.0", manifest="package.json"),
    ]
    language_map = {"main.js": {"language": "JavaScript", "language_id": "javascript"}}
    contexts = select_file_contexts(
        review_id="r", project_id="p", project_name="sample", files=files,
        file_records=[], file_tree={}, language_map=language_map, metadata={}, dependencies=dependencies,
        relationships=relationships, framework=None, configuration={}, selected_files=["main.js"],
    )

    assert [item.import_name for item in contexts["main.js"].relationships] == ["lodash"]
    assert [item.name for item in contexts["main.js"].dependencies] == ["lodash"]


def test_cycle_detection_and_code_quality_agent_report_import_cycles():
    relationships = [
        ImportRelationship(source="a.py", target="b.py", import_name="b", relationship="import", resolution_status="resolved_internal", resolution="test"),
        ImportRelationship(source="b.py", target="a.py", import_name="a", relationship="import", resolution_status="resolved_internal", resolution="test"),
    ]
    cycles = find_circular_dependencies(relationships)
    context = AnalysisContext(
        review_id="r", project_id="p", project_name="sample", source_code="x = 1", filename="a.py",
        language="Python", project_metadata={"circular_dependencies": cycles}, relationships=relationships,
    )

    findings = analyze_code_quality("x = 1", "a.py", "Python", context)

    assert cycles == [["a.py", "b.py"]]
    assert any(item.title == "Circular project import relationship" for item in findings)


def test_context_aware_agents_report_limited_cross_file_candidates():
    relationship = ImportRelationship(
        source="web/route.js", target="web/handler.js", import_name="./handler.js", relationship="import",
        resolution_status="resolved_internal", resolution="test",
    )
    context = AnalysisContext(
        review_id="r", project_id="p", project_name="sample", source_code="", filename="web/route.js",
        language="JavaScript", related_files=[{"path": "web/handler.js", "content": "eval(value)\ndb.fetch()"}],
        relationships=[relationship],
    )
    security = analyze_security("const value = request.body", "web/route.js", "JavaScript", context)
    performance = analyze_performance("db.execute()\ndb.query()", "web/route.js", "JavaScript", context)

    assert any("cross-file" in finding.title.lower() for finding in security)
    assert any("across related files" in finding.title for finding in performance)


def test_bug_agent_reports_unresolved_relative_project_import():
    relationship = ImportRelationship(
        source="src/main.js", target="./missing.js", import_name="./missing.js", relationship="import",
        resolution_status="unresolved", resolution="not supplied",
    )
    context = AnalysisContext(
        review_id="r", project_id="p", project_name="sample", source_code="", filename="src/main.js",
        language="JavaScript", relationships=[relationship],
    )

    findings = analyze_bugs("import './missing.js'", "src/main.js", "JavaScript", context)

    assert any(finding.title == "Unresolved relative project import" for finding in findings)


def test_python_ast_syntax_analysis_reports_errors_without_execution():
    valid = analyze_syntax("src/main.py", "print('ok')", "python")
    invalid = analyze_syntax("src/broken.py", "def broken(:\n pass", "python")
    unavailable = analyze_syntax("src/main.js", "console.log('ok')", "javascript")

    assert valid["status"] == "AVAILABLE"
    assert invalid["status"] == "FINDINGS"
    assert invalid["findings"][0]["file"] == "src/broken.py"
    assert unavailable["status"] in {"UNAVAILABLE", "AVAILABLE_NOT_INVOKED"}