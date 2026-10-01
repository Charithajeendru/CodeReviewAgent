from backend.agents.language_agent import detect_language
from backend.services.language_registry import list_language_capabilities


def test_registry_has_requested_languages_and_extensions():
    capabilities = list_language_capabilities()
    names = {item["name"] for item in capabilities}

    assert names == {
        "Python", "JavaScript", "TypeScript", "Java", "C", "C++", "C#", "Go", "Rust",
        "PHP", "Ruby", "Kotlin", "Swift", "SQL", "HTML", "CSS", "Shell", "PowerShell",
    }
    extensions = {extension for item in capabilities for extension in item["extensions"]}
    assert {".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".php", ".rb", ".kt", ".swift", ".sql", ".html", ".css", ".sh", ".ps1"} <= extensions


def test_language_capabilities_do_not_claim_ai_or_general_static_analysis():
    capabilities = list_language_capabilities()

    assert not any(item["ai_analysis_available"] for item in capabilities)
    assert not any(item["static_analysis_available"] for item in capabilities)
    assert next(item for item in capabilities if item["id"] == "python")["syntax_analysis_available"] is True


def test_detection_prefers_explicit_language_then_extension_then_shebang():
    explicit = detect_language("#!/bin/bash\necho hi", "main.py", "Go")
    extension = detect_language("unknown", "module.ts")
    shebang = detect_language("#!/usr/bin/env python3\nprint('ok')", "script")

    assert (explicit.language, explicit.confidence, explicit.detection_method) == ("Go", 100, "explicit")
    assert (extension.language, extension.confidence, extension.detection_method) == ("TypeScript", 100, "extension")
    assert (shebang.language, shebang.confidence, shebang.detection_method) == ("Python", 98, "shebang")


def test_detection_uses_content_heuristics_and_returns_unknown_for_ambiguous_code():
    content = detect_language("public class Example { }", "source")
    unknown = detect_language("value = thing", "mystery.unknown")

    assert content.language == "Java"
    assert content.detection_method == "content"
    assert content.confidence >= 70
    assert unknown.language == "Unknown"
    assert unknown.confidence == 0