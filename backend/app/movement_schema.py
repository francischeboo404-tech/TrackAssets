from sqlalchemy import inspect, text

from app import db


def ensure_movement_schema_columns(app=None):
    """Ensure movement tables have the columns required for inventory and asset flows."""
    if app is None:
        from flask import current_app
        app = current_app

    if app is None:
        return

    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)

        required_columns = {
            "item_issues": [
                ("asset_id", "INTEGER", None),
                ("item_type", "VARCHAR(50)", "'inventory'"),
            ],
            "item_returns": [
                ("asset_id", "INTEGER", None),
                ("item_type", "VARCHAR(50)", "'inventory'"),
            ],
        }

        for table_name, columns in required_columns.items():
            if not inspector.has_table(table_name):
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type, default_value in columns:
                if column_name in existing_columns:
                    continue

                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                if default_value is not None:
                    sql = f"{sql} DEFAULT {default_value}"

                db.session.execute(text(sql))

        db.session.commit()
