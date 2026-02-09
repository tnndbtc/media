"""API middleware for logging, timing, and CORS."""

import logging as std_logging
import time
import uuid
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Bind request context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Start timing
        start_time = time.perf_counter()

        # Log request (single line)
        client_ip = request.client.host if request.client else "unknown"
        std_logging.info(f"request_started - {request.method} {request.url.path} [client: {client_ip}] [request_id: {request_id}]")

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response (single line)
            std_logging.info(f"request_completed - {response.status_code} {round(duration_ms, 2)}ms [request_id: {request_id}]")

            # Add timing header
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "request_failed",
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            raise


class TimingMiddleware(BaseHTTPMiddleware):
    """Simple timing middleware that adds Server-Timing header."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["Server-Timing"] = f"total;dur={duration_ms:.2f}"
        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging (applied after CORS)
    app.add_middleware(RequestLoggingMiddleware)
