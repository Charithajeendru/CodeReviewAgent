from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from backend.config import settings
from backend.models.finding import Finding
from backend.services.language_registry import resolve_language


class RelatedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: StrictStr
    content: StrictStr

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = value.strip()
        if (
            not path
            or path.startswith(("/", "\\"))
            or "\\" in path
            or ":" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or len(path) > settings.max_project_path_chars
        ):
            raise ValueError("Related file path must be a safe relative path.")
        return path

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > settings.max_project_related_file_chars:
            raise ValueError("Related source exceeds the configured context size limit.")
        return value


class GenerateFixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding: Finding
    source_code: StrictStr
    filename: StrictStr
    language: StrictStr
    framework: StrictStr | None = None
    project_context: dict[str, Any] = Field(default_factory=dict)
    related_files: list[RelatedSource] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_related_context_size(self) -> GenerateFixRequest:
        total_bytes = sum(len(item.content.encode("utf-8")) for item in self.related_files)
        if total_bytes > settings.max_project_context_chars:
            raise ValueError("Related source exceeds the configured total context limit.")
        return self

    @field_validator("source_code")
    @classmethod
    def validate_source_size(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source code cannot be empty.")
        if len(value) > settings.max_code_chars:
            raise ValueError("Source code exceeds the configured size limit.")
        return value

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        path = value.strip()
        if (
            not path or len(path) > settings.max_project_path_chars
            or path.startswith(("/", "\\")) or "\\" in path or ":" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
        ):
            raise ValueError("Filename must be a safe relative project path.")
        return path

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        capability = resolve_language(value)
        if capability is None:
            raise ValueError("Language is not supported.")
        return capability.name


class GenerateTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework: StrictStr | None = None


class VerifyFixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: uuid.UUID | None = None


class ProposedFileChange(BaseModel):
    file: str
    original_code: str
    proposed_code: str
    diff: str


class FixResult(BaseModel):
    fix_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    finding_id: str
    status: Literal["GENERATED", "FAILED", "NOT_APPLICABLE", "NO_CHANGE"]
    file: str
    language: str
    framework: str | None = None
    original_code: str
    fixed_code: str
    diff: str
    files_changed: list[str] = Field(default_factory=list)
    file_changes: list[ProposedFileChange] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(ge=0, le=100)
    validation_status: Literal["VALIDATED", "VALIDATION_UNAVAILABLE", "INVALID", "NO_CHANGE"]
    validation_message: str
    finding: dict[str, Any]
    project_context: dict[str, Any] = Field(default_factory=dict)
    related_files: list[RelatedSource] = Field(default_factory=list)
    finding_lifecycle: list[str] = Field(default_factory=lambda: ["DETECTED"])
    created_at: str | None = None


class GeneratedTestResult(BaseModel):
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    finding_id: str
    fix_id: str
    language: str
    framework: str
    status: Literal["GENERATED", "FAILED", "UNAVAILABLE"]
    test_code: str = ""
    purpose: str = ""
    expected_behavior: str = ""
    validation_status: Literal["VALIDATED", "VALIDATION_UNAVAILABLE", "INVALID"]
    execution_status: Literal["EXECUTION_UNAVAILABLE"] = "EXECUTION_UNAVAILABLE"
    finding_lifecycle: list[str] = Field(default_factory=lambda: ["DETECTED", "FIX_PROPOSED", "FIX_VALIDATED", "TEST_GENERATED"])
    created_at: str | None = None


class VerificationCheck(BaseModel):
    name: str
    status: Literal["PASSED", "FAILED", "UNAVAILABLE"]
    details: str = ""


class VerificationResult(BaseModel):
    verification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    finding_id: str
    fix_id: str
    test_id: str | None = None
    status: Literal["VERIFIED", "PARTIALLY_VERIFIED", "NOT_VERIFIED", "UNABLE_TO_VERIFY"]
    checks: list[VerificationCheck]
    explanation: str
    finding_lifecycle: list[str] = Field(default_factory=list)
    created_at: str | None = None