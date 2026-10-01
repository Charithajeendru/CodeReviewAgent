from __future__ import annotations

from abc import ABC, abstractmethod


class LanguageAnalyzer(ABC):
    supported_language: str = "generic"

    @property
    @abstractmethod
    def parser_available(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def formatter(self) -> str | None:
        raise NotImplementedError

    @property
    @abstractmethod
    def test_framework(self) -> str | None:
        raise NotImplementedError

    def static_analysis_commands(self, file_path: str) -> list[str]:
        return []

    def dependency_info(self) -> dict:
        return {}

    def analyze(self, code: str, filename: str) -> dict:
        return {
            "language": self.supported_language,
            "filename": filename,
            "analysis": "No native static analysis tool available; AI review fallback used.",
            "static_analysis_available": self.parser_available,
        }
