from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import ninja.errors
from django.http import Http404, HttpRequest, HttpResponse
from ninja.errors import AuthenticationError, HttpError, ValidationError

if TYPE_CHECKING:
    from ninja import NinjaAPI

logger = logging.getLogger(__name__)

# Fallback error codes for errors raised by Django Ninja itself.
STATUS_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


# ---------------------------------------------------------------------------
# Our own error types. Raise these from anywhere in the code.
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Base class. Each subclass sets its HTTP status, error code and default message."""

    status_code = 400
    code = "bad_request"
    default_message = "The request could not be processed."

    def __init__(self, message: str | None = None, *, details: list[dict[str, Any]] | None = None):
        self.message = message or self.default_message
        self.details = details or []
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_error"
    default_message = "Some fields are invalid."


class AuthenticationFailed(AppError):
    status_code = 401
    code = "not_authenticated"
    default_message = "Authentication credentials were missing or invalid."


class Forbidden(AppError):
    status_code = 403
    code = "permission_denied"
    default_message = "You do not have permission to perform this action."


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    default_message = "The requested resource was not found."


class Conflict(AppError):
    status_code = 409
    code = "conflict"
    default_message = "The request conflicts with the current state of the resource."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_body(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"error": body}


def _clean_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn Pydantic's detailed errors into simple {field, message} pairs.

    We deliberately do NOT include the value the user submitted, because it might
    be a password and we don't want to send it back or write it to logs.
    """
    cleaned = []
    for err in errors:
        loc = [str(part) for part in err.get("loc", [])]
        # Django Ninja reports locations like ["body", "payload", "email"].
        # By convention in this project, the request body parameter is always called
        # `payload` and a query-string schema is called `filters`, so we strip those.
        if loc[:2] in (["body", "payload"], ["query", "filters"]):
            loc = loc[2:]
        elif loc and loc[0] in {"body", "query", "path", "header", "cookie"}:
            loc = loc[1:]
        message = str(err.get("msg", "Invalid value.")).removeprefix("Value error, ")
        cleaned.append({"field": ".".join(loc) or None, "message": message})
    return cleaned


# ---------------------------------------------------------------------------
# Register the handlers on the API
# ---------------------------------------------------------------------------


def register_exception_handlers(api: NinjaAPI) -> None:
    def respond(
        request: HttpRequest,
        status: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> HttpResponse:
        return api.create_response(request, _error_body(code, message, details), status=status)

    # 1. Our own errors (NotFound, Forbidden, ...)
    @api.exception_handler(AppError)
    def handle_app_error(request: HttpRequest, exc: AppError) -> HttpResponse:
        return respond(request, exc.status_code, exc.code, exc.message, exc.details)

    # 2. Invalid request data, detected automatically by Django Ninja/Pydantic
    @api.exception_handler(ValidationError)
    def handle_validation_error(request: HttpRequest, exc: ValidationError) -> HttpResponse:
        return respond(
            request,
            422,
            "validation_error",
            "Some fields are invalid.",
            _clean_validation_errors(list(exc.errors)),
        )

    # 3. Missing or invalid login token
    @api.exception_handler(AuthenticationError)
    def handle_auth_error(request: HttpRequest, exc: AuthenticationError) -> HttpResponse:
        return respond(request, 401, "not_authenticated", AuthenticationFailed.default_message)

    # 4. Other HTTP errors raised by Django Ninja (including "too many requests" later)
    def handle_http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        status = exc.status_code
        response = respond(request, status, STATUS_CODES.get(status, "error"), str(exc))
        wait = getattr(exc, "wait", None)
        if status == 429 and wait:
            response["Retry-After"] = str(int(wait))  # tells the client how long to wait
        return response

    api.add_exception_handler(HttpError, handle_http_error)
    for name in ("Throttled", "AuthorizationError"):
        exc_class = getattr(ninja.errors, name, None)
        if exc_class is not None:
            api.add_exception_handler(exc_class, handle_http_error)

    # 5. Django's own "not found" (e.g. from get_object_or_404)
    @api.exception_handler(Http404)
    def handle_not_found(request: HttpRequest, exc: Http404) -> HttpResponse:
        return respond(request, 404, "not_found", NotFound.default_message)

    # 6. Anything else = a bug. Log the full details for us, show a generic message to users.
    @api.exception_handler(Exception)
    def handle_unexpected(request: HttpRequest, exc: Exception) -> HttpResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return respond(request, 500, "server_error", "Something went wrong. Please try again.")