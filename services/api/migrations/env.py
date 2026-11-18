from alembic import context
from recruitment_api.database import database_url
from recruitment_api.schema import metadata
from sqlalchemy import create_engine, pool

url = database_url()

if context.is_offline_mode():
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
