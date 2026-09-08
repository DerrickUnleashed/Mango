"""Structured API errors with machine-readable codes."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Base class for domain API errors.

    Attributes:
        code: Machine-readable error code, e.g. ``video_not_found``.
        message: Human-readable, user-facing message.
        http_status: HTTP status to return.
        details: Optional additional structured context.
    """

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}


class NotFoundError(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status.HTTP_404_NOT_FOUND)


class ConflictError(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status.HTTP_409_CONFLICT)


class ValidationFailError(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status.HTTP_422_UNPROCESSABLE_CONTENT)


def _error_response(
    status_code: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    body: dict = {"code": code, "detail": message}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    del request
    return _error_response(exc.http_status, exc.code, exc.message, exc.details)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    code = "http_error"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        code = "method_not_allowed"
    return _error_response(exc.status_code, code, str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request
    errors = [
        {
            "loc": list(e.get("loc", [])),
            "msg": e.get("msg", "invalid"),
            "type": e.get("type", ""),
        }
        for e in exc.errors()
    ]
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation_error",
        "Request validation failed",
        {"errors": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    del request, exc
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "An unexpected error occurred",
    )
