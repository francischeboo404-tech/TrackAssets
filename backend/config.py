import os
import re
from datetime import timedelta
from urllib.parse import quote_plus, urlparse, urlunparse
from typing import Optional


def normalize_supabase_database_url(url: Optional[str]) -> Optional[str]:
    """Use Supabase pooler for cloud hosts (Render cannot reach direct db.* IPv6).

    Direct: postgresql://postgres:PASS@db.PROJECT.supabase.co:5432/postgres
    Pooler: postgresql://postgres.PROJECT:PASS@aws-0-REGION.pooler.supabase.com:6543/postgres
    """
    if not url or "pooler.supabase.com" in url:
        return url

    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host.startswith("db.") or not host.endswith(".supabase.co"):
        return url

    project_ref = host[len("db.") : -len(".supabase.co")]
    password = parsed.password
    if not password:
        return url

    pooler_host = os.environ.get(
        "SUPABASE_POOLER_HOST", "aws-0-eu-west-1.pooler.supabase.com"
    )
    pooler_port = os.environ.get("SUPABASE_POOLER_PORT", "6543")
    path = parsed.path or "/postgres"
    query = parsed.query
    if "sslmode=" not in query:
        query = f"{query}&sslmode=require" if query else "sslmode=require"

    netloc = f"postgres.{project_ref}:{quote_plus(password)}@{pooler_host}:{pooler_port}"
    return urlunparse(
        (parsed.scheme, netloc, path, parsed.params, query, parsed.fragment)
    )


def _postgres_engine_options(db_url: Optional[str]) -> dict:
    options = {"pool_pre_ping": True}
    if db_url and db_url.startswith("postgresql://"):
        options["client_encoding"] = "utf8"
        options["connect_args"] = {"connect_timeout": 10}
    return options


def _get_production_jwt_secret() -> str:
    """Get and validate JWT secret for production (minimum 32 chars for HS256).
    
    Raises:
        ValueError: If JWT_SECRET_KEY is not set or too short.
    """
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise ValueError(
            "JWT_SECRET_KEY environment variable is required and must be set. "
            "Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if len(secret) < 32:
        raise ValueError(
            f"JWT_SECRET_KEY must be at least 32 characters (HS256 minimum). "
            f"Current length: {len(secret)}. "
            f"Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return secret


def _validate_jwt_secret(secret: Optional[str]) -> str:
    """Validate JWT secret meets minimum length for HS256 (32 bytes).
    
    Args:
        secret: The JWT secret from environment or config.
    
    Returns:
        The validated secret.
    
    Raises:
        ValueError: If secret is missing or too short in production.
    """
    if not secret:
        raise ValueError(
            "JWT_SECRET_KEY environment variable is required and must be set. "
            "Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if len(secret) < 32:
        raise ValueError(
            f"JWT_SECRET_KEY must be at least 32 characters (HS256 minimum). "
            f"Current length: {len(secret)}. "
            f"Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return secret


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = "None"
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_CSRF_HEADER_NAME = "X-CSRF-TOKEN"
    JWT_REFRESH_CSRF_HEADER_NAME = "X-CSRF-TOKEN"

    # Rate Limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"

    # CORS
    CORS_HEADERS = "Content-Type,Authorization"
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5000"
    ).split(",")

    # Security
    BCRYPT_LOG_ROUNDS = 12

    # Optional secret for /cron/keepalive (?token=... or X-Cron-Secret header)
    CRON_SECRET = os.environ.get("CRON_SECRET")

    # QR tracking
    TRACKING_PUBLIC_URL = os.environ.get(
        "TRACKING_PUBLIC_URL", "http://localhost:5173/tracking"
    )
    QR_PAYLOAD_TTL_DAYS = int(os.environ.get("QR_PAYLOAD_TTL_DAYS", "365"))
    SCAN_DEDUP_SECONDS = int(os.environ.get("SCAN_DEDUP_SECONDS", "30"))

    _db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_PROD")
    SQLALCHEMY_ENGINE_OPTIONS = _postgres_engine_options(_db_url)



class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "dev-secret-key"
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or "sqlite:///trackit_dev.db"
    )
    SESSION_COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"

    # Development CORS
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
    ]


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    
    # Enforce strong JWT secret in production (minimum 32 characters for HS256)
    # Note: Actual validation happens in create_app() to avoid import-time errors in tests
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    
    # Disable CSRF checks for cookie-based JWT in cross-site environments.
    # This prevents 401 on safe session checks like GET /api/auth/me when
    # the frontend cannot reliably emit X-CSRF-TOKEN.
    JWT_COOKIE_CSRF_PROTECT = False
    
    _db_url = os.environ.get("DATABASE_URL_PROD") or os.environ.get("DATABASE_URL")
    _db_url = normalize_supabase_database_url(_db_url)
    if _db_url and _db_url.startswith("postgresql://") and "sslmode=" not in _db_url:
        _db_url += "?sslmode=require"
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_ENGINE_OPTIONS = _postgres_engine_options(_db_url)

    # Production security
    SESSION_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = "None"
    
    _cors_env = os.environ.get("CORS_ORIGINS", "").strip()
    CORS_ORIGINS = (
        [o.strip() for o in _cors_env.split(",") if o.strip()]
        if _cors_env
        else [
            "https://track-it-eta-one.vercel.app",
            "https://track-it-gamma-blue.vercel.app",
        ]
    )


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    SECRET_KEY = os.environ.get("SECRET_KEY") or "test-secret-key"
    # Use a longer default test JWT secret to avoid InsecureKeyLengthWarning during tests
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "test-jwt-secret-key-please-change-to-32-chars!"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
