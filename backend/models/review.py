from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.finding import Finding


class LanguageInfo(BaseModel):
    language: str
    language_id: str = "unknown"
    version: str | None = None
    framework: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    detection_method: str = "unknown"
    file_extension: str | None = None
    static_analysis_available: bool = True
    notes: str = ""


class ReviewSummary(BaseModel):
    language: str | None = None
    framework: str | None = None
    files_reviewed: list[str] = Field(default_factory=list)
    lines_reviewed: int = 0
    review_duration_seconds: float = 0.0
    overall_risk_level: str = "LOW"


class ReviewResult(BaseModel):
    review_id: str
    language: LanguageInfo | None = None
    static_analysis: dict = Field(default_factory=dict)
    bugs: list[Finding] = Field(default_factory=list)
    security: list[Finding] = Field(default_factory=list)
    performance: list[Finding] = Field(default_factory=list)
    code_quality: list[Finding] = Field(default_factory=list)
    tests: list[dict] = Field(default_factory=list)
    fixes: list[dict] = Field(default_factory=list)
    summary: ReviewSummary | None = None
