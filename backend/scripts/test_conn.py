import os
import sys
from dotenv import load_dotenv

def main():
    sys.path.append(os.getcwd())
    load_dotenv()
    # Intentionally use production config to mirror deployment checks
    os.environ["FLASK_ENV"] = "production"

    from app import create_app
    from sqlalchemy import create_engine

    app = create_app("production")
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        print("No database URL configured; skipping connection test.")
        return

    masked = db_url.replace("Fr%4038998653", "***") if isinstance(db_url, str) else str(db_url)
    print("Normalized URL (masked password):", masked)

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("Successfully connected!")
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
