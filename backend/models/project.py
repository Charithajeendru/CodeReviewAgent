from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictStr, computed_field, field_validator, model_validator

from backend.config import settings
from backend.services.language_registry import resolve_language


class ProjectFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: StrictStr
    content: StrictStr
    language: StrictStr = "auto"
    size: int | None = Field(default=None, ge=0)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = value.strip()
        components = path.split("/")
        if (
            not path
            or len(path) > settings.max_project_path_chars
            or path.startswith("/")
            or "\\" in path
            or ":" in path
            or any(part in {"", ".", ".."} for part in components)
            or any(ord(character) < 32 or ord(character) == 127 for character in path)
        ):
            raise ValueError("Project file paths must be safe relative POSIX paths.")
        if len(components[-1]) > settings.max_project_filename_chars:
            raise ValueError("Project filename exceeds the configured filename limit.")
        return path

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized in {"", "auto", "auto detect"}:
            return "auto"
        capability = resolve_language(normalized)
        if capability is None:
            raise ValueError("Language is not supported.")
        return capability.name

    @model_validator(mode="after")
    def validate_size(self) -> ProjectFile:
        content_size = len(self.content.encode("utf-8"))
        if content_size > settings.max_project_file_bytes:
            raise ValueError("Project file exceeds the configured per-file size limit.")
        if self.size is not None and self.size != content_size:
            raise ValueError("Provided file size does not match the UTF-8 content size.")
        return self

    @computed_field
    @property
    def filename(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @computed_field
    @property
    def content_size(self) -> int:
        return len(self.content.encode("utf-8"))


class ProjectReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: StrictStr = Field(min_length=1, max_length=100)
    files: list[ProjectFile] = Field(min_length=1)
    entry_file: StrictStr | None = None
    language: StrictStr = "auto"
    framework: StrictStr | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    selected_files: list[StrictStr] | None = None

    @field_validator("project_name")
    @classmethod
    def normalize_project_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Project name cannot be empty.")
        return name

    @field_validator("language")
    @classmethod
    def normalize_project_language(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized in {"", "auto", "auto detect"}:
            return "auto"
        capability = resolve_language(normalized)
        if capability is None:
            raise ValueError("Language is not supported.")
        return capability.name

    @field_validator("entry_file")
    @classmethod
    def validate_entry_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return ProjectFile(path=value, content="").path

    @model_validator(mode="after")
    def validate_project_files(self) -> ProjectReviewRequest:
        if len(self.files) > settings.max_project_files:
            raise ValueError("Project contains more files than the configured limit.")
        canonical_paths = [item.path.casefold() for item in self.files]
        if len(set(canonical_paths)) != len(canonical_paths):
            raise ValueError("Project contains duplicate file paths.")
        if sum(item.content_size for item in self.files) > settings.max_project_total_bytes:
            raise ValueError("Project exceeds the configured total size limit.")
        paths = {item.path for item in self.files}
        if self.entry_file and self.entry_file not in paths:
            raise ValueError("Entry file must match a file included in the project.")
        if self.selected_files:
            unknown = set(self.selected_files) - paths
            if unknown:
                raise ValueError("Selected files must match project file paths.")
        return self


class ProjectDependency(BaseModel):
    ecosystem: str
    name: str
    version: str | None = None
    manifest: str
    vulnerability_status: str = "Dependency detected; vulnerability intelligence unavailable."


class ImportRelationship(BaseModel):
    source: str
    target: str
    import_name: str
    relationship: str = "detected"
    resolution_status: str
    resolution: str


class ProjectFileRecord(BaseModel):
    path: str
    language: str = "Unknown"
    language_id: str = "unknown"
    kind: str
    ignored: bool = False


class AnalysisContext(BaseModel):
    review_id: str
    project_id: str
    project_name: str
    source_code: str
    filename: str
    language: str
    framework: str | None = None
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    files: list[ProjectFileRecord] = Field(default_factory=list)
    file_tree: dict[str, Any] = Field(default_factory=dict)
    language_map: dict[str, dict[str, Any]] = Field(default_factory=dict)
    dependencies: list[ProjectDependency] = Field(default_factory=list)
    relationships: list[ImportRelationship] = Field(default_factory=list)
    related_files: list[dict[str, str]] = Field(default_factory=list)
    selected_files: list[str] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)
    entry_points: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)

    @classmethod
    def new_ids(cls) -> tuple[str, str]:
        return str(uuid.uuid4()), str(uuid.uuid4())


ProjectAnalysisContext = AnalysisContext