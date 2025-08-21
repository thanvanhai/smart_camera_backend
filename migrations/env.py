from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.database import Base  # metadata của các model
from app.config import settings       # <--- dùng settings.database_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

target_metadata = Base.metadata

# overwrite sqlalchemy.url bằng async database url (chuyển sang sync cho Alembic)
DATABASE_URL_SYNC = settings.database_url.replace("+asyncpg", "")

def run_migrations_offline():
    context.configure(
        url=DATABASE_URL_SYNC,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL_SYNC},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
