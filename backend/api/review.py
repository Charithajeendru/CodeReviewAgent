from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator

from backend.agents.fix_agent import propose_fix
from backend.agents.language_agent import detect_language
from backend.agents.orchestrator import orchestrate_review, orchestrate_review_batch
from backend.agents.project_orchestrator import orchestrate_project_review
from backend.agents.test_agent import generate_tests
from backend.config import settings
from backend.database.database import db
from backend.api.responses import success_response
from backend.models.project import ProjectReviewRequest

router = APIRouter()


def enforce_single_code_limit(code: str) -> None:
    if len(code) > settings.max_code_chars:
        raise HTTPException(status_code=413, detail="Code exceeds the configured size limit.")


SUPPORTED_LANGUAGES = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "c": "C",
    "c++": "C++",
    "c#": "C#",
    "go": "Go",
    "rust": "Rust",
    "php": "PHP",
    "ruby": "Ruby",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "sql": "SQL",
    "shell": "Shell",
    "powershell": "PowerShell",
    "html": "HTML",
    "css": "CSS",
    "generic": "Generic",
}


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: StrictStr = "auto"
    filename: StrictStr = "example.py"
    code: StrictStr = ""

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized in {"auto", "auto detect"}:
            return "auto"
        if normalized not in SUPPORTED_LANGUAGES:
            raise ValueError("Language is not supported.")
        return SUPPORTED_LANGUAGES[normalized]

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        filename = value.strip()
        if (
            not filename
            or len(filename) > 255
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or ":" in filename
            or any(ord(character) < 32 or ord(character) == 127 for character in filename)
        ):
            raise ValueError("Filename must be a safe filename, not a filesystem path.")
        return filename

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Code cannot be empty.")
        return value


class DetectLanguageRequest(ReviewRequest):
    pass


class BatchReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[Any] = Field(default_factory=list)


@router.post("/review")
async def review_code(payload: ReviewRequest) -> dict:
    enforce_single_code_limit(payload.code)

    result = await orchestrate_review(payload.code, payload.filename, payload.language if payload.language != "auto" else None)
    result_payload = result.model_dump(mode="json")
    db.save_review(result.review_id, result_payload)
    return success_response(db.get_review(result.review_id))


@router.post("/review/batch")
async def review_batch(payload: BatchReviewRequest) -> dict:
    if not payload.files:
        raise HTTPException(status_code=400, detail="At least one file is required for a batch review.")
    if len(payload.files) > settings.max_batch_files:
        raise HTTPException(status_code=413, detail="Batch contains more files than the configured limit.")

    total_chars = sum(
        len(item.get("code", ""))
        for item in payload.files
        if isinstance(item, dict) and isinstance(item.get("code", ""), str)
    )
    if total_chars > settings.max_batch_total_chars:
        raise HTTPException(status_code=413, detail="Batch source exceeds the configured total size limit.")

    valid_files: list[dict[str, Any]] = []
    file_errors: list[dict[str, Any]] = []
    for index, item in enumerate(payload.files):
        try:
            if not isinstance(item, dict):
                raise ValueError("Each batch file must be an object.")
            request = ReviewRequest.model_validate(item)
            if len(request.code) > settings.max_batch_file_chars:
                raise ValueError("File exceeds the configured per-file size limit.")
            valid_files.append({
                "filename": request.filename,
                "language": request.language if request.language != "auto" else None,
                "code": request.code,
                "source_index": index,
            })
        except ValidationError as exc:
            file_errors.append({"index": index, "errors": exc.errors(include_input=False, include_context=False)})
        except ValueError as exc:
            file_errors.append({"index": index, "errors": [{"message": str(exc)}]})

    if not valid_files:
        raise HTTPException(
            status_code=422,
            detail={"message": "No valid files were provided.", "file_errors": file_errors},
        )

    batch = await orchestrate_review_batch(valid_files)
    file_errors.extend(batch.get("file_errors", []))
    batch["file_errors"] = file_errors
    batch["partial"] = bool(file_errors)
    if batch.get("review_id"):
        db.save_review(batch["review_id"], batch)
        batch = db.get_review(batch["review_id"])
        batch["file_errors"] = file_errors
        batch["partial"] = bool(file_errors)
    return success_response(batch)


@router.post("/reviews/project")
async def review_project(payload: ProjectReviewRequest) -> dict:
    result = await orchestrate_project_review(payload)
    db.save_review(result["review_id"], result)
    return success_response(db.get_review(result["review_id"]))


@router.get("/review/{review_id}")
async def get_review(review_id: uuid.UUID) -> dict:
    item = db.get_review(str(review_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return success_response(item)


@router.get("/reviews")
async def list_reviews(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> dict:
    return success_response({"reviews": db.list_reviews(limit=limit, offset=offset), "limit": limit, "offset": offset})


@router.post("/detect-language")
async def detect_language_endpoint(payload: DetectLanguageRequest) -> dict:
    enforce_single_code_limit(payload.code)
    info = detect_language(payload.code, payload.filename, payload.language)
    return success_response(info.model_dump(mode="json"))


@router.post("/generate-tests")
async def generate_tests_endpoint(payload: ReviewRequest) -> dict:
    enforce_single_code_limit(payload.code)
    tests = generate_tests(payload.code, payload.filename, payload.language)
    return success_response({"language": payload.language, "tests": tests})


@router.post("/fix")
async def fix_endpoint(payload: ReviewRequest) -> dict:
    enforce_single_code_limit(payload.code)
    fix = propose_fix(payload.code, payload.filename, payload.language, [])
    return success_response(fix)
