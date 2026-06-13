import traceback

from flask import current_app, jsonify, request

from app import db
from app.audit_service import AuditService


class APIError(Exception):
    """Base API error class"""

    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


class ValidationError(APIError):
    """Validation error"""

    def __init__(self, message, errors=None):
        super().__init__(message, 400, {"errors": errors or []})


class AuthenticationError(APIError):
    """Authentication error"""

    def __init__(self, message="Authentication required"):
        super().__init__(message, 401)


class AuthorizationError(APIError):
    """Authorization error"""

    def __init__(self, message="Insufficient permissions"):
        super().__init__(message, 403)


class NotFoundError(APIError):
    """Resource not found error"""

    def __init__(self, message="Resource not found"):
        super().__init__(message, 404)


class ConflictError(APIError):
    """Resource conflict error"""

    def __init__(self, message="Resource conflict"):
        super().__init__(message, 409)


def _error_response(message, status_code, error_name, extra=None):
    body = {
        "success": False,
        "message": message,
        "errors": [],
        "error": error_name,
        "status_code": status_code,
    }
    if extra:
        body.update(extra)
    return jsonify(body), status_code


def register_error_handlers(app):
    """Register error handlers for the Flask app"""

    @app.errorhandler(APIError)
    def handle_api_error(error):
        AuditService.log_user_action(
            action="API_ERROR",
            details={
                "error_type": error.__class__.__name__,
                "message": error.message,
                "status_code": error.status_code,
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            },
        )

        body = {
            "success": False,
            "message": error.message,
            "errors": [],
            "error": error.__class__.__name__,
            "status_code": error.status_code,
        }
        if error.payload:
            if "validation_errors" in error.payload and "errors" not in error.payload:
                body["errors"] = error.payload["validation_errors"]
            body.update(error.payload)

        return jsonify(body), error.status_code

    @app.errorhandler(400)
    def handle_bad_request(error):
        AuditService.log_user_action(
            action="BAD_REQUEST",
            details={
                "description": error.description,
                "endpoint": request.endpoint,
                "method": request.method,
            },
        )
        return _error_response(
            "Invalid request data",
            400,
            "BadRequest",
            {"details": error.description},
        )

    @app.errorhandler(401)
    def handle_unauthorized(error):
        AuditService.log_user_action(
            action="UNAUTHORIZED_ACCESS",
            details={
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            },
        )
        return _error_response("Authentication required", 401, "Unauthorized")

    @app.errorhandler(403)
    def handle_forbidden(error):
        AuditService.log_user_action(
            action="FORBIDDEN_ACCESS",
            details={
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            },
        )
        return _error_response("Insufficient permissions", 403, "Forbidden")

    @app.errorhandler(404)
    def handle_not_found(error):
        AuditService.log_user_action(
            action="NOT_FOUND",
            details={
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            },
        )
        return _error_response("Resource not found", 404, "NotFound")

    @app.errorhandler(429)
    def handle_rate_limit(error):
        AuditService.log_user_action(
            action="RATE_LIMIT_EXCEEDED",
            details={
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            },
        )
        return _error_response("Too many requests", 429, "RateLimitExceeded")

    from sqlalchemy.exc import IntegrityError, DataError, OperationalError

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        db.session.rollback()
        current_app.logger.warning(f"Database integrity error: {str(error)}")

        message = "A database integrity constraint was violated."
        if "unique" in str(error).lower():
            message = "This record already exists in the system."
        elif "foreign key" in str(error).lower():
            message = (
                "This operation cannot be completed because the record is "
                "referenced by other data."
            )

        return _error_response(message, 409, "Conflict")

    @app.errorhandler(DataError)
    def handle_data_error(error):
        db.session.rollback()
        current_app.logger.warning(f"Database data error: {str(error)}")
        return _error_response(
            "The provided data format is invalid for the database.",
            400,
            "ValidationError",
        )

    @app.errorhandler(OperationalError)
    def handle_operational_error(error):
        db.session.rollback()
        current_app.logger.error(f"Database operational error: {str(error)}")
        return _error_response(
            "The database is currently unavailable or busy. Please try again later.",
            503,
            "ServiceUnavailable",
        )

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        AuditService.log_user_action(
            action="HTTP_EXCEPTION",
            details={
                "code": error.code,
                "name": error.name,
                "description": error.description,
                "endpoint": request.endpoint,
                "method": request.method,
            },
        )
        return _error_response(
            error.description or error.name,
            error.code,
            error.name,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        current_app.logger.error(f"Unexpected error: {traceback.format_exc()}")

        AuditService.log_user_action(
            action="UNEXPECTED_ERROR",
            details={
                "error_type": type(error).__name__,
                "endpoint": request.endpoint,
                "method": request.method,
                "error": "Error details captured in system logs",
            },
        )

        db.session.rollback()

        extra = {"details": str(error)} if current_app.debug else None
        return _error_response(
            "An unexpected system error occurred.",
            500,
            "InternalServerError",
            extra,
        )
