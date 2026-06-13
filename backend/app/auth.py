"""
JWT Authentication & Authorization
Handles token generation, validation, and role-based access control
"""

import os
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import g, jsonify, request

from app.models.user import User

# JWT Configuration
JWT_SECRET = os.environ.get(
    "JWT_SECRET", "dev-jwt-secret-change-in-production"
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class TokenManager:
    """Generate and validate JWT tokens"""

    @staticmethod
    def generate_token(
        user_id, organisation_id, expires_in=JWT_EXPIRATION_HOURS
    ):
        """Generate JWT token for user"""
        payload = {
            "user_id": user_id,
            "organisation_id": organisation_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=expires_in),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_token(token):
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired", "code": "TOKEN_EXPIRED"}
        except jwt.InvalidTokenError:
            return {"error": "Invalid token", "code": "INVALID_TOKEN"}
        except Exception as e:
            return {"error": str(e), "code": "TOKEN_ERROR"}

    @staticmethod
    def extract_token_from_header(request):
        """Extract token from Authorization header"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:]  # Remove 'Bearer ' prefix


def require_auth(f):
    """
    Decorator: Require valid JWT token
    Sets g.user and g.organisation_id
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = TokenManager.extract_token_from_header(request)

        if not token:
            return (
                jsonify({"error": "Missing or invalid authorization header"}),
                401,
            )

        payload = TokenManager.verify_token(token)

        if "error" in payload:
            return jsonify(payload), 401

        user_id = payload.get("user_id")
        organisation_id = payload.get("organisation_id")

        # Load user
        user = User.query.filter_by(
            id=user_id, organisation_id=organisation_id
        ).first()

        if not user or not user.is_active:
            return jsonify({"error": "User not found or inactive"}), 401

        # Set context
        g.user = user
        g.organisation_id = organisation_id

        return f(*args, **kwargs)

    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator: Require user to have one of specified roles
    Must be used AFTER @require_auth
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "user"):
                return jsonify({"error": "Authentication required"}), 401

            if g.user.role not in allowed_roles:
                return (
                    jsonify(
                        {
                            "error": f'Insufficient permissions. Required roles: {", ".join(allowed_roles)}',
                            "required_roles": list(allowed_roles),
                            "user_role": g.user.role,
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_permission(permission):
    """
    Decorator: Require user to have specific permission
    Must be used AFTER @require_auth
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "user"):
                return jsonify({"error": "Authentication required"}), 401

            if not g.user.has_permission(permission):
                return (
                    jsonify(
                        {
                            "error": f"User does not have permission: {permission}",
                            "required_permission": permission,
                            "user_role": g.user.role,
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def filter_by_org():
    """
    Decorator: Automatically filter queries by organisation_id
    Must be used AFTER @require_auth

    Usage in routes:
        @require_auth
        @filter_by_org()
        def my_route():
            org_id = g.organisation_id
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "organisation_id"):
                return jsonify({"error": "Organisation context not set"}), 500

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def verify_org_access(org_id):
    """
    Verify user has access to requested organisation
    Returns True if authorized, False otherwise
    """
    if not hasattr(g, "organisation_id"):
        return False

    return g.organisation_id == org_id


def verify_resource_ownership(resource, user_id=None):
    """
    Verify user has access to resource
    Checks organisation_id and optionally user ownership
    """
    if not hasattr(g, "organisation_id"):
        return False

    if not hasattr(resource, "organisation_id"):
        return False

    if resource.organisation_id != g.organisation_id:
        return False

    if user_id and hasattr(resource, "user_id"):
        if resource.user_id != user_id:
            return False

    return True
