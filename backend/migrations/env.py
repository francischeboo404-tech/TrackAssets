import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

_flask_env = os.environ.get("FLASK_ENV", "development")

load_dotenv(os.path.join(BASE_DIR, ".env"))

if _flask_env == "production":
    load_dotenv(
        os.path.join(BASE_DIR, ".env.production"),
        override=True,
    )

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import Flask app and models
from app import create_app, db

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

flask_app = create_app(_flask_env)

db_url = flask_app.config["SQLALCHEMY_DATABASE_URI"]

config.set_main_option(
    "sqlalchemy.url",
    db_url.replace("%", "%%")
)

ini_file = os.path.abspath(
    config.config_file_name
) if config.config_file_name else None

print("=" * 60)
print("config =", config.config_file_name)
print("absolute =", ini_file)
print("exists =", os.path.exists(ini_file) if ini_file else False)
print("database =", db_url)
print("=" * 60)

if ini_file and os.path.exists(ini_file):
    fileConfig(ini_file)

target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
