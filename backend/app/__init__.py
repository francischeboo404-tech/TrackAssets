import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
import re
from flask_jwt_extended import JWTManager, get_jwt, verify_jwt_in_request
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text as sa_text
import shutil
import os as _os

db = SQLAlchemy()
jwt = JWTManager()

# Rate Limiting
storage_uri = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=["200 per day", "50 per hour"],
)


def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    from config import config_by_name

    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    
    # Configure SQLite to use WAL mode and busy timeout to prevent "database is locked" errors
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if type(dbapi_connection).__name__ == "Connection": # sqlite3.Connection
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=15000") # Wait 15 seconds for a lock
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
            except Exception:
                pass

    jwt.init_app(app)
    limiter.init_app(app)

    # Configure CORS strictly
    cors_origins = app.config.get("CORS_ORIGINS", [])
    if isinstance(cors_origins, str):
        cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    # Allow Vercel-hosted frontends by adding a regex origin for any subdomain of vercel.app
    cors_origins_compiled = list(cors_origins)
    try:
        vercel_regex = re.compile(r"^https://.*\.vercel\.app$")
        cors_origins_compiled.append(vercel_regex)
    except re.error:
        # If regex compilation fails, fall back to literal vercel domain
        cors_origins_compiled.append("https://track-it-gamma-blue.vercel.app")

    CORS(
        app,
        origins=cors_origins_compiled,
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-TOKEN",
            "Accept",
        ],
        expose_headers=["Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        supports_credentials=True,
        max_age=3600,
    )

    with app.app_context():
        from app.models import token

        from app.tenant_utils import is_token_revoked

        @jwt.token_in_blocklist_loader
        def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
            return is_token_revoked(jwt_payload["jti"])

        # Register blueprints (use relative imports to avoid import-resolution issues)
        import importlib

        def _import_bp(module_name: str):
            # Ensure any stray 'app' module is a proper package; if not, reload it
            import sys
            if "app" in sys.modules and not getattr(sys.modules["app"], "__path__", None):
                del sys.modules["app"]

            pkg_candidates = [__package__ or "app", "app"]
            last_exc = None
            for pkg in pkg_candidates:
                try:
                    mod = importlib.import_module(f"{pkg}.blueprints.{module_name}")
                    return getattr(mod, f"{module_name}_bp")
                except Exception as e:
                    last_exc = e
            # If all attempts failed, raise the last exception for visibility
            raise last_exc

        assets_bp = _import_bp("assets")
        audit_bp = _import_bp("audit")
        auth_bp = _import_bp("auth")
        departments_bp = _import_bp("departments")
        inventory_bp = _import_bp("inventory")
        transfers_bp = _import_bp("transfers")
        tracking_bp = _import_bp("tracking")
        restock_bp = _import_bp("restock")
        analytics_bp = _import_bp("analytics")
        reports_bp = _import_bp("reports")
        warehouses_bp = _import_bp("warehouses")
        settings_bp = _import_bp("settings")
        search_bp = _import_bp("search")

        users_bp = _import_bp("users")

        app.register_blueprint(users_bp, url_prefix="/api/users")

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(assets_bp, url_prefix="/api/assets")
        app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
        app.register_blueprint(departments_bp, url_prefix="/api/departments")
        app.register_blueprint(transfers_bp, url_prefix="/api/transfers")
        app.register_blueprint(tracking_bp, url_prefix="/api/tracking")
        app.register_blueprint(restock_bp, url_prefix="/api/restock")
        app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
        app.register_blueprint(audit_bp, url_prefix="/api/audit")
        app.register_blueprint(warehouses_bp, url_prefix="/api/warehouses")
        app.register_blueprint(reports_bp, url_prefix="/api/reports")
        app.register_blueprint(settings_bp, url_prefix="/api/settings")
        app.register_blueprint(search_bp, url_prefix="/api/search")

        @app.route("/static/uploads/logos/<path:filename>")
        def serve_org_logo(filename):
            """Serve organization logo uploads."""
            from flask import send_from_directory

            directory = _os.path.join(app.root_path, "static", "uploads", "logos")
            return send_from_directory(directory, filename)

        # Health check
        @app.route("/health")
        def health_check():
            health = {"status": "healthy", "services": {}}

            # DB Check (use SQLAlchemy text)
            try:
                db.session.execute(sa_text("SELECT 1"))
                health["services"]["database"] = "up"
            except Exception as e:
                app.logger.error(f"Health DB check failed: {str(e)}")
                health["services"]["database"] = "down"
                health["status"] = "unhealthy"

            # Disk Space Check (platform-safe root)
            try:
                root_path = _os.path.abspath(_os.sep)
                total, used, free = shutil.disk_usage(root_path)
                health["system"] = {
                    "disk_free_gb": round(free / (2**30), 2),
                    "disk_total_gb": round(total / (2**30), 2),
                }
                if free < (2**30):  # Less than 1GB
                    health["status"] = "degraded"
            except Exception as e:
                app.logger.warning(f"Disk usage check skipped: {e}")
                health.setdefault("system", {})["disk_check"] = "unavailable"

            return jsonify(health), (
                200 if health["status"] != "unhealthy" else 503
            )

        _PUBLIC_PATHS = {
            "/",
            "/health",
            "/ping",
            "/cron/keepalive",
            "/api/cron/keepalive",
        }

        def _cron_keepalive_response():
            """Wake Render/free-tier hosts; call every ~10 minutes from cron-job.org."""
            secret = app.config.get("CRON_SECRET")
            if secret:
                provided = (
                    request.args.get("token")
                    or request.headers.get("X-Cron-Secret")
                )
                if provided != secret:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "message": "Invalid or missing cron token",
                                "status_code": 401,
                            }
                        ),
                        401,
                    )

            db_status = "skipped"
            if request.args.get("db", "").lower() in ("1", "true", "yes"):
                try:
                    db.session.execute(sa_text("SELECT 1"))
                    db_status = "up"
                except Exception as exc:
                    app.logger.warning("Cron keepalive DB check failed: %s", exc)
                    db_status = "down"

            return (
                jsonify(
                    {
                        "ok": True,
                        "service": "trackit",
                        "purpose": "keepalive",
                        "database": db_status,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                200,
            )

        @app.route("/ping", methods=["GET", "HEAD"])
        def ping():
            """Minimal liveness probe (no database)."""
            return (
                jsonify(
                    {
                        "ok": True,
                        "service": "trackit",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                200,
            )

        @app.route("/cron/keepalive", methods=["GET", "HEAD"])
        def cron_keepalive():
            return _cron_keepalive_response()

        @app.route("/api/cron/keepalive", methods=["GET", "HEAD"])
        def api_cron_keepalive():
            return _cron_keepalive_response()

        @app.route("/", methods=["GET"])
        def index():
            """Root endpoint providing basic API information."""
            return (
                jsonify(
                    {
                        "service": "Assets Inventory API",
                        "status": "running",
                        "health": "/health",
                        "ping": "/ping",
                        "cron_keepalive": "/cron/keepalive",
                        "api_cron_keepalive": "/api/cron/keepalive",
                        "endpoints": [
                            "/api/users",
                            "/api/auth",
                            "/api/assets",
                            "/api/inventory",
                        ],
                    }
                ),
                200,
            )

        # Catch-all route for OPTIONS preflight on /api paths
        @app.route("/api/<path:path>", methods=["OPTIONS"])
        def handle_options(path):
            """Handle CORS preflight for all /api paths."""
            from app.cors_utils import apply_cors_headers, is_allowed_origin

            origin = request.headers.get("Origin", "")
            if origin and not is_allowed_origin(origin):
                resp = jsonify({"success": False, "message": "Origin not allowed"})
                apply_cors_headers(resp, origin)
                return resp, 403
            resp = app.make_response("")
            resp.status_code = 204
            apply_cors_headers(resp, origin or None)
            return resp

        # Global handler for all OPTIONS requests (preflight)
        @app.before_request
        def handle_options_preflight():
            """Handle CORS preflight requests globally."""
            if request.method == "OPTIONS":
                from app.cors_utils import is_allowed_origin, apply_cors_headers

                origin = request.headers.get("Origin", "")
                if origin and not is_allowed_origin(origin):
                    resp = jsonify(
                        {"success": False, "message": "Origin not allowed"}
                    )
                    apply_cors_headers(resp, origin)
                    return resp, 403

                resp = app.make_response("")
                resp.status_code = 204
                apply_cors_headers(resp, origin or None)
                return resp

        # Multi-tenant Schema Isolation
        from app.tenant_utils import set_tenant_schema

        @app.before_request
        def handle_tenant_isolation():
            """Switch database schema based on the authenticated user's organization."""
            # Skip for non-API, public routes, and OPTIONS preflight
            if (
                request.path.startswith("/static")
                or request.method == "OPTIONS"
                or request.path in _PUBLIC_PATHS
                or request.path.startswith("/api/auth/")
                or request.path.startswith("/api/cron/")
            ):
                return

            try:
                # Check for JWT and extract organization context
                verify_jwt_in_request(optional=True)
                claims = get_jwt()
                if claims and 'organisation_id' in claims:
                    set_tenant_schema(claims['organisation_id'])
            except Exception as e:
                # Log but don't block; actual auth decorators will handle errors
                app.logger.debug(f"Tenant isolation context skipped: {str(e)}")

        @app.before_request
        def log_incoming_request():
            """Log key request info to help diagnose Method Not Allowed or proxy issues."""
            if request.path in ("/ping", "/cron/keepalive", "/api/cron/keepalive"):
                return
            try:
                origin = request.headers.get('Origin')
                host = request.headers.get('Host')
                ua = request.headers.get('User-Agent')
                app.logger.info(
                    f"INCOMING REQUEST - {request.remote_addr} {request.method} {request.path} Origin={origin} Host={host} UA={ua}"
                )
            except Exception:
                app.logger.debug("Failed to log incoming request details")

        @app.after_request
        def normalize_api_responses(response):
            """Ensure JSON responses have a consistent wrapper but DO NOT alter HTTP status codes.

            Keeping original status codes preserves correct semantics for clients, health checks,
            and observability while still adding 'success' and 'status_code' metadata for
            well-formed JSON responses.
            """
            try:
                # Consider responses that claim to be JSON
                if response.content_type and response.content_type.startswith("application/json"):
                    original_status = response.status_code
                    try:
                        data = response.get_json()
                    except Exception:
                        data = None

                    # If it's a dict, ensure the wrapper fields exist
                    if isinstance(data, dict):
                        is_success = 200 <= original_status < 300
                        data.setdefault("success", is_success)
                        data.setdefault("status_code", original_status)
                        response.set_data(jsonify(data).data)
                    elif data is not None:
                        # For non-dict JSON (lists, primitives), wrap them to maintain structure
                        is_success = 200 <= original_status < 300
                        wrapped = {"success": is_success, "status_code": original_status, "data": data}
                        response.set_data(jsonify(wrapped).data)
                    # If data is None (invalid JSON or empty body), leave response as-is
                    # NOTE: Do NOT change response.status_code here; preserve original HTTP semantics
            except Exception:
                # Fail-safe: on any error while normalizing, do not modify response
                pass

            try:
                from app.cors_utils import apply_cors_headers

                origin = request.headers.get("Origin")
                if origin and not response.headers.get("Access-Control-Allow-Origin"):
                    apply_cors_headers(response, origin)
            except Exception:
                pass

            return response

        # Security Headers — Strict enterprise standards (no unsafe-*)
        # Build CSP based on environment
        allowed_origins = cors_origins if cors_origins else ["https://localhost:3000"]
        # Add a CSP-friendly wildcard for Vercel-hosted frontends if not already present
        if not any("vercel" in str(o) for o in allowed_origins):
            allowed_origins.append("https://*.vercel.app")
        
        # In production, no localhost; in dev, allow localhost
        if config_name == "production":
            allowed_origins = [o for o in allowed_origins if not o.startswith("http://localhost")]
            if not allowed_origins:
                # Fallback to empty list (origin cannot be wildcard in production CSP)
                allowed_origins = []
        
        # Construct CSP: no unsafe-inline or unsafe-eval; nonce-based for scripts if needed
        csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'"] + (["https://cdn.jsdelivr.net"] if config_name == "development" else []),
            "style-src": ["'self'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:", "blob:"] + allowed_origins,
            "connect-src": ["'self'"] + allowed_origins,
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
        }
        
        Talisman(
            app,
            content_security_policy=csp,
            force_https=(config_name == "production"), 
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,  # 1 year
            strict_transport_security_include_subdomains=True,
            session_cookie_secure=(config_name == "production"),
            session_cookie_http_only=True,
            referrer_policy="strict-origin-when-cross-origin",
            x_content_type_options=True,
            frame_options="DENY",
        )

        # Register error handlers
        from app.errors import register_error_handlers
        from app.logging_utils import configure_logging

        register_error_handlers(app)
        configure_logging(app)

        # db.create_all() # Moved to migrations

    return app
