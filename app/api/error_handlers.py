"""API error handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.utils.exceptions import (
    APIError,
    CacheError,
    ExternalServiceError,
    MediaSearchError,
    RateLimitError,
    ValidationError,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register custom error handlers with the FastAPI app."""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        logger.warning("validation_error", message=exc.message, field=exc.field)
        return JSONResponse(
            status_code=400,
            content={
                "error": "validation_error",
                "message": exc.message,
                "field": exc.field,
                "details": exc.details,
            },
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(request: Request, exc: RateLimitError) -> JSONResponse:
        logger.warning("rate_limit_exceeded", service=exc.service)
        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=429,
            headers=headers,
            content={
                "error": "rate_limit_exceeded",
                "message": exc.message,
                "service": exc.service,
                "retry_after": exc.retry_after,
            },
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        logger.error(
            "external_service_error",
            service=exc.service,
            status_code=exc.status_code,
            message=exc.message,
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": "external_service_error",
                "message": exc.message,
                "service": exc.service,
                "details": exc.details,
            },
        )

    @app.exception_handler(CacheError)
    async def cache_error_handler(request: Request, exc: CacheError) -> JSONResponse:
        logger.error("cache_error", message=exc.message)
        return JSONResponse(
            status_code=503,
            content={
                "error": "cache_error",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        logger.error(
            "api_error",
            message=exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(MediaSearchError)
    async def media_search_error_handler(
        request: Request, exc: MediaSearchError
    ) -> JSONResponse:
        logger.error("media_search_error", message=exc.message)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
