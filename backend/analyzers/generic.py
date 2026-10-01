from backend.analyzers.base import LanguageAnalyzer


class GenericAnalyzer(LanguageAnalyzer):
    supported_language = "generic"

    @property
    def parser_available(self) -> bool:
        return False

    @property
    def formatter(self) -> str | None:
        return None

    @property
    def test_framework(self) -> str | None:
        return None

    def analyze(self, code: str, filename: str) -> dict:
        return {
            "language": self.supported_language,
            "filename": filename,
            "analysis": "Generic fallback review. Language-specific tooling unavailable.",
            "static_analysis_available": False,
        }
