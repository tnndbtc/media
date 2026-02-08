"""Base HTTP client with retry logic and error handling."""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.utils.circuit_breaker import CircuitBreaker
from app.utils.exceptions import ExternalServiceError, RateLimitError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseHTTPClient:
    """Base HTTP client with retry logic, circuit breaker, and error handling."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        service_name: str = "http_client",
    ):
        """Initialize the HTTP client.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            service_name: Name for logging and circuit breaker
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.service_name = service_name

        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(
            name=service_name,
            failure_threshold=5,
            recovery_timeout=30.0,
        )

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> dict[str, str]:
        """Get default headers. Override in subclasses."""
        return {
            "Accept": "application/json",
            "User-Agent": "MultilangMediaSearch/1.0",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers

        Returns:
            Parsed JSON response

        Raises:
            ExternalServiceError: On request failure
            RateLimitError: On 429 response
        """
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
            reraise=True,
        )
        async def _execute_request() -> httpx.Response:
            return await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
            )

        try:
            response = await self._circuit_breaker.call(_execute_request)
            return self._handle_response(response)

        except httpx.TimeoutException as e:
            logger.error("request_timeout", service=self.service_name, url=url)
            raise ExternalServiceError(
                message=f"Request timeout to {self.service_name}",
                service=self.service_name,
                details={"url": url, "error": str(e)},
            )
        except httpx.TransportError as e:
            logger.error("transport_error", service=self.service_name, url=url, error=str(e))
            raise ExternalServiceError(
                message=f"Connection error to {self.service_name}",
                service=self.service_name,
                details={"url": url, "error": str(e)},
            )

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle HTTP response and extract JSON.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON data

        Raises:
            RateLimitError: On 429 response
            ExternalServiceError: On error responses
        """
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                service=self.service_name,
                retry_after=int(retry_after) if retry_after else None,
            )

        if response.status_code >= 400:
            logger.error(
                "api_error_response",
                service=self.service_name,
                status_code=response.status_code,
                body=response.text[:500],
            )
            raise ExternalServiceError(
                message=f"{self.service_name} API error: {response.status_code}",
                service=self.service_name,
                status_code=response.status_code,
                details={"response": response.text[:500]},
            )

        try:
            return response.json()
        except Exception as e:
            raise ExternalServiceError(
                message=f"Invalid JSON response from {self.service_name}",
                service=self.service_name,
                details={"error": str(e), "response": response.text[:200]},
            )

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self._make_request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request."""
        return await self._make_request(
            "POST", endpoint, params=params, json_data=json_data, headers=headers
        )
