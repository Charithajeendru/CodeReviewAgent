from backend.analyzers.base import LanguageAnalyzer


class JavaScriptAnalyzer(LanguageAnalyzer):
    supported_language = "JavaScript"

    @property
    def parser_available(self) -> bool:
        return True

    @property
    def formatter(self) -> str | None:
        return "prettier"

    @property
    def test_framework(self) -> str | None:
        return "Jest/Vitest"

    def static_analysis_commands(self, file_path: str) -> list[str]:
        return [f"node --check {file_path}"]
