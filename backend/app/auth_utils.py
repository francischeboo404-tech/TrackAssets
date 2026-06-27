from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.errors import AuthenticationError, AuthorizationError
from app.tenant_utils import get_user_by_id


def jwt_required_with_user(f):
    """Decorator that requires JWT and loads user into g"""

    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        from flask import g

        user_id = get_jwt_identity()
        jwt_data = get_jwt()

        user_obj = get_user_by_id(user_id)
        if not user_obj or not user_obj.is_active:
            raise AuthenticationError("User not found or inactive")

        # Store user in flask g for easy access
        g.user = user_obj
        g.jwt_claims = jwt_data

        return f(*args, **kwargs)

    return decorated_function


def normalize_role(role: str) -> str:
    """Convert legacy aliases to canonical role names."""
    return {
        "staff": "logistics_officer",
        "dept_head": "procurement_officer",
        "viewer": "employee",
    }.get(role, role)


def require_role(*roles):
    """Decorator to require specific roles"""

    normalized_required = tuple(normalize_role(role) for role in roles)

    def decorator(f):
        @wraps(f)
        @jwt_required_with_user
        def decorated_function(*args, **kwargs):
            from flask import g

            current_role = normalize_role(g.user.role)
            allowed_roles = ("admin", "superadmin") + normalized_required

            if current_role not in allowed_roles:
                raise AuthorizationError(
                    f"Role '{g.user.role}' not authorized. "
                    f"Required: {', '.join(roles)}"
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_permission(permission):
    """Decorator to require specific permissions"""

    def decorator(f):
        @wraps(f)
        @jwt_required_with_user
        def decorated_function(*args, **kwargs):
            from flask import g

            # Allow admin and superadmin to bypass permission checks
            if g.user.role not in ("admin", "superadmin") and not g.user.has_permission(permission):
                raise AuthorizationError(f"Permission '{permission}' required")

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_current_user():
    """Get current user from JWT token"""
    from flask import g

    return getattr(g, "user", None)


def get_current_user_id():
    """Get current user ID"""
    user_obj = get_current_user()
    return user_obj.id if user_obj else None


def get_current_organisation_id():
    """Get current user's organization ID"""
    user_obj = get_current_user()
    return user_obj.organisation_id if user_obj else None
