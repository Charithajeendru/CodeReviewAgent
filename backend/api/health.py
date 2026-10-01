from fastapi import APIRouter

from backend.api.responses import success_response
from backend.config import settings
from backend.database.database import db

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    db.check_health()
    return success_response({
        "status": "healthy",
        "service": "CodeReviewAgent",
        "version": settings.app_version,
    })
