from backend.analyzers.base import LanguageAnalyzer


class PythonAnalyzer(LanguageAnalyzer):
    supported_language = "Python"

    @property
    def parser_available(self) -> bool:
        return True

    @property
    def formatter(self) -> str | None:
        return "black"

    @property
    def test_framework(self) -> str | None:
        return "pytest"

    def static_analysis_commands(self, file_path: str) -> list[str]:
        return [f"python -m compileall {file_path}"]
