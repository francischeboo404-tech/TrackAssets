import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db

# Default to development when running directly to avoid forcing HTTPS redirects
# which cause TLS ClientHello bytes to be received by the plain HTTP dev server.
# Use the explicit FLASK_ENV environment variable to opt into production.
app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Add models to Flask shell context"""
    from app.models import user, organization, department, asset, inventory
    return {
        'db': db,
        'User': user.User,
        'Organization': organization.Organization,
        'Department': organization.Department,
        'Asset': asset.Asset,
        'InventoryItem': inventory.InventoryItem,
        'StockMovement': inventory.StockMovement,
        'AuditLog': inventory.AuditLog,
    }

if __name__ == '__main__':
    with app.app_context():
        # Only auto-create tables in non-production environments
        if app.config.get('DEBUG') or app.config.get('TESTING'):
            try:
                db.create_all()
            except Exception as e:
                # Don't crash the dev server if the database is temporarily unavailable
                # Log the error so the developer can fix credentials or start the DB.
                app.logger.warning(
                    f"Skipping automatic table creation due to DB error: {e}"
                )
    # Properly parse DEBUG env var (handle strings like 'False')
    debug_env = os.environ.get('DEBUG', 'False')
    debug = str(debug_env).lower() in ('1', 'true', 'yes', 'on')
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    # Use reloader only in explicit debug mode
    app.run(host=host, port=port, debug=debug, use_reloader=debug)
