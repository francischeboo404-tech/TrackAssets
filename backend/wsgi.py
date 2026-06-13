import os
from app import create_app

# WSGI entrypoint for production servers (gunicorn, uwsgi, Render, etc.)
# Uses FLASK_ENV environment variable or defaults to 'production'.
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    # Useful for local debugging with `python backend/wsgi.py`
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes', 'on')
    app.run(host=host, port=port, debug=debug)
