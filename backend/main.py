import logging
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from backend.api.files import router as files_router
from backend.api.health import router as health_router
from backend.api.review import router as review_router
from backend.api.workflow import router as workflow_router
from backend.api.responses import error_response, success_response
from backend.config import settings

logger = logging.getLogger(__name__)


class RequestTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_request_bytes: int) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_request_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content=error_response("PAYLOAD_TOO_LARGE", "Request body exceeds the configured size limit."),
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_request_bytes:
                    raise RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            response = JSONResponse(
                status_code=413,
                content=error_response("PAYLOAD_TOO_LARGE", "Request body exceeds the configured size limit."),
            )
            await response(scope, receive, send)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent AI code review platform for multiple languages.",
)
app.add_middleware(RequestSizeLimitMiddleware, max_request_bytes=settings.max_request_bytes)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"location": list(error.get("loc", ())), "message": error.get("msg", "Invalid value.")}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_response("VALIDATION_ERROR", "Request validation failed.", details),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_by_status = {
        400: "BAD_REQUEST",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
    }
    message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
    details = exc.detail if isinstance(exc.detail, (dict, list)) else None
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=error_response(code_by_status.get(exc.status_code, "REQUEST_ERROR"), message, details),
    )


@app.exception_handler(sqlite3.Error)
async def database_exception_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    logger.error("Database operation failed (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content=error_response("DATABASE_ERROR", "The review store is temporarily unavailable."),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled API exception (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content=error_response("INTERNAL_SERVER_ERROR", "An unexpected server error occurred."),
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.allowed_origins == ["*"] else settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")


@app.get("/")
def root() -> dict:
    return success_response({
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    })
