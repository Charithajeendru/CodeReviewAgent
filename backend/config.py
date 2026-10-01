import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

load_dotenv()


class Settings(BaseModel):
    app_name: str = "CodeReview Agent"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    max_code_chars: int = int(os.getenv("MAX_CODE_CHARS", "250000"))
    max_batch_files: int = int(os.getenv("MAX_BATCH_FILES", "20"))
    max_batch_file_chars: int = int(os.getenv("MAX_BATCH_FILE_CHARS", os.getenv("MAX_CODE_CHARS", "250000")))
    max_batch_total_chars: int = int(os.getenv("MAX_BATCH_TOTAL_CHARS", "1000000"))
    max_request_bytes: int = int(os.getenv("MAX_REQUEST_BYTES", "5000000"))
    max_project_files: int = int(os.getenv("MAX_PROJECT_FILES", "100"))
    max_project_file_bytes: int = int(os.getenv("MAX_PROJECT_FILE_BYTES", "250000"))
    max_project_total_bytes: int = int(os.getenv("MAX_PROJECT_TOTAL_BYTES", "2000000"))
    max_project_path_chars: int = int(os.getenv("MAX_PROJECT_PATH_CHARS", "512"))
    max_project_filename_chars: int = int(os.getenv("MAX_PROJECT_FILENAME_CHARS", "255"))
    max_project_context_chars: int = int(os.getenv("MAX_PROJECT_CONTEXT_CHARS", "50000"))
    max_project_related_file_chars: int = int(os.getenv("MAX_PROJECT_RELATED_FILE_CHARS", "12000"))
    sqlite_database_path: str = os.getenv(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "data" / "reviews.db"),
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "stub")
    llm_model: str = os.getenv("LLM_MODEL", "stub-model")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
            if origin.strip()
        ]
    )

    @field_validator(
        "max_code_chars", "max_batch_files", "max_batch_file_chars", "max_batch_total_chars", "max_request_bytes",
        "max_project_files", "max_project_file_bytes", "max_project_total_bytes", "max_project_path_chars",
        "max_project_filename_chars",
        "max_project_context_chars", "max_project_related_file_chars",
    )
    @classmethod
    def validate_positive_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Resource limits must be positive integers.")
        return value


settings = Settings()
