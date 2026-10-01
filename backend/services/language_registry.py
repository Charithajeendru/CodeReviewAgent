from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageCapability:
    id: str
    name: str
    extensions: tuple[str, ...]
    filename_patterns: tuple[str, ...]
    comment_syntax: tuple[str, ...]
    syntax_analysis_available: bool = False
    static_analysis_available: bool = False
    dependency_analysis_available: bool = False
    ai_analysis_available: bool = False
    supported_agents: tuple[str, ...] = (
        "bug-heuristics",
        "security-heuristics",
        "performance-heuristics",
        "code-quality-heuristics",
    )


_AGENTS = (
    "bug-heuristics",
    "security-heuristics",
    "performance-heuristics",
    "code-quality-heuristics",
)

_CAPABILITIES = (
    LanguageCapability("python", "Python", (".py", ".pyw", ".pyi"), (), ("#",), True, False, True, False, _AGENTS),
    LanguageCapability("javascript", "JavaScript", (".js", ".jsx", ".mjs", ".cjs"), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("typescript", "TypeScript", (".ts", ".tsx", ".mts", ".cts"), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("java", "Java", (".java",), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("c", "C", (".c", ".h"), (), ("//", "/* */"), False, False, False, False, _AGENTS),
    LanguageCapability("cpp", "C++", (".cc", ".cpp", ".cxx", ".hh", ".hpp", ".hxx"), (), ("//", "/* */"), False, False, False, False, _AGENTS),
    LanguageCapability("csharp", "C#", (".cs",), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("go", "Go", (".go",), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("rust", "Rust", (".rs",), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("php", "PHP", (".php",), (), ("//", "#", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("ruby", "Ruby", (".rb", ".rake", ".gemspec"), (), ("#",), False, False, True, False, _AGENTS),
    LanguageCapability("kotlin", "Kotlin", (".kt", ".kts"), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("swift", "Swift", (".swift",), (), ("//", "/* */"), False, False, True, False, _AGENTS),
    LanguageCapability("sql", "SQL", (".sql",), (), ("--", "/* */"), False, False, False, False, _AGENTS),
    LanguageCapability("html", "HTML", (".html", ".htm"), (), ("<!-- -->",), False, False, False, False, _AGENTS),
    LanguageCapability("css", "CSS", (".css",), (), ("/* */",), False, False, False, False, _AGENTS),
    LanguageCapability("shell", "Shell", (".sh", ".bash", ".zsh", ".fish"), (".bashrc", ".zshrc"), ("#",), False, False, False, False, _AGENTS),
    LanguageCapability("powershell", "PowerShell", (".ps1", ".psm1", ".psd1"), (), ("#", "<# #>"), False, False, False, False, _AGENTS),
)

LANGUAGES_BY_ID = {capability.id: capability for capability in _CAPABILITIES}
LANGUAGES_BY_NAME = {capability.name.casefold(): capability for capability in _CAPABILITIES}
LANGUAGES_BY_EXTENSION = {
    extension: capability
    for capability in _CAPABILITIES
    for extension in capability.extensions
}
LANGUAGES_BY_FILENAME = {
    pattern.casefold(): capability
    for capability in _CAPABILITIES
    for pattern in capability.filename_patterns
}

_ALIASES = {
    "c++": "cpp",
    "c#": "csharp",
    "c-sharp": "csharp",
    "js": "javascript",
    "ts": "typescript",
    "sh": "shell",
    "bash": "shell",
    "ps1": "powershell",
}


def resolve_language(value: str) -> LanguageCapability | None:
    normalized = value.strip().casefold()
    language_id = _ALIASES.get(normalized, normalized)
    return LANGUAGES_BY_ID.get(language_id) or LANGUAGES_BY_NAME.get(normalized)


def get_language_capability(language_id: str) -> LanguageCapability | None:
    return LANGUAGES_BY_ID.get(language_id.strip().casefold())


def list_language_capabilities() -> list[dict]:
    return [
        {
            "id": capability.id,
            "name": capability.name,
            "extensions": list(capability.extensions),
            "filename_patterns": list(capability.filename_patterns),
            "comment_syntax": list(capability.comment_syntax),
            "syntax_analysis_available": capability.syntax_analysis_available,
            "static_analysis_available": capability.static_analysis_available,
            "dependency_analysis_available": capability.dependency_analysis_available,
            "ai_analysis_available": capability.ai_analysis_available,
            "supported_agents": list(capability.supported_agents),
        }
        for capability in _CAPABILITIES
    ]