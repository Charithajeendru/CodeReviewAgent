from fastapi import APIRouter

from backend.api.responses import success_response
from backend.config import settings
from backend.services.language_registry import list_language_capabilities

router = APIRouter()


@router.get("/files")
async def list_supported_files() -> dict:
    return success_response({
        "supported_extensions": sorted({
            extension
            for capability in list_language_capabilities()
            for extension in capability["extensions"]
        }),
    })


@router.get("/languages")
async def list_languages() -> dict:
    return success_response({"languages": list_language_capabilities()})


@router.get("/config")
async def get_public_config() -> dict:
    return success_response({
        "limits": {
            "max_code_chars": settings.max_code_chars,
            "max_project_files": settings.max_project_files,
            "max_project_file_bytes": settings.max_project_file_bytes,
            "max_project_total_bytes": settings.max_project_total_bytes,
            "max_project_path_chars": settings.max_project_path_chars,
            "max_project_filename_chars": settings.max_project_filename_chars,
            "max_project_context_chars": settings.max_project_context_chars,
            "max_project_related_file_chars": settings.max_project_related_file_chars,
        }
    })
