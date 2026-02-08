"""Custom exceptions for the application."""


class MediaSearchError(Exception):
    """Base exception for media search errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(MediaSearchError):
    """Configuration-related errors."""

    pass


class ExternalServiceError(MediaSearchError):
    """External API service errors."""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: int | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.service = service
        self.status_code = status_code


class RateLimitError(ExternalServiceError):
    """Rate limit exceeded errors."""

    def __init__(
        self,
        service: str,
        retry_after: int | None = None,
        details: dict | None = None,
    ):
        super().__init__(
            f"Rate limit exceeded for {service}",
            service=service,
            status_code=429,
            details=details,
        )
        self.retry_after = retry_after


class CacheError(MediaSearchError):
    """Cache-related errors."""

    pass


class ValidationError(MediaSearchError):
    """Input validation errors."""

    def __init__(self, message: str, field: str | None = None, details: dict | None = None):
        super().__init__(message, details)
        self.field = field


class APIError(MediaSearchError):
    """API endpoint errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
